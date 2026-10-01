from datetime import datetime

from pydantic import BaseModel


class AuctionSchema(BaseModel):
    id:int
    product_name:str
    product_description:str
    buy_now_price:float
    starting_price:float
    current_price:float
    end_date:datetime
    is_active:bool
    image_url:str
    seller_id:int

class CreateAuctionSchema(BaseModel):
    product_name:str
    product_description:str
    buy_now_price:float
    starting_price:float
    end_date:datetime

class UpdateAuctionSchema(BaseModel):
    product_name: str
    product_description: str
    buy_now_price: float
    end_date: datetime




