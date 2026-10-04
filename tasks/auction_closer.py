import asyncio

from database import SessionLocal
from models.auction import AuctionModel, AuctionStatus
from utils.time import utcnow
from websocket.manager import manager


def close_expired_auctions() -> list[int]:
    with SessionLocal() as db:
        expired = db.query(AuctionModel).filter(
            AuctionModel.status == AuctionStatus.ACTIVE,
            AuctionModel.end_date <= utcnow(),
        ).all()
        ids = []
        for auction in expired:
            auction.status = AuctionStatus.ENDED  # type: ignore
            auction.ended_at = auction.end_date  # type: ignore
            ids.append(auction.id)
        db.commit()
        return ids  # type: ignore


async def auction_closer():
    while True:
        try:
            ids = await asyncio.to_thread(close_expired_auctions)
            for auction_id in ids:
                await manager.broadcast(auction_id, {"type": "auction_ended"})
                await manager.close_room(auction_id)
        except Exception as e:
            print("auction_closer error:", e)
        await asyncio.sleep(30)