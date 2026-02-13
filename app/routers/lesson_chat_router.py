from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.lesson import Lesson
from app.models.lesson_chat import LessonChatMessage, LessonChatThread
from app.models.user import User
from app.schemas.lesson_chat import (
    LessonChatMessageCreate,
    LessonChatMessageOut,
    LessonChatMessageUpdate,
    LessonChatThreadOut,
)

from fastapi import WebSocket, WebSocketDisconnect
from app.realtime.lesson_chat_ws import manager
from app.core.jwt import decode_token

router = APIRouter(prefix="/lesson-chat", tags=["Lesson Chat"])


def _is_teacher_or_admin(user: User) -> bool:
    user_roles = set(user.roles or [])
    return "teacher" in user_roles or "admin" in user_roles


def _ensure_lesson_exists(db: Session, lesson_id: UUID) -> None:
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")


def _get_or_create_thread(db: Session, lesson_id: UUID, student_id: UUID) -> LessonChatThread:
    thread = (
        db.query(LessonChatThread)
        .filter(
            LessonChatThread.lesson_id == lesson_id,
            LessonChatThread.student_id == student_id,
        )
        .first()
    )
    if thread:
        return thread

    thread = LessonChatThread(lesson_id=lesson_id, student_id=student_id)
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread


def _ensure_thread_access(thread: LessonChatThread, user: User) -> None:
    if _is_teacher_or_admin(user):
        return
    if thread.student_id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")


def _serialize_message(message: LessonChatMessage) -> dict:
    return {
        "id": message.id,
        "thread_id": message.thread_id,
        "sender_id": message.sender_id,
        "sender_username": message.sender.username if message.sender else None,
        "text": message.text,
        "created_at": message.created_at,
    }


def _serialize_thread(thread: LessonChatThread) -> dict:
    return {
        "id": thread.id,
        "lesson_id": thread.lesson_id,
        "student_id": thread.student_id,
        "student_username": thread.student.username if thread.student else None,
        "created_at": thread.created_at,
    }


def _can_manage_message(message: LessonChatMessage, user: User) -> bool:
    if _is_teacher_or_admin(user):
        return True
    return message.sender_id == user.id


