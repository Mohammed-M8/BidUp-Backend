from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session,joinedload

from database import get_db
from dependencies.get_current_user import get_current_user
from models.auction import AuctionModel,AuctionStatus
from models.bid import BidModel
from models.user import UserModel
from serializers.bid import BidSchema, CreateBidSchema, UserBidSchema
from utils.time import utcnow
from websocket.manager import manager

router=APIRouter(prefix="/api")

@router.get("/bids/{bid_id}",response_model=BidSchema)
def get_single(bid_id:int,db:Session=Depends(get_db)):
    bid=db.query(BidModel).filter(BidModel.id==bid_id).first()
    if not bid:
        raise HTTPException(404,"Bid not found")
    return bid

@router.get("/auctions/{auction_id}/bids",response_model=List[BidSchema])
def get_auction_bids(auction_id:int,user: UserModel = Depends(get_current_user),db:Session=Depends(get_db)):
    auction=db.query(AuctionModel).filter(AuctionModel.id==auction_id).first()
    if not auction:
        raise HTTPException(404,"Auction not found")
    bids=db.query(BidModel).filter(BidModel.auction_id==auction_id).options(joinedload(BidModel.bidder)).order_by(BidModel.price.desc()).all()
    return bids

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

@router.get("/users/{user_id}/bids", response_model=List[UserBidSchema])
def get_user_bids(user_id: int, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    if user_id != user.id:  # type: ignore
        raise HTTPException(403, "Cannot view other users' bids")
    return db.query(BidModel).filter(BidModel.bidder_id == user_id).options(joinedload(BidModel.auction)).order_by(BidModel.id.desc()).all()

