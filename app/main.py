from fastapi import FastAPI
import app.models
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers.user_router import router as users_router
from app.routers.auth_router import router as auth_router
from app.routers.product_router import router as product_router
from app.routers.category_router import router as category_router
from app.routers.carousel_router import router as carousel_router
from app.routers.order_router import router as order_router

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(product_router)
app.include_router(category_router)
app.include_router(carousel_router)
app.include_router(order_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)
