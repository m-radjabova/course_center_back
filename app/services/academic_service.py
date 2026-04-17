from calendar import monthrange
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.academic import GroupStudent, Lesson, LessonAttendance, MonthlyPayment
from app.models.course import CourseGroup
from app.models.enums import AttendanceStatus, UserRole
from app.models.user import User
from app.schemas.course import (
    AttendanceCreate,
    AttendanceUpdate,
    EnrollmentCreate,
    EnrollmentUpdate,
    LessonCreate,
    LessonUpdate,
    MonthlyPaymentCreate,
    MonthlyPaymentUpdate,
)
from app.services.utils import parse_uuid


def _enrollment_query(db: Session):
    return db.query(GroupStudent).options(joinedload(GroupStudent.student))


def _lesson_query(db: Session):
    return db.query(Lesson).options(joinedload(Lesson.teacher))


def _attendance_query(db: Session):
    return db.query(LessonAttendance).options(joinedload(LessonAttendance.student))


def _payment_query(db: Session):
    return db.query(MonthlyPayment).options(joinedload(MonthlyPayment.student))


def list_group_students(db: Session, group_id: str):
    parsed_group_id = parse_uuid(group_id, "group id")
    return _enrollment_query(db).filter(GroupStudent.group_id == parsed_group_id).order_by(GroupStudent.created_at.desc()).all()


