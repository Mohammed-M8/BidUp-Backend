from sqlalchemy import Column, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship
from models.base import BaseModel


class BidModel(BaseModel):
    __tablename__="bids"

    id=Column(Integer,primary_key=True,nullable=False)
    price=Column(Float,nullable=False)
    bidder_id=Column(Integer,ForeignKey("users.id"),nullable=False)
    auction_id=Column(Integer,ForeignKey('auctions.id'),nullable=False)
    bidder=relationship('UserModel',back_populates='bids')
    auction=relationship('AuctionModel',back_populates='bids')
