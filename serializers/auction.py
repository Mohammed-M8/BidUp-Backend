from datetime import datetime
from typing import Annotated

from fastapi import File, Form, UploadFile
from pydantic import BaseModel, Field, field_validator, model_validator

from models.auction import AuctionStatus
from utils.time import utcnow


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
    product_name: Annotated[str, Form()]
    product_description: Annotated[str, Form()]
    buy_now_price: Annotated[float | None, Form()] = Field(default=None, gt=0)
    starting_price: Annotated[float, Form()] = Field(gt=0)
    end_date: Annotated[datetime, Form()]
    image: Annotated[UploadFile, File()]

    @field_validator("end_date")
    @classmethod
    def end_date_in_future(cls,v:datetime)->datetime:
         if v<=utcnow():
              raise ValueError("end_date must be in the future")
         return v

    @model_validator(mode="after")
    def check_prices(self):
        if self.buy_now_price is not None and self.buy_now_price <= self.starting_price:
            raise ValueError("buy_now_price must be greater than starting_price")
        return self
    
        

class UpdateAuctionSchema(BaseModel):
    product_name: Annotated[str|None,Form()] =None
    product_description: Annotated[str|None,Form()] =None
    buy_now_price: Annotated[float|None,Form()] =None
    end_date: Annotated[datetime|None,Form()] =None
    image:Annotated[UploadFile|None,File()]=None

    @field_validator("end_date")
    @classmethod
    def end_date_in_future(cls,v:datetime|None)->datetime|None:
         if v is not None and v<=utcnow():
              raise ValueError("end_date must be in the future")
         return v



class CancelAuctionSchema(BaseModel):
    reason: str = Field(min_length=3, max_length=500)




