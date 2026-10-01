from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from models.auction import AuctionStatus


class AuctionSchema(BaseModel):
    id:int
    product_name:str
    product_description:str
    buy_now_price:float | None
    starting_price:float
    current_price:float
    end_date:datetime
    status: AuctionStatus
    image_url: str | None
    seller_id: int
    cancelled_at: datetime | None = None
    cancel_reason: str | None = None

    class Config:
            orm_mode = True

class CreateAuctionSchema(BaseModel):
    product_name:str
    product_description:str
    buy_now_price: float | None = Field(default=None, gt=0)
    starting_price:float =Field(gt=0)
    end_date:datetime

    @field_validator("end_date")
    @classmethod
    def end_date_in_future(cls,v:datetime)->datetime:
         if v<=datetime.now():
              raise ValueError("end_date must be in the future")
         return v

    @model_validator(mode="after")
    def check_prices(self):
        if self.buy_now_price is not None and self.buy_now_price <= self.starting_price:
            raise ValueError("buy_now_price must be greater than starting_price")
        return self
    
        

class UpdateAuctionSchema(BaseModel):
    product_name: str|None =None
    product_description: str|None=None
    buy_now_price: float|None=None
    end_date: datetime|None=None

    @field_validator("end_date")
    @classmethod
    def end_date_in_future(cls,v:datetime|None)->datetime|None:
         if v is not None and v<=datetime.now():
              raise ValueError("end_date must be in the future")
         return v



class CancelAuctionSchema(BaseModel):
    reason: str = Field(min_length=3, max_length=500)




