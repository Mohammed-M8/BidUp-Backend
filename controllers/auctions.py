from datetime import datetime, timedelta
from typing import Annotated, List

import cloudinary
import cloudinary.uploader
import config.cloudinary
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from database import get_db
from dependencies.get_current_user import get_current_user
from models.auction import AuctionModel, AuctionStatus
from models.bid import BidModel
from models.user import UserModel
from serializers.auction import AuctionSchema, CancelAuctionSchema, CreateAuctionSchema, UpdateAuctionSchema


router=APIRouter(prefix="/api/auctions")
CANCEL_LOCK_HOURS = 12


@router.get("",response_model=List[AuctionSchema])
def get_all(db:Session=Depends(get_db)):
    auctions=db.query(AuctionModel).filter(AuctionModel.status==AuctionStatus.ACTIVE,AuctionModel.end_date>datetime.now()).all()
    return auctions

@router.get("/{auction_id}",response_model=AuctionSchema)
def get_single(auction_id:int,db:Session=Depends(get_db)):
    auction=db.query(AuctionModel).filter(AuctionModel.id==auction_id).first()
    if not auction:
        raise HTTPException(404,"Auction not found")
    return auction

@router.post("",response_model=AuctionSchema,status_code=201)
def create(form:CreateAuctionSchema=Depends(),user:UserModel=Depends(get_current_user),db:Session=Depends(get_db)):
    starting_price=form.starting_price
    result=cloudinary.uploader.upload(form.image.file,folder="bidup/auctions")
    image_url=result["secure_url"]
    image_public_id=result["public_id"]
    new_auction=AuctionModel(**form.model_dump(exclude={"image"}),current_price=starting_price,image_url=image_url,image_public_id=image_public_id,seller_id=user.id)
    db.add(new_auction)
    db.commit()
    db.refresh(new_auction)
    return new_auction

@router.put("/{auction_id}",response_model=AuctionSchema)
def update(auction_id:int,update_form:UpdateAuctionSchema=Depends(),user:UserModel=Depends(get_current_user),db:Session=Depends(get_db)):
    auction=db.query(AuctionModel).filter(AuctionModel.id==auction_id).first()
    if not auction:
        raise HTTPException(404,"Auction not found")

    if auction.seller_id!=user.id:#type:ignore
        raise HTTPException(403,"Cannot edit other's auctions")

    if auction.status!=AuctionStatus.ACTIVE:#type:ignore
        raise HTTPException(409,"Only active auctions can be edited")

    if auction.end_date <= datetime.now():  # type: ignore
        raise HTTPException(409, "This auction has already ended")

    has_bids = (
        db.query(BidModel.id).filter(BidModel.auction_id == auction_id).first()
        is not None
    )
    if has_bids:
        raise HTTPException(
            409,
            "Can't edit an auction after bids have been placed. Cancel it and relist instead",
        )

    update_data = update_form.model_dump(
        exclude_none=True,
        exclude={"image"})
    if "end_date" in update_data and auction.bids:
        raise HTTPException(409, "Can't change the end date after bids have been placed")

    new_buy_now = update_data.get("buy_now_price")
    if new_buy_now is not None and new_buy_now <= auction.starting_price:  # type: ignore
        raise HTTPException(422, "buy_now_price must be greater than starting_price")

    for key,value in update_data.items():
        setattr(auction,key,value)

    if update_form.image:
        result = cloudinary.uploader.upload(
            update_form.image.file,
            public_id=auction.image_public_id,
            overwrite=True)

        db.commit()
        db.refresh(auction)

    else:
        db.commit()
        db.refresh(auction)
    return auction


@router.delete("/{auction_id}", status_code=204)
def delete(
    auction_id: int,
    body: CancelAuctionSchema,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    auction = db.query(AuctionModel).filter(AuctionModel.id == auction_id).first()
    if not auction:
        raise HTTPException(404, "Auction not found")

    if auction.seller_id != user.id:  # type: ignore
        raise HTTPException(403, "Cannot delete other's auctions")

    if auction.status != AuctionStatus.ACTIVE:  # type: ignore
        raise HTTPException(409, "Auction is already ended or cancelled")

    if auction.bids:
        time_left = auction.end_date - datetime.now()  # type: ignore
        if time_left < timedelta(hours=CANCEL_LOCK_HOURS):#type:ignore
            raise HTTPException(
                409,
                f"Can't remove an auction with bids in its last {CANCEL_LOCK_HOURS} hours",
            )

    auction.status = AuctionStatus.CANCELLED  # type: ignore
    auction.cancelled_at = datetime.now()  # type: ignore
    auction.cancel_reason = body.reason  # type: ignore

    db.commit()





