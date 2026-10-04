import os
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI

# Controllers
from controllers.auth import router as AuthRouter
from controllers.users import router as UsersRouter
from controllers.auctions import router as AuctionsRouter
from controllers.bids import router as BidsRouter


app = FastAPI()

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

@app.get('/health')
def health_check():
  return {'message': 'Api is running'}

