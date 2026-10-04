from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.category import CategoryModel
from serializers.category import CategorySchema

router = APIRouter(prefix="/api/categories")


@router.get("", response_model=List[CategorySchema])
def get_all(db: Session = Depends(get_db)):
    return db.query(CategoryModel).order_by(CategoryModel.name).all()