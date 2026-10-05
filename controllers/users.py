# controllers/users.py

from math import ceil
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from models.auction import AuctionModel
from models.user import UserModel
from serializers.auction import AuctionSchema
from serializers.pagination import PaginatedResponse
from serializers.user import UserSchema, UserRegistrationSchema, UserLoginSchema, UserTokenSchema
from database import get_db
from dependencies.get_current_user import get_current_user

router = APIRouter(prefix="/api/users")


@router.get('/me', response_model=UserSchema)
def current_user(user: UserSchema = Depends(get_current_user)):
    return user

@router.get( "/{user_id}/auctions",response_model=PaginatedResponse[AuctionSchema])
def get_user_auctions(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=10, le=30),
    db: Session = Depends(get_db)):
    total = (
        db.query(func.count(AuctionModel.id))
        .filter(AuctionModel.seller_id == user_id)
        .scalar()
    )

    auctions = (
        db.query(AuctionModel)
        .filter(AuctionModel.seller_id == user_id)
        .order_by(AuctionModel.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": auctions,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": ceil(total / page_size) if total else 0,
    }
