import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship
from models.base import BaseModel

class AuctionStatus(str, enum.Enum):
    ACTIVE = "active"
    ENDED = "ended"
    CANCELLED = "cancelled" 

class AuctionModel(BaseModel):
    __tablename__="auctions"

    id=Column(Integer,primary_key=True,index=True)
    product_name=Column(String,nullable=False)
    product_description=Column(String,nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)
    buy_now_price=Column(Float)
    starting_price=Column(Float,nullable=False)
    current_price=Column(Float,nullable=False)
    end_date=Column(DateTime(timezone=True),nullable=False)
    status = Column(Enum(AuctionStatus), default=AuctionStatus.ACTIVE, nullable=False, index=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(String, nullable=True)
    image_url=Column(String)
    image_public_id=Column(String)
    seller_id=Column(Integer,ForeignKey("users.id"),nullable=False)
    seller=relationship('UserModel',back_populates='auctions')
    bids=relationship('BidModel',back_populates='auction')
    category = relationship("CategoryModel", back_populates="auctions")
    ended_at = Column(DateTime(timezone=True), nullable=True)
