from datetime import datetime
from enum import Enum

from pydantic import BaseModel, computed_field

from models.auction import AuctionStatus
from serializers.auction import AuctionSchema, AuctionSummarySchema
from serializers.user import SellerSchema
from utils.time import utcnow

class BidStatus(str, Enum):
    LEADING = "leading"
    OUTBID = "outbid"
    WON = "won"
    LOST = "lost"
    CANCELLED = "cancelled"


class BidBase(BaseModel):
    id: int
    price: float
    bidder_id: int
    auction_id: int
    created_at: datetime

    class Config():
        orm_mode=True

class BidSchema(BidBase):
    bidder: SellerSchema | None = None


class UserBidSchema(BidBase):
    auction: AuctionSummarySchema
    @computed_field
    @property
    def status(self) -> BidStatus:
        auction = self.auction

        if auction.status == AuctionStatus.CANCELLED:
            return BidStatus.CANCELLED

        is_top_bid = self.price >= auction.current_price
        is_over = auction.status == AuctionStatus.ENDED or auction.end_date <= utcnow()

        if is_over:
            return BidStatus.WON if is_top_bid else BidStatus.LOST
        return BidStatus.LEADING if is_top_bid else BidStatus.OUTBID

class CreateBidSchema(BaseModel):
    price:float

    
