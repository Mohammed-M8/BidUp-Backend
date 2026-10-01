from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship
from models.base import BaseModel


class AuctionModel(BaseModel):
    __tablename__="auctions"

    id=Column(Integer,primary_key=True,index=True)
    product_name=Column(String,nullable=False)
    product_description=Column(String,nullable=False)
    buy_now_price=Column(Float,nullable=False)
    starting_price=Column(Float,nullable=False)
    current_price=Column(Float,nullable=False)
    end_date=Column(DateTime,nullable=False)
    is_active=Column(Boolean,default=True)
    image_url=Column(String)
    seller_id=Column(Integer,ForeignKey("users.id"),nullable=False)
    seller=relationship('UserModel',back_populates='auctions')
    bids=relationship('BidModel',back_populates='auction')