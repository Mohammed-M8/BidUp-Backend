from dotenv import load_dotenv
load_dotenv()
from database import SessionLocal
from models.auction import AuctionModel
from models.category import CategoryModel


NAMES = [
    "Electronics",
    "Fashion & Accessories",
    "Home & Garden",
    "Collectibles & Antiques",
    "Art",
    "Jewelry & Watches",
    "Vehicles & Parts",
    "Sports & Outdoors",
    "Toys & Games",
    "Books, Music & Movies",
    "Musical Instruments",
    "Other",
]
with SessionLocal() as db:
    existing = {name for (name,) in db.query(CategoryModel.name).all()}
    for name in NAMES:
        if name not in existing:
            db.add(CategoryModel(name=name))
    db.commit()
    print("done")