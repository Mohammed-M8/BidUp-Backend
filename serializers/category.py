from pydantic import BaseModel, ConfigDict


class CategorySchema(BaseModel):
    id: int
    name: str

    class Config():
        orm_mode=True