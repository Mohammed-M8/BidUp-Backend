import asyncio
from contextlib import asynccontextmanager
import os
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv

from tasks.auction_closer import auction_closer

load_dotenv()

from fastapi import FastAPI

# Controllers
from controllers.auth import router as AuthRouter
from controllers.users import router as UsersRouter
from controllers.auctions import router as AuctionsRouter
from controllers.bids import router as BidsRouter
from controllers.websockets import router as WebsocketsRouter

@asynccontextmanager
async def lifespan(app:FastAPI):
  task=asyncio.create_task(auction_closer())
  yield
  task.cancel()

app = FastAPI(lifespan=lifespan)

# ✅ Allow your React dev server(s) to call the API
origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,     # Which sites can call this API
    allow_methods=["*"],       # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],       # Allow all headers (e.g., Content-Type, Authorization)
)
app.include_router(AuthRouter)
app.include_router(UsersRouter)
app.include_router(AuctionsRouter)
app.include_router(BidsRouter)
app.include_router(WebsocketsRouter)

@app.get('/health')
def health_check():
  return {'message': 'Api is running'}

