from pydantic import BaseModel


class BidSchema(BaseModel):
    id:int
    price:float
    bidder_id:int
    auction_id:int

class CreateBidSchema(BaseModel):
    price:float
