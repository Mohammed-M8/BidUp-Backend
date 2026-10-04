from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from models.base import BaseModel


class CategoryModel(BaseModel):

    __tablename__="categories"
    id=Column(Integer,primary_key=True,nullable=False)
    name=Column(String,nullable=False,unique=True)
    auctions=relationship("AuctionModel",back_populates="category")
