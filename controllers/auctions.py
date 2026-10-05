from datetime import datetime, timedelta
from math import ceil
from operator import or_
from typing import Annotated, List

import cloudinary
import cloudinary.uploader
from sqlalchemy import func, null
import config.cloudinary
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session,joinedload

from database import get_db
from dependencies.get_current_user import get_current_user
from models.auction import AuctionModel, AuctionStatus
from models.bid import BidModel
from models.category import CategoryModel
from models.user import UserModel
from serializers.auction import AuctionSchema, CancelAuctionSchema, CreateAuctionSchema, UpdateAuctionSchema
from serializers.pagination import PaginatedResponse
from utils.time import utcnow
from websocket.manager import manager


router=APIRouter(prefix="/api/auctions")
CANCEL_LOCK_HOURS = 12


@router.get("", response_model=PaginatedResponse[AuctionSchema])
def get_all(category_id: int | None = None,page:int=Query(1,ge=1),page_size:int=Query(12,ge=1,le=50),search: str | None = Query(None, min_length=1, max_length=100), db: Session = Depends(get_db)):

    filters=[AuctionModel.status==AuctionStatus.ACTIVE,
             AuctionModel.end_date>utcnow()]

    if category_id:
        filters.append(AuctionModel.category_id==category_id)
    if search:
        filters.append(
            or_(
                AuctionModel.product_name.ilike(f"%{search}%"),
                AuctionModel.product_description.ilike(f"%{search}%")
            )
        )

    total=db.query(func.count(AuctionModel.id)).filter(*filters).scalar()

    items=(
        db.query(AuctionModel)
        .options(joinedload(AuctionModel.category),joinedload(AuctionModel.seller))
        .filter(*filters)
        .order_by(AuctionModel.end_date.asc(),AuctionModel.id.asc())
        .offset((page-1)*page_size)
        .limit(page_size)
        .all()#type:ignore
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": ceil(total / page_size) if total else 0,#type:ignore
    }

@router.get("/{auction_id}",response_model=AuctionSchema)
def get_single(auction_id:int,db:Session=Depends(get_db)):
    auction=db.query(AuctionModel).filter(AuctionModel.id==auction_id).options(joinedload(AuctionModel.category),joinedload(AuctionModel.seller)).first()
    if not auction:
        raise HTTPException(404,"Auction not found")
    return auction

@router.post("",response_model=AuctionSchema,status_code=201)
def create(form:CreateAuctionSchema=Depends(),user:UserModel=Depends(get_current_user),db:Session=Depends(get_db)):
    if form.category_id is not None:
        exists = db.query(CategoryModel.id).filter(CategoryModel.id == form.category_id).first()
        if not exists:
            raise HTTPException(422, "Category does not exist")
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

    if auction.end_date <= utcnow():  # type: ignore
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
    category_id = update_data.get("category_id")
    if category_id is not None:
        exists = db.query(CategoryModel.id).filter(CategoryModel.id == category_id).first()
        if not exists:
            raise HTTPException(422, "Category does not exist")
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
    background_tasks:BackgroundTasks,
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
        time_left = auction.end_date - utcnow()  # type: ignore
        if time_left < timedelta(hours=CANCEL_LOCK_HOURS):#type:ignore
            raise HTTPException(
                409,
                f"Can't remove an auction with bids in its last {CANCEL_LOCK_HOURS} hours",
            )

    auction.status = AuctionStatus.CANCELLED  # type: ignore
    auction.cancelled_at = utcnow()  # type: ignore
    auction.cancel_reason = body.reason  # type: ignore
    background_tasks.add_task(manager.broadcast, auction_id, {"type": "auction_cancelled"})
    background_tasks.add_task(manager.close_room, auction_id)

    db.commit()
    