def enroll_student(db: Session, group_id: str, payload: EnrollmentCreate):
    parsed_group_id = parse_uuid(group_id, "group id")
    student_id = parse_uuid(payload.student_id, "student id")

    group = db.query(CourseGroup).filter(CourseGroup.id == parsed_group_id).first()
    if not group:
        return None

    student = db.query(User).filter(User.id == student_id, User.role == UserRole.USER).first()
    if not student:
        raise ValueError("Student not found")

    enrollment = GroupStudent(
        group_id=parsed_group_id,
        student_id=student_id,
        enrolled_on=payload.enrolled_on,
        status=payload.status,
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return _enrollment_query(db).filter(GroupStudent.id == enrollment.id).first()


def update_enrollment(db: Session, enrollment_id: str, payload: EnrollmentUpdate):
    enrollment = _enrollment_query(db).filter(GroupStudent.id == parse_uuid(enrollment_id, "enrollment id")).first()
    if not enrollment:
        return None
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(enrollment, field, value)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return _enrollment_query(db).filter(GroupStudent.id == enrollment.id).first()


def create_lesson(db: Session, payload: LessonCreate):
    group = db.query(CourseGroup).filter(CourseGroup.id == parse_uuid(payload.group_id, "group id")).first()
    if not group:
        raise ValueError("Group not found")

    teacher_id = parse_uuid(payload.teacher_id, "teacher id") if payload.teacher_id else None
    if teacher_id:
        teacher = db.query(User).filter(User.id == teacher_id, User.role == UserRole.TEACHER).first()
        if not teacher:
            raise ValueError("Teacher not found")

    lesson = Lesson(
        group_id=group.id,
        teacher_id=teacher_id,
        lesson_date=payload.lesson_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        order_index=payload.order_index,
        is_exam=payload.is_exam,
        topic=payload.topic,
        homework=payload.homework,
        notes=payload.notes,
        status=payload.status,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return _lesson_query(db).filter(Lesson.id == lesson.id).first()


def list_lessons(db: Session, group_id: str | None = None):
    query = _lesson_query(db)
    if group_id:
        query = query.filter(Lesson.group_id == parse_uuid(group_id, "group id"))
    return query.order_by(Lesson.lesson_date.desc()).all()


def update_lesson(db: Session, lesson_id: str, payload: LessonUpdate):
    lesson = _lesson_query(db).filter(Lesson.id == parse_uuid(lesson_id, "lesson id")).first()
    if not lesson:
        return None
    data = payload.model_dump(exclude_unset=True)
    if "teacher_id" in data:
        lesson.teacher_id = parse_uuid(data["teacher_id"], "teacher id") if data["teacher_id"] else None
        if lesson.teacher_id:
            teacher = db.query(User).filter(User.id == lesson.teacher_id, User.role == UserRole.TEACHER).first()
            if not teacher:
                raise ValueError("Teacher not found")
        del data["teacher_id"]
    for field, value in data.items():
        setattr(lesson, field, value)
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return _lesson_query(db).filter(Lesson.id == lesson.id).first()


def add_attendance(db: Session, lesson_id: str, payload: AttendanceCreate):
    parsed_lesson_id = parse_uuid(lesson_id, "lesson id")
    parsed_enrollment_id = parse_uuid(payload.enrollment_id, "enrollment id")
    parsed_student_id = parse_uuid(payload.student_id, "student id")

    lesson = db.query(Lesson).filter(Lesson.id == parsed_lesson_id).first()
    if not lesson:
        raise ValueError("Lesson not found")

    enrollment = db.query(GroupStudent).filter(GroupStudent.id == parsed_enrollment_id).first()
    if not enrollment:
        raise ValueError("Enrollment not found")
    if enrollment.student_id != parsed_student_id:
        raise ValueError("Enrollment and student do not match")
    if enrollment.group_id != lesson.group_id:
        raise ValueError("Student is not enrolled in this lesson's group")

    attendance = LessonAttendance(
        lesson_id=parsed_lesson_id,
        enrollment_id=parsed_enrollment_id,
        student_id=parsed_student_id,
        status=payload.status,
        homework_score=payload.homework_score,
        exam_score=payload.exam_score,
        comment=payload.comment,
    )
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return _attendance_query(db).filter(LessonAttendance.id == attendance.id).first()


def list_attendance(db: Session, lesson_id: str):
    return _attendance_query(db).filter(LessonAttendance.lesson_id == parse_uuid(lesson_id, "lesson id")).all()


def update_attendance(db: Session, attendance_id: str, payload: AttendanceUpdate):
    attendance = _attendance_query(db).filter(
        LessonAttendance.id == parse_uuid(attendance_id, "attendance id")
    ).first()
    if not attendance:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(attendance, field, value)
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return _attendance_query(db).filter(LessonAttendance.id == attendance.id).first()


def list_monthly_payments(db: Session, group_id: str | None = None, year: int | None = None, month: int | None = None):
    query = _payment_query(db)
    if group_id:
        query = query.filter(MonthlyPayment.group_id == parse_uuid(group_id, "group id"))
    if year and month:
        period_start = date(year, month, 1)
        query = query.filter(MonthlyPayment.period_month == period_start)
    return query.order_by(MonthlyPayment.period_month.desc(), MonthlyPayment.created_at.desc()).all()


def create_monthly_payment(db: Session, group_id: str, payload: MonthlyPaymentCreate):
    parsed_group_id = parse_uuid(group_id, "group id")
    parsed_enrollment_id = parse_uuid(payload.enrollment_id, "enrollment id")
    parsed_student_id = parse_uuid(payload.student_id, "student id")

    enrollment = db.query(GroupStudent).filter(GroupStudent.id == parsed_enrollment_id).first()
    if not enrollment:
        raise ValueError("Enrollment not found")
    if enrollment.group_id != parsed_group_id or enrollment.student_id != parsed_student_id:
        raise ValueError("Payment data does not match enrollment")

    payment = MonthlyPayment(
        enrollment_id=parsed_enrollment_id,
        student_id=parsed_student_id,
        group_id=parsed_group_id,
        period_month=date(payload.period_month.year, payload.period_month.month, 1),
        amount_due=payload.amount_due,
        amount_paid=payload.amount_paid,
        status=payload.status,
        note=payload.note,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return _payment_query(db).filter(MonthlyPayment.id == payment.id).first()


def update_monthly_payment(db: Session, payment_id: str, payload: MonthlyPaymentUpdate):
    payment = _payment_query(db).filter(MonthlyPayment.id == parse_uuid(payment_id, "payment id")).first()
    if not payment:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(payment, field, value)
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return _payment_query(db).filter(MonthlyPayment.id == payment.id).first()


def get_student_monthly_journal(db: Session, group_id: str, student_id: str, year: int, month: int):
    parsed_group_id = parse_uuid(group_id, "group id")
    parsed_student_id = parse_uuid(student_id, "student id")
    period_start = date(year, month, 1)
    period_end = date(year, month, monthrange(year, month)[1])

    enrollment = _enrollment_query(db).filter(
        GroupStudent.group_id == parsed_group_id,
        GroupStudent.student_id == parsed_student_id,
    ).first()
    if not enrollment:
        return None

    lessons = _lesson_query(db).filter(
        Lesson.group_id == parsed_group_id,
        Lesson.lesson_date >= period_start,
        Lesson.lesson_date <= period_end,
    ).order_by(Lesson.lesson_date.asc(), Lesson.order_index.asc()).all()

    attendances = _attendance_query(db).filter(
        LessonAttendance.enrollment_id == enrollment.id,
        LessonAttendance.lesson_id.in_([lesson.id for lesson in lessons]) if lessons else False,
    ).all()
    attendance_map = {attendance.lesson_id: attendance for attendance in attendances}

    lesson_rows = []
    attendance_summary = {status.value: 0 for status in AttendanceStatus}
    homework_scores: list[int] = []
    exam_scores: list[int] = []

    for lesson in lessons:
        attendance = attendance_map.get(lesson.id)
        if attendance:
            attendance_summary[attendance.status.value] += 1
            if attendance.homework_score is not None:
                homework_scores.append(attendance.homework_score)
            if attendance.exam_score is not None:
                exam_scores.append(attendance.exam_score)

        lesson_rows.append(
            {
                "lesson_id": lesson.id,
                "lesson_date": lesson.lesson_date,
                "order_index": lesson.order_index,
                "topic": lesson.topic,
                "is_exam": lesson.is_exam,
                "attendance_status": attendance.status if attendance else None,
                "homework_score": attendance.homework_score if attendance else None,
                "exam_score": attendance.exam_score if attendance else None,
                "comment": attendance.comment if attendance else None,
            }
        )

    payments = _payment_query(db).filter(
        MonthlyPayment.enrollment_id == enrollment.id,
        MonthlyPayment.period_month == period_start,
    ).order_by(MonthlyPayment.created_at.desc()).all()

    return {
        "student": enrollment.student,
        "group_id": parsed_group_id,
        "year": year,
        "month": month,
        "lessons": lesson_rows,
        "attendance_summary": attendance_summary,
        "average_homework_score": round(sum(homework_scores) / len(homework_scores), 2) if homework_scores else None,
        "average_exam_score": round(sum(exam_scores) / len(exam_scores), 2) if exam_scores else None,
        "payments": payments,
    }
