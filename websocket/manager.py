import asyncio
from collections import defaultdict

from fastapi import WebSocket
class ConnectionManager:
    def __init__(self):
        self.rooms:dict[int,set[WebSocket]]=defaultdict(set)


    async def connect(self,auction_id:int,websocket:WebSocket):
        await websocket.accept()
        self.rooms[auction_id].add(websocket)

    def disconnect(self,auction_id:int,websocket:WebSocket):
        self.rooms[auction_id].remove(websocket)

    async def close_room(self, auction_id: int, code: int = 4410):
        sockets = list(self.rooms.pop(auction_id, []))
        await asyncio.gather(
            *(ws.close(code=code) for ws in sockets),
            return_exceptions=True,
        )


    async def broadcast(self,auction_id:int,message:dict):
        rooms=self.rooms.get(auction_id,[])
        results= await asyncio.gather(*(websocket.send_json(message) for websocket in rooms),return_exceptions=True)

        for websocket,result in zip(rooms,results):
            if isinstance(result,Exception):
                self.disconnect(auction_id,websocket)

manager=ConnectionManager()
