from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.lesson import Lesson
from app.schemas.assingment import (
    AssignmentCreate, AssignmentOut, AssignmentUpdate,
    SubmissionCreate, SubmissionOut, GradeSubmission
)
from app.dependencies.auth import get_current_user  


router = APIRouter(prefix="/assignments", tags=["Assignments"])


def require_role(user, role: str):
    return user and user.roles and role in user.roles


def serialize_submission(submission: AssignmentSubmission) -> dict:
    return {
        "id": submission.id,
        "assignment_id": submission.assignment_id,
        "user_id": submission.user_id,
        "username": submission.user.username if submission.user else None,
        "text_answer": submission.text_answer,
        "file_url": submission.file_url,
        "status": submission.status,
        "score": submission.score,
        "submitted_at": submission.submitted_at,
        "graded_at": submission.graded_at,
    }


@router.post("/lessons/{lesson_id}", response_model=AssignmentOut)
def create_assignment(
    lesson_id: UUID,
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not (require_role(current_user, "teacher") or require_role(current_user, "admin")):
        raise HTTPException(status_code=403, detail="Only teacher/admin can create assignments")

    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    assignment = Assignment(
        lesson_id=lesson_id,
        title=payload.title,
        description=payload.description,
        order=payload.order,
        due_at=payload.due_at,
        max_score=payload.max_score,
        is_required=payload.is_required,
    )
    db.add(assignment)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Could not create assignment (maybe order conflict)")
    db.refresh(assignment)
    return assignment


@router.get("/lessons/{lesson_id}", response_model=list[AssignmentOut])
def list_assignments(
    lesson_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return (
        db.query(Assignment)
        .filter(Assignment.lesson_id == lesson_id)
        .order_by(Assignment.order.asc())
        .all()
    )


@router.patch("/{assignment_id}", response_model=AssignmentOut)
def update_assignment(
    assignment_id: UUID,
    payload: AssignmentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not (require_role(current_user, "teacher") or require_role(current_user, "admin")):
        raise HTTPException(status_code=403, detail="Only teacher/admin can update assignments")

    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(assignment, k, v)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Could not update assignment (maybe order conflict)")
    db.refresh(assignment)
    return assignment


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not (require_role(current_user, "teacher") or require_role(current_user, "admin")):
        raise HTTPException(status_code=403, detail="Only teacher/admin can delete assignments")

    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    db.delete(assignment)
    db.commit()
    return None


@router.post("/{assignment_id}/submit", response_model=SubmissionOut)
def submit_assignment(
    assignment_id: UUID,
    payload: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if not payload.text_answer and not payload.file_url:
        raise HTTPException(status_code=400, detail="Provide text_answer or file_url")

    submission = (
        db.query(AssignmentSubmission)
        .filter(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.user_id == current_user.id,
        )
        .first()
    )

    # agar oldin topshirgan bo‘lsa — update (re-submit)
    if submission:
        submission.text_answer = payload.text_answer
        submission.file_url = payload.file_url
        submission.status = "submitted"
        submission.score = None
        submission.graded_at = None
        submission.submitted_at = datetime.utcnow()
    else:
        submission = AssignmentSubmission(
            assignment_id=assignment_id,
            user_id=current_user.id,
            text_answer=payload.text_answer,
            file_url=payload.file_url,
        )
        db.add(submission)

    db.commit()
    db.refresh(submission)
    return serialize_submission(submission)


@router.get("/{assignment_id}/my-submission", response_model=SubmissionOut | None)
def get_my_submission(
    assignment_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    submission = (
        db.query(AssignmentSubmission)
        .filter(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.user_id == current_user.id,
        )
        .first()
    )
    if not submission:
        return None
    return serialize_submission(submission)


@router.get("/{assignment_id}/submissions", response_model=list[SubmissionOut])
def list_submissions(
    assignment_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not (require_role(current_user, "teacher") or require_role(current_user, "admin")):
        raise HTTPException(status_code=403, detail="Only teacher/admin can view submissions")

    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    submissions = (
        db.query(AssignmentSubmission)
        .options(joinedload(AssignmentSubmission.user))
        .filter(AssignmentSubmission.assignment_id == assignment_id)
        .order_by(AssignmentSubmission.submitted_at.desc())
        .all()
    )
    return [serialize_submission(item) for item in submissions]


@router.post("/submissions/{submission_id}/grade", response_model=SubmissionOut)
def grade_submission(
    submission_id: UUID,
    payload: GradeSubmission,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not (require_role(current_user, "teacher") or require_role(current_user, "admin")):
        raise HTTPException(status_code=403, detail="Only teacher/admin can grade submissions")

    submission = db.query(AssignmentSubmission).filter(AssignmentSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    submission.score = payload.score
    submission.status = payload.status
    submission.graded_at = datetime.utcnow()

    db.commit()
    db.refresh(submission)
    return serialize_submission(submission)
