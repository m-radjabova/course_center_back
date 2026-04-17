from sqlalchemy import Boolean, Column, Date, Enum, ForeignKey, Integer, Numeric, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AttendanceStatus, EnrollmentStatus, LessonStatus, PaymentStatus


class GroupStudent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "group_students"

    group_id = Column(ForeignKey("course_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    enrolled_on = Column(Date, nullable=False)
    status = Column(
        Enum(EnrollmentStatus, name="enrollment_status"),
        nullable=False,
        default=EnrollmentStatus.ACTIVE,
    )

    group = relationship("CourseGroup", back_populates="students")
    student = relationship("User", back_populates="enrollments", foreign_keys=[student_id])
    attendances = relationship("LessonAttendance", back_populates="enrollment", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("group_id", "student_id", name="uq_group_student"),)


class Lesson(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lessons"

    group_id = Column(ForeignKey("course_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_id = Column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    lesson_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    topic = Column(String(255), nullable=True)
    order_index = Column(Integer, nullable=False, default=1, server_default="1")
    is_exam = Column(Boolean, nullable=False, default=False, server_default="false")
    homework = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(Enum(LessonStatus, name="lesson_status"), nullable=False, default=LessonStatus.PLANNED)

    group = relationship("CourseGroup", back_populates="lessons")
    teacher = relationship("User", back_populates="lessons", foreign_keys=[teacher_id])
    attendances = relationship("LessonAttendance", back_populates="lesson", cascade="all, delete-orphan")


class LessonAttendance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lesson_attendances"

    lesson_id = Column(ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    enrollment_id = Column(ForeignKey("group_students.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(
        Enum(AttendanceStatus, name="attendance_status"),
        nullable=False,
        default=AttendanceStatus.PRESENT,
    )
    homework_score = Column(Integer, nullable=True)
    exam_score = Column(Integer, nullable=True)
    comment = Column(Text, nullable=True)

    lesson = relationship("Lesson", back_populates="attendances")
    enrollment = relationship("GroupStudent", back_populates="attendances")
    student = relationship("User", back_populates="attendances")

    __table_args__ = (UniqueConstraint("lesson_id", "student_id", name="uq_lesson_student"),)


class MonthlyPayment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "monthly_payments"

    enrollment_id = Column(ForeignKey("group_students.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id = Column(ForeignKey("course_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    period_month = Column(Date, nullable=False, index=True)
    amount_due = Column(Numeric(12, 2), nullable=False, server_default="0")
    amount_paid = Column(Numeric(12, 2), nullable=False, server_default="0")
    status = Column(Enum(PaymentStatus, name="payment_status"), nullable=False, default=PaymentStatus.PENDING)
    note = Column(Text, nullable=True)

    enrollment = relationship("GroupStudent")
    student = relationship("User")
    group = relationship("CourseGroup")

    __table_args__ = (UniqueConstraint("enrollment_id", "period_month", name="uq_payment_enrollment_period"),)
