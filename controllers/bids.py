from math import ceil
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session,joinedload

from database import get_db
from dependencies.get_current_user import get_current_user
from models.auction import AuctionModel,AuctionStatus
from models.bid import BidModel
from models.user import UserModel
from serializers.bid import BidSchema, CreateBidSchema, UserBidSchema
from serializers.pagination import PaginatedResponse
from utils.time import utcnow
from websocket.manager import manager

router=APIRouter(prefix="/api")

@router.get("/bids/{bid_id}",response_model=BidSchema)
def get_single(bid_id:int,db:Session=Depends(get_db)):
    bid=db.query(BidModel).filter(BidModel.id==bid_id).first()
    if not bid:
        raise HTTPException(404,"Bid not found")
    return bid

@router.get("/auctions/{auction_id}/bids",response_model=PaginatedResponse[BidSchema])
def get_auction_bids(auction_id:int,page:int=Query(1,ge=1),page_size:int=Query(10,ge=10,le=30),user: UserModel = Depends(get_current_user),db:Session=Depends(get_db)):
    auction=db.query(AuctionModel).filter(AuctionModel.id==auction_id).first()
    if not auction:
        raise HTTPException(404,"Auction not found")
    total=db.query(func.count(BidModel.id)).filter(BidModel.auction_id==auction_id).scalar()
    bids=db.query(BidModel).filter(BidModel.auction_id==auction_id).options(joinedload(BidModel.bidder)).order_by(BidModel.price.desc()).offset((page-1)*page_size).limit(page_size).all()
    return {
        "items":bids,
        "total":total,
        "page":page,
        "page_size":page_size,
        "pages": ceil(total / page_size) if total else 0,#type:ignore
    }

@router.get("/auctions/{auction_id}/winner", response_model=BidSchema)
def get_winning_bid(auction_id: int, db: Session = Depends(get_db)):
    auction = db.query(AuctionModel).filter(AuctionModel.id == auction_id).first()
    if not auction:
        raise HTTPException(404, "Auction not found")

    if auction.status == AuctionStatus.CANCELLED:#type:ignore
        raise HTTPException(409, "Auction was cancelled, so there is no winner")
    has_ended: bool = auction.status == AuctionStatus.ENDED or auction.end_date <= utcnow()  # type: ignore
    if not has_ended:
        raise HTTPException(409, "Auction is still running")
    winning_bid = (
        db.query(BidModel)
        .filter(BidModel.auction_id == auction_id)
        .order_by(BidModel.price.desc(), BidModel.id.asc()).options(joinedload(BidModel.bidder))
        .first()
    )
    if not winning_bid:
        raise HTTPException(404, "Auction ended with no bids")

    return winning_bid

@router.post("/auctions/{auction_id}/bids", status_code=201, response_model=BidSchema)
def create_bid(auction_id: int, form: CreateBidSchema,background_tasks:BackgroundTasks,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)):
    auction = (db.query(AuctionModel)
    .filter(AuctionModel.id == auction_id).with_for_update().first())
       
    if not auction:
       raise HTTPException(404, "Auction not found")
    if auction.status != AuctionStatus.ACTIVE or auction.end_date <= utcnow():#type:ignore
       raise HTTPException(409, "Auction is not accepting bids")
    if auction.seller_id == user.id:#type:ignore
       raise HTTPException(403, "You can't bid on your own auction")
    if form.price <= auction.current_price:#type:ignore
       raise HTTPException(409, "Bid must be higher than the current price")

    price = form.price
    ended = False
    if auction.buy_now_price is not None and price >= auction.buy_now_price:  # type: ignore
        price = auction.buy_now_price  # type: ignore
        auction.status = AuctionStatus.ENDED  # type: ignore
        auction.ended_at = utcnow()#type:ignore 
        ended=True

    bid = BidModel(price=price, bidder_id=user.id, auction_id=auction_id)
    auction.current_price=price#type:ignore    
    db.add(bid)
    db.commit()
    db.refresh(bid)
    background_tasks.add_task(manager.broadcast,auction_id,
            {"type": "new_bid",
            "bid_id": bid.id,
            "price": price,
            "bidder": {"id": bid.bidder_id, "username": user.username},
            "ended": ended,})
    if ended:
        background_tasks.add_task(manager.close_room, auction_id)

    return bid

@router.get("/users/{user_id}/bids", response_model=PaginatedResponse[UserBidSchema])
def get_user_bids(user_id: int,page:int=Query(1,ge=1),page_size:int=Query(10,ge=10,le=25), user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    if user_id != user.id:  # type: ignore
        raise HTTPException(403, "Cannot view other users' bids")
    total=db.query(func.count(BidModel.id)).filter(BidModel.bidder_id==user_id).scalar()
    bids= db.query(BidModel).filter(BidModel.bidder_id == user_id).options(joinedload(BidModel.auction)).order_by(BidModel.id.desc()).offset((page-1)*page_size).limit(page_size).all()
    return {
        "items":bids,
        "total":total,
        "page":page,
        "page_size":page_size,
        "pages":ceil(total/page_size) if total else 0
    }


@router.post("/bids/{bid_id}/accept", response_model=BidSchema)
def accept_bid(
    bid_id: int,
    background_tasks: BackgroundTasks,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bid = db.query(BidModel).filter(BidModel.id == bid_id).first()
    if not bid:
        raise HTTPException(404, "Bid not found")
    
    auction_id: int = bid.auction_id  # type: ignore

    auction = (
        db.query(AuctionModel)
        .filter(AuctionModel.id == bid.auction_id)
        .with_for_update()
        .first()
    )

    if auction.seller_id != user.id:  # type: ignore
        raise HTTPException(403, "Only the seller can accept a bid")
    if auction.status != AuctionStatus.ACTIVE or auction.end_date <= utcnow():  # type: ignore
        raise HTTPException(409, "Auction is not active")

    top_bid = (
        db.query(BidModel)
        .filter(BidModel.auction_id == auction.id)#type:ignore
        .order_by(BidModel.price.desc(), BidModel.id.asc())
        .first()
    )
    if top_bid.id != bid.id:  # type: ignore
        raise HTTPException(409, "Only the highest bid can be accepted")

    auction.status = AuctionStatus.ENDED  # type: ignore
    auction.ended_at = utcnow()  # type: ignore
    db.commit()
    db.refresh(bid)

    background_tasks.add_task(manager.broadcast, auction_id, {
        "type": "bid_accepted",
        "bid_id": bid.id,
        "price": bid.price,
        "bidder": {"id": bid.bidder_id, "username": bid.bidder.username},
    })
    background_tasks.add_task(manager.close_room, auction_id)

    return bid
