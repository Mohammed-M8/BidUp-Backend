# controllers/users.py

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.auction import AuctionModel
from models.user import UserModel
from serializers.auction import AuctionSchema
from serializers.user import UserSchema, UserRegistrationSchema, UserLoginSchema, UserTokenSchema
from database import get_db
from dependencies.get_current_user import get_current_user

router = APIRouter(prefix="/api/users")


@router.get('/me', response_model=UserSchema)
def current_user(user: UserSchema = Depends(get_current_user)):
    return user

@router.get("/{user_id}/auctions",response_model=List[AuctionSchema])
def get_user_auctions(user_id:int,user: UserModel = Depends(get_current_user),db:Session=Depends(get_db)):
    user=db.query(UserModel).filter(UserModel.id==user_id).first()
    if not user:
        raise HTTPException(404,"User not found")
    auctions=db.query(AuctionModel).filter(AuctionModel.seller_id==user_id).all()
    return auctions
