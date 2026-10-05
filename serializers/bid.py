from pydantic import BaseModel

from serializers.auction import AuctionSchema, AuctionSummarySchema
from serializers.user import SellerSchema



class BidBase(BaseModel):
    id: int
    price: float
    bidder_id: int
    auction_id: int

    class Config():
        orm_mode=True

class BidSchema(BidBase):
    bidder: SellerSchema | None = None


class UserBidSchema(BidBase):
    auction: AuctionSummarySchema

class CreateBidSchema(BaseModel):
    price:float

    
