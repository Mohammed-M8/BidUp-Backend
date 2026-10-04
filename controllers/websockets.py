import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from database import SessionLocal          # adjust to what your database.py exposes
from models.auction import AuctionModel, AuctionStatus
from utils.time import utcnow
from websocket.manager import manager

router = APIRouter(prefix="/ws")


def get_auction_state(auction_id: int) -> str:
    with SessionLocal() as db:
        auction = db.query(AuctionModel).filter(AuctionModel.id == auction_id).first()
        if not auction:
            return "missing"
        if auction.status != AuctionStatus.ACTIVE or auction.end_date <= utcnow():  # type: ignore
            return "closed"
        return "active"


@router.websocket("/{auction_id}")
async def auction_websocket(auction_id: int, websocket: WebSocket):
    state = await asyncio.to_thread(get_auction_state, auction_id)

    if state != "active":
        await websocket.accept()
        await websocket.close(code=4404 if state == "missing" else 4409)
        return

    await manager.connect(auction_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(auction_id, websocket)