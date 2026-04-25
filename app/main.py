from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import (
    attendance_router,
    auth_router,
    course_centers_router,
    courses_router,
    grades_router,
    groups_router,
    lessons_router,
    payments_router,
    rooms_router,
    students_router,
    teachers_router,
    telegram_router,
    users_router,
)
from app.services.telegram_polling import telegram_polling_runner


app = FastAPI(title="Course Center API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(course_centers_router)
app.include_router(users_router)
app.include_router(teachers_router)
app.include_router(students_router)
app.include_router(telegram_router)
app.include_router(courses_router)
app.include_router(rooms_router)
app.include_router(groups_router)
app.include_router(lessons_router)
app.include_router(attendance_router)
app.include_router(grades_router)
app.include_router(payments_router)


@app.get("/health", tags=["Health"])
def healthcheck():
    return {"status": "ok"}


@app.on_event("startup")
async def start_telegram_polling():
    await telegram_polling_runner.start()


@app.on_event("shutdown")
async def stop_telegram_polling():
    await telegram_polling_runner.stop()
