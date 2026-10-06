from datetime import datetime, timezone
from typing import Annotated

from fastapi import File, Form, UploadFile
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from models.auction import AuctionStatus
from serializers.category import CategorySchema
from serializers.user import SellerSchema
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
    seller: SellerSchema | None = None
    cancelled_at: datetime | None = None
    cancel_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    category_id: int | None = None
    category: CategorySchema | None = None

    class Config:
            orm_mode = True

class CreateAuctionSchema(BaseModel):
    product_name: str
    product_description: str
    buy_now_price: float | None = Field(default=None, gt=0)
    starting_price: float = Field(gt=0)
    end_date: datetime
    category_id: int | None = None

    @field_validator("end_date")
    @classmethod
    def end_date_in_future(cls, v: datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= utcnow():
            raise ValueError("end_date must be in the future")
        return v

    @model_validator(mode="after")
    def check_prices(self):
        if self.buy_now_price is not None and self.buy_now_price <= self.starting_price:
            raise ValueError("buy_now_price must be greater than starting_price")
        return self

    @classmethod
    def as_form(
        cls,
        product_name: Annotated[str, Form()],
        product_description: Annotated[str, Form()],
        starting_price: Annotated[float, Form()],
        end_date: Annotated[datetime, Form()],
        buy_now_price: Annotated[float | None, Form()] = None,
        category_id: Annotated[int | None, Form()] = None,
    ):
        try:
            return cls(
                product_name=product_name,
                product_description=product_description,
                starting_price=starting_price,
                end_date=end_date,
                buy_now_price=buy_now_price,
                category_id=category_id,
            )
        except ValidationError as e:
            raise RequestValidationError(e.errors(include_url=False, include_context=False))

class UpdateAuctionSchema(BaseModel):
    product_name: str | None = None
    product_description: str | None = None
    buy_now_price: float | None = Field(default=None, gt=0)
    end_date: datetime | None = None
    category_id: int | None = None

    @field_validator("end_date")
    @classmethod
    def end_date_in_future(cls, v: datetime | None):
        if v is None:
            return v
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= utcnow():
            raise ValueError("end_date must be in the future")
        return v
    
    @classmethod
    def as_form(
        cls,
        product_name: Annotated[str | None, Form()] = None,
        product_description: Annotated[str | None, Form()] = None,
        buy_now_price: Annotated[float | None, Form()] = None,
        end_date: Annotated[datetime | None, Form()] = None,
        category_id: Annotated[int | None, Form()] = None,
    ):
        try:
            return cls(
                product_name=product_name,
                product_description=product_description,
                buy_now_price=buy_now_price,
                end_date=end_date,
                category_id=category_id,
            )
        except ValidationError as e:
            raise RequestValidationError(e.errors(include_url=False, include_context=False))


class CancelAuctionSchema(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class AuctionSummarySchema(BaseModel):
    id: int
    product_name: str
    image_url: str | None
    current_price: float
    end_date: datetime
    status: AuctionStatus

    class Config():
        orm_mode=True