@router.get("/lessons/{lesson_id}/messages", response_model=list[LessonChatMessageOut])
def list_my_lesson_messages(
    lesson_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_lesson_exists(db, lesson_id)

    if _is_teacher_or_admin(current_user):
        raise HTTPException(
            status_code=400,
            detail="Teacher/admin must use thread-specific endpoint",
        )

    thread = (
        db.query(LessonChatThread)
        .filter(
            LessonChatThread.lesson_id == lesson_id,
            LessonChatThread.student_id == current_user.id,
        )
        .first()
    )
    if not thread:
        return []

    rows = (
        db.query(LessonChatMessage)
        .options(joinedload(LessonChatMessage.sender))
        .filter(LessonChatMessage.thread_id == thread.id)
        .order_by(LessonChatMessage.created_at.asc())
        .all()
    )
    return [_serialize_message(item) for item in rows]


@router.post(
    "/lessons/{lesson_id}/messages",
    response_model=LessonChatMessageOut,
    status_code=status.HTTP_201_CREATED,
)
def create_my_lesson_message(
    lesson_id: UUID,
    payload: LessonChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_lesson_exists(db, lesson_id)

    if _is_teacher_or_admin(current_user):
        raise HTTPException(
            status_code=400,
            detail="Teacher/admin must use thread-specific endpoint",
        )

    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message text is required")

    thread = _get_or_create_thread(db, lesson_id, current_user.id)

    message = LessonChatMessage(
        thread_id=thread.id,
        sender_id=current_user.id,
        text=text,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    message = (
        db.query(LessonChatMessage)
        .options(joinedload(LessonChatMessage.sender))
        .filter(LessonChatMessage.id == message.id)
        .first()
    )
    out = _serialize_message(message)

    import anyio
    anyio.from_thread.run(
        manager.broadcast,
        thread.id,
        {"type": "new_message", "data": out},
    )

    return out


@router.get("/lessons/{lesson_id}/threads", response_model=list[LessonChatThreadOut])
def list_lesson_threads(
    lesson_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_lesson_exists(db, lesson_id)
    if not _is_teacher_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Only teacher/admin can view threads")

    rows = (
        db.query(LessonChatThread)
        .options(joinedload(LessonChatThread.student))
        .filter(LessonChatThread.lesson_id == lesson_id)
        .order_by(LessonChatThread.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_serialize_thread(item) for item in rows]


@router.get("/threads/{thread_id}/messages", response_model=list[LessonChatMessageOut])
def list_thread_messages(
    thread_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    thread = (
        db.query(LessonChatThread)
        .filter(LessonChatThread.id == thread_id)
        .first()
    )
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    _ensure_thread_access(thread, current_user)

    rows = (
        db.query(LessonChatMessage)
        .options(joinedload(LessonChatMessage.sender))
        .filter(LessonChatMessage.thread_id == thread_id)
        .order_by(LessonChatMessage.created_at.asc())
        .all()
    )
    return [_serialize_message(item) for item in rows]

@router.post(
    "/threads/{thread_id}/messages",
    response_model=LessonChatMessageOut,
    status_code=status.HTTP_201_CREATED,
)
def create_thread_message(
    thread_id: UUID,
    payload: LessonChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    thread = (
        db.query(LessonChatThread)
        .filter(LessonChatThread.id == thread_id)
        .first()
    )
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    _ensure_thread_access(thread, current_user)

    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message text is required")

    message = LessonChatMessage(
        thread_id=thread.id,
        sender_id=current_user.id,
        text=text,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    message = (
        db.query(LessonChatMessage)
        .options(joinedload(LessonChatMessage.sender))
        .filter(LessonChatMessage.id == message.id)
        .first()
    )

    out = _serialize_message(message)

    import anyio
    anyio.from_thread.run(
        manager.broadcast,
        thread.id,
        {"type": "new_message", "data": out},
    )

    return out


@router.patch("/messages/{message_id}", response_model=LessonChatMessageOut)
def update_message(
    message_id: UUID,
    payload: LessonChatMessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = (
        db.query(LessonChatMessage)
        .options(
            joinedload(LessonChatMessage.sender),
            joinedload(LessonChatMessage.thread),
        )
        .filter(LessonChatMessage.id == message_id)
        .first()
    )
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    _ensure_thread_access(message.thread, current_user)
    if not _can_manage_message(message, current_user):
        raise HTTPException(status_code=403, detail="Permission denied")

    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message text is required")

    message.text = text
    db.commit()
    db.refresh(message)
    message = (
        db.query(LessonChatMessage)
        .options(joinedload(LessonChatMessage.sender))
        .filter(LessonChatMessage.id == message.id)
        .first()
    )
    out = _serialize_message(message)

    import anyio
    anyio.from_thread.run(
        manager.broadcast,
        message.thread_id,
        {"type": "message_updated", "data": out},
    )

    return out


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    message_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = (
        db.query(LessonChatMessage)
        .options(joinedload(LessonChatMessage.thread))
        .filter(LessonChatMessage.id == message_id)
        .first()
    )
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    _ensure_thread_access(message.thread, current_user)
    if not _can_manage_message(message, current_user):
        raise HTTPException(status_code=403, detail="Permission denied")

    thread_id = message.thread_id
    db.delete(message)
    db.commit()

    import anyio
    anyio.from_thread.run(
        manager.broadcast,
        thread_id,
        {"type": "message_deleted", "data": {"id": str(message_id), "thread_id": str(thread_id)}},
    )

    return None



@router.websocket("/ws/threads/{thread_id}")
async def websocket_thread_chat(
    websocket: WebSocket,
    thread_id: UUID,
    db: Session = Depends(get_db),
):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=1008)
        return

    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=1008)
        return

    try:
        user_uuid = UUID(user_id)
    except:
        await websocket.close(code=1008)
        return

    current_user = db.query(User).filter(User.id == user_uuid).first()
    if not current_user:
        await websocket.close(code=1008)
        return

    thread = db.query(LessonChatThread).filter(
        LessonChatThread.id == thread_id
    ).first()

    if not thread:
        await websocket.close(code=1008)
        return

    if not _is_teacher_or_admin(current_user):
        if thread.student_id != current_user.id:
            await websocket.close(code=1008)
            return

    await manager.connect(thread_id, websocket)

    try:
        while True:
            await websocket.receive_text() 
    except WebSocketDisconnect:
        manager.disconnect(thread_id, websocket)
