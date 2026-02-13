from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers.user_router import router as users_router
from app.routers.auth_router import router as auth_router
from app.routers.category_router import router as category_router
from app.routers.course_router import router as course_router
from app.routers.lesson_router import router as lesson_router
from app.routers.assignments_router import router as assignments_router
from app.routers.progress_router import router as progress_router
from app.routers.lesson_chat_router import router as lesson_chat_router

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(category_router)
app.include_router(course_router)
app.include_router(lesson_router)
app.include_router(assignments_router)
app.include_router(progress_router)
app.include_router(lesson_chat_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
