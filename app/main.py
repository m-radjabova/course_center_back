from fastapi import FastAPI
from app.routers.user_router import router as users_router

app = FastAPI()

app.include_router(users_router)
