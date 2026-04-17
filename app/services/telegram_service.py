from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, timezone, timedelta
from secrets import token_urlsafe

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import settings
from app.core.security import hash_password
from app.models.attendance import Attendance
from app.models.enrollment import Enrollment
from app.models.enums import EnrollmentStatus
from app.models.grade import Grade
from app.models.group import Group
from app.models.lesson import Lesson
from app.models.payment import Payment
from app.models.profile import StudentProfile
from app.models.user import User
from app.services.base import BaseService, parse_uuid


MENU_COURSES = "📚 Kurslarim"
MENU_SCHEDULE = "🗓 Jadvalim"
MENU_PAYMENTS = "💳 To'lovlarim"
MENU_GRADES = "📊 Baholarim"
MENU_HOMEWORK = "📝 Vazifalarim"

TELEGRAM_MENU_KEYBOARD = {
    "keyboard": [
        [{"text": MENU_COURSES}, {"text": MENU_SCHEDULE}],
        [{"text": MENU_PAYMENTS}, {"text": MENU_GRADES}],
        [{"text": MENU_HOMEWORK}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}


class TelegramService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.bot_username = settings.TELEGRAM_BOT_USERNAME

    def is_enabled(self) -> bool:
        return bool(self.token and self.bot_username)

    def _api_url(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self.token}/{method}"

    def _raise_if_disabled(self) -> None:
        if not self.token:
            raise self.bad_request("TELEGRAM_BOT_TOKEN is not configured")
        if not self.bot_username:
            raise self.bad_request("TELEGRAM_BOT_USERNAME is not configured")

    def _format_money(self, amount: float | int | None) -> str:
        if amount is None:
            return "Kiritilmagan"
        return f"{int(amount):,}".replace(",", " ") + " so'm"

    def _format_date(self, value: datetime | None) -> str:
        if value is None:
            return "Kiritilmagan"
        return value.strftime("%d.%m.%Y")

    def _format_plain_date(self, value) -> str:
        if value is None:
            return "Kiritilmagan"
        return value.strftime("%d.%m.%Y")

    def _format_room(self, group: Group | None) -> str:
        if not group or not group.room:
            return "Biriktirilmagan"

        details = [group.room.name]
        if group.room.capacity:
            details.append(f"{group.room.capacity} ta joy")
        if group.room.location_note:
            details.append(group.room.location_note)
        return " | ".join(details)

    def _format_grade_percentage(self, score) -> str:
        if score is None:
            return "Kiritilmagan"
        try:
            normalized_score = Decimal(str(score)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            return f"{int(normalized_score)}%"
        except (InvalidOperation, ValueError, TypeError):
            return f"{score}%"

    def _first_name(self, user: User | None, fallback: str = "do'stim") -> str:
        if not user or not user.full_name:
            return fallback
        return user.full_name.split(" ")[0]

    def _post_to_telegram(self, method: str, payload: dict) -> dict:
        self._raise_if_disabled()
        response = httpx.post(self._api_url(method), json=payload, timeout=15.0)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise self.bad_request(data.get("description", "Telegram API request failed"))
        return data

    def _get_student_profile(self, user_id: str) -> StudentProfile:
        student = self.db.execute(
            select(User)
            .options(selectinload(User.student_profile))
            .where(User.id == parse_uuid(user_id, "student id"))
        ).scalar_one_or_none()
        if not student or not student.student_profile:
            raise self.not_found("Student profile")
        return student.student_profile

    def _get_student_by_chat_id(self, chat_id: str) -> User | None:
        return self.db.execute(
            select(User)
            .join(User.student_profile)
            .options(
                selectinload(User.student_profile),
                selectinload(User.enrollments)
                .joinedload(Enrollment.group)
                .joinedload(Group.course),
                selectinload(User.enrollments)
                .joinedload(Enrollment.group)
                .joinedload(Group.teacher),
                selectinload(User.enrollments)
                .joinedload(Enrollment.group)
                .joinedload(Group.room),
            )
            .where(StudentProfile.telegram_chat_id == chat_id)
        ).scalar_one_or_none()

    def _get_active_enrollments(self, student_id: str) -> list[Enrollment]:
        return list(
            self.db.execute(
                select(Enrollment)
                .options(
                    joinedload(Enrollment.group).joinedload(Group.course),
                    joinedload(Enrollment.group).joinedload(Group.teacher),
                    joinedload(Enrollment.group).joinedload(Group.room),
                )
                .where(Enrollment.student_id == parse_uuid(student_id, "student id"))
                .where(Enrollment.status == EnrollmentStatus.ACTIVE)
                .order_by(Enrollment.enrolled_at.desc())
            ).scalars().unique()
        )

    def _get_relevant_lessons(self, student_id: str, limit: int = 8) -> list[Lesson]:
        enrollments = self._get_active_enrollments(student_id)
        if not enrollments:
            return []

        lessons: list[Lesson] = []
        for enrollment in enrollments:
            group_lessons = list(
                self.db.execute(
                    select(Lesson)
                    .options(
                        joinedload(Lesson.group).joinedload(Group.course),
                        joinedload(Lesson.group).joinedload(Group.room),
                    )
                    .where(Lesson.group_id == enrollment.group_id)
                    .where(Lesson.lesson_date >= enrollment.enrolled_at)
                    .order_by(Lesson.lesson_date.desc(), Lesson.lesson_number.desc())
                    .limit(limit)
                ).scalars().unique()
            )
            if enrollment.left_at:
                group_lessons = [lesson for lesson in group_lessons if lesson.lesson_date <= enrollment.left_at]
            lessons.extend(group_lessons)

        lessons.sort(key=lambda lesson: (lesson.lesson_date, lesson.lesson_number), reverse=True)
        unique_lessons: dict[str, Lesson] = {}
        for lesson in lessons:
            unique_lessons.setdefault(str(lesson.id), lesson)
        return list(unique_lessons.values())[:limit]

    def _get_recent_grades(self, student_id: str, limit: int = 8) -> list[Grade]:
        enrollments = self._get_active_enrollments(student_id)
        enrollment_ids = [enrollment.id for enrollment in enrollments]
        if not enrollment_ids:
            return []
        return list(
            self.db.execute(
                select(Grade)
                .options(
                    joinedload(Grade.lesson).joinedload(Lesson.group),
                    joinedload(Grade.lesson).joinedload(Lesson.group).joinedload(Group.room),
                    joinedload(Grade.teacher),
                )
                .where(Grade.student_id == parse_uuid(student_id, "student id"))
                .where(Grade.enrollment_id.in_(enrollment_ids))
                .order_by(Grade.created_at.desc())
                .limit(limit)
            ).scalars().unique()
        )

    def _get_recent_payments(self, student_id: str, limit: int = 8) -> list[Payment]:
        return list(
            self.db.execute(
                select(Payment)
                .options(
                    joinedload(Payment.group).joinedload(Group.course),
                    joinedload(Payment.group).joinedload(Group.room),
                )
                .where(Payment.student_id == parse_uuid(student_id, "student id"))
                .order_by(Payment.paid_at.desc())
                .limit(limit)
            ).scalars().unique()
        )

    def generate_student_link(self, user_id: str) -> dict:
        profile = self._get_student_profile(user_id)
        self._raise_if_disabled()

        now = datetime.now(timezone.utc)
        token = token_urlsafe(24)
        profile.telegram_link_token = token
        profile.telegram_link_token_expires_at = now + timedelta(minutes=settings.TELEGRAM_LINK_EXPIRE_MINUTES)
        self.db.add(profile)
        self.commit()

        return {
            "bot_username": self.bot_username,
            "link_token": token,
            "telegram_link_url": f"https://t.me/{self.bot_username}?start=link_{token}",
            "token_expires_at": profile.telegram_link_token_expires_at,
            "is_connected": bool(profile.telegram_chat_id),
            "telegram_username": profile.telegram_username,
            "telegram_first_name": profile.telegram_first_name,
            "telegram_connected_at": profile.telegram_connected_at,
        }

    def get_student_link_status(self, user_id: str) -> dict:
        profile = self._get_student_profile(user_id)
        link_token = profile.telegram_link_token
        link_url = f"https://t.me/{self.bot_username}?start=link_{link_token}" if self.bot_username and link_token else None
        return {
            "bot_username": self.bot_username or None,
            "link_token": link_token,
            "telegram_link_url": link_url,
            "token_expires_at": profile.telegram_link_token_expires_at,
            "is_connected": bool(profile.telegram_chat_id),
            "telegram_username": profile.telegram_username,
            "telegram_first_name": profile.telegram_first_name,
            "telegram_connected_at": profile.telegram_connected_at,
        }

    def send_credentials(self, user_id: str, temporary_password: str | None = None) -> dict:
        profile = self._get_student_profile(user_id)
        user = self.db.get(User, parse_uuid(user_id, "student id"))
        if not user:
            raise self.not_found("Student")
        if not profile.telegram_chat_id:
            raise self.bad_request("Student has not linked Telegram yet")

        temp_password = temporary_password or f"12345678"
        user.password_hash = hash_password(temp_password)
        profile.telegram_last_credentials_sent_at = datetime.now(timezone.utc)
        self.db.add(user)
        self.db.add(profile)
        self.commit()

        message = (
            f"Assalomu alaykum, {self._first_name(user)}! 👋\n\n"
            "🎓 Course Center ga xush kelibsiz.\n"
            "Siz uchun yangi student akkaunti tayyorlandi.\n\n"
            "🔐 Kirish ma'lumotlari\n"
            f"• Login: {user.email}\n"
            f"• Parol: {temp_password}\n\n"
            "🌐 Shaxsiy kabinet manzili\n"
            f"{settings.APP_LOGIN_URL}\n\n"
            "⚠️ Xavfsizlik uchun tizimga kirgach parolni darhol yangilashingizni tavsiya qilamiz.\n\n"
            "💬 Savol tug'ilsa, admin bilan bemalol bog'lanishingiz mumkin."
        )
        self.send_message(profile.telegram_chat_id, message, TELEGRAM_MENU_KEYBOARD)
        return {
            "delivered": True,
            "chat_id": profile.telegram_chat_id,
            "sent_at": profile.telegram_last_credentials_sent_at,
        }

    def send_message(self, chat_id: str, text: str, reply_markup: dict | None = None) -> None:
        payload: dict = {"chat_id": chat_id, "text": text}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        self._post_to_telegram("sendMessage", payload)

    def set_webhook(self, public_base_url: str) -> dict:
        self._raise_if_disabled()
        base_url = public_base_url.rstrip("/")
        webhook_url = f"{base_url}/telegram/webhook"
        payload = {"url": webhook_url}
        if settings.TELEGRAM_WEBHOOK_SECRET:
            payload["secret_token"] = settings.TELEGRAM_WEBHOOK_SECRET
        telegram_response = self._post_to_telegram("setWebhook", payload)
        return {
            "ok": bool(telegram_response.get("ok")),
            "description": telegram_response.get("description"),
            "webhook_url": webhook_url,
        }

    def handle_webhook(self, update: dict) -> dict:
        message = update.get("message") or update.get("edited_message")
        if not message:
            return {"ok": True}

        chat = message.get("chat") or {}
        chat_id = str(chat.get("id", "")).strip()
        if not chat_id:
            return {"ok": True}

        text = (message.get("text") or "").strip()
        telegram_username = message.get("from", {}).get("username")
        telegram_first_name = message.get("from", {}).get("first_name")

        if text.startswith("/start"):
            parts = text.split(maxsplit=1)
            payload = parts[1].strip() if len(parts) > 1 else ""
            if payload.startswith("link_"):
                return self._handle_link_start(
                    chat_id=chat_id,
                    link_token=payload.removeprefix("link_"),
                    telegram_username=telegram_username,
                    telegram_first_name=telegram_first_name,
                )
            linked_student = self._get_student_by_chat_id(chat_id)
            if linked_student:
                self.send_message(
                    chat_id,
                    (
                        f"Assalomu alaykum, {self._first_name(linked_student)}! 👋\n\n"
                        "🤖 Bot sizning akkauntingizga ulangan.\n"
                        "Pastdagi menyu orqali kurslar, jadval, baholar, vazifalar va to'lovlarni qulay ko'rishingiz mumkin."
                    ),
                    TELEGRAM_MENU_KEYBOARD,
                )
            else:
                self.send_message(
                    chat_id,
                    (
                        "🔗 Akkauntingiz hali ulanmagan.\n\n"
                        "Admin yuborgan maxsus link yoki QR orqali botni student profilingizga ulang,"
                        " shundan keyin barcha ma'lumotlar shu yerda chiqadi."
                    ),
                )
            return {"ok": True}

        student = self._get_student_by_chat_id(chat_id)
        if not student:
            self.send_message(
                chat_id,
                (
                    "🚫 Avval botni student akkauntingizga ulashingiz kerak.\n\n"
                    "Buning uchun admin bergan link yoki QR koddan foydalaning."
                ),
            )
            return {"ok": True}

        handlers = {
            MENU_COURSES: self._build_courses_text,
            MENU_SCHEDULE: self._build_schedule_text,
            MENU_PAYMENTS: self._build_payments_text,
            MENU_GRADES: self._build_grades_text,
            MENU_HOMEWORK: self._build_homework_text,
        }
        handler = handlers.get(text)
        if handler is None:
            self.send_message(
                chat_id,
                (
                    "👇 Quyidagi menyudan kerakli bo'limni tanlang:\n"
                    f"{MENU_COURSES}\n"
                    f"{MENU_SCHEDULE}\n"
                    f"{MENU_PAYMENTS}\n"
                    f"{MENU_GRADES}\n"
                    f"{MENU_HOMEWORK}"
                ),
                TELEGRAM_MENU_KEYBOARD,
            )
            return {"ok": True}

        self.send_message(chat_id, handler(student), TELEGRAM_MENU_KEYBOARD)
        return {"ok": True}

    def _handle_link_start(
        self,
        *,
        chat_id: str,
        link_token: str,
        telegram_username: str | None,
        telegram_first_name: str | None,
    ) -> dict:
        now = datetime.now(timezone.utc)
        profile = self.db.execute(
            select(StudentProfile)
            .options(joinedload(StudentProfile.user))
            .where(StudentProfile.telegram_link_token == link_token)
        ).scalar_one_or_none()
        if not profile:
            self.send_message(
                chat_id,
                "❌ Ulanish havolasi topilmadi yoki noto'g'ri. Admin bilan bog'lanib, yangi link olib ko'ring.",
            )
            return {"ok": True}
        if not profile.telegram_link_token_expires_at or profile.telegram_link_token_expires_at < now:
            self.send_message(
                chat_id,
                "⏳ Ulanish havolasining muddati tugagan. Admin sizga yangi QR yoki link yuborishi kerak.",
            )
            return {"ok": True}

        duplicate_profile = self.db.execute(
            select(StudentProfile).where(
                StudentProfile.telegram_chat_id == chat_id,
                StudentProfile.user_id != profile.user_id,
            )
        ).scalar_one_or_none()
        if duplicate_profile:
            duplicate_profile.telegram_chat_id = None
            duplicate_profile.telegram_username = None
            duplicate_profile.telegram_first_name = None
            duplicate_profile.telegram_connected_at = None
            self.db.add(duplicate_profile)

        profile.telegram_chat_id = chat_id
        profile.telegram_username = telegram_username
        profile.telegram_first_name = telegram_first_name
        profile.telegram_connected_at = now
        profile.telegram_link_token = None
        profile.telegram_link_token_expires_at = None
        self.db.add(profile)
        self.commit()

        student_name = self._first_name(profile.user, "student")
        self.send_message(
            chat_id,
            (
                f"Tabriklaymiz, {student_name}! 🎉\n\n"
                "Telegram bot student akkauntingizga muvaffaqiyatli ulandi.\n"
                "Endi admin sizga login va vaqtinchalik parol yuborishi mumkin."
            ),
            TELEGRAM_MENU_KEYBOARD,
        )
        return {"ok": True}

    def _build_courses_text(self, student: User) -> str:
        enrollments = self._get_active_enrollments(str(student.id))

        if not enrollments:
            return (
                "📚 *Sizning kurslaringiz*\n\n"
                "Hozircha faol kurs topilmadi."
            )

        blocks = []

        for enrollment in enrollments:
            group = enrollment.group
            course_name = group.course.name if group and group.course else "Kurs"
            teacher_name = group.teacher.full_name if group and group.teacher else "Biriktirilmagan"

            blocks.append(
                "\n".join([
                    f"📘 *{course_name}*",
                    "",
                    f"👥 Guruh: {group.name}",
                    f"👨‍🏫 O‘qituvchi: {teacher_name}",
                    f"🏫 Xona: {self._format_room(group)}",
                    "",
                    f"🗓 Jadval:",
                    f"{group.schedule_summary or 'Kiritilmagan'}",
                    "",
                    f"💰 Oylik to‘lov: {self._format_money(group.monthly_fee)}",
                ])
            )

        return "📚 *Sizning kurslaringiz*\n\n" + "\n\n━━━━━━━━━━━━━━━\n\n".join(blocks)

    def _build_schedule_text(self, student: User) -> str:
        enrollments = self._get_active_enrollments(str(student.id))

        if not enrollments:
            return (
                "🗓 *Jadvalim*\n\n"
                "Hozircha faol jadval topilmadi.\n\n"
                "📌 Jadval kiritilgach, shu yerda ko‘rinadi."
            )

        blocks = []

        for enrollment in enrollments:
            group = enrollment.group
            schedule = group.schedule_summary or "Jadval kiritilmagan"

            blocks.append(
                "\n".join([
                    f"📘 *{group.name}*",
                    "",
                    "🗓 *Dars vaqti:*",
                    f"{schedule}",
                    "",
                    f"🏫 *Xona:* {self._format_room(group)}",
                ])
            )

        return "🗓 *Sizning jadvalingiz*\n\n" + "\n\n━━━━━━━━━━━━━━━\n\n".join(blocks)
    def _build_grades_text(self, student: User) -> str:
        enrollments = self._get_active_enrollments(str(student.id))
        grades = self._get_recent_grades(str(student.id))

        if not grades:
            if not enrollments:
                return (
                    "📊 *Baholarim*\n\n"
                    "Hozircha siz uchun baho qo‘yilmagan.\n\n"
                    "📌 Yangi baholar shu yerda ko‘rinadi."
                )

            group_rows = [
                f"• {enrollment.group.name} ({enrollment.group.course.name})"
                for enrollment in enrollments
            ]

            return (
                "📊 *Baholarim*\n\n"
                "Hozircha siz uchun baho qo‘yilmagan.\n\n"
                "🎓 *Faol guruhlaringiz:*\n"
                + "\n".join(group_rows)
                + "\n\n📌 Yangi baho qo‘yilgach, bu yerda fan va izoh bilan chiqadi."
            )

        blocks = []

        for grade in grades:
            lesson_title = grade.lesson.topic or f"{grade.lesson.lesson_number}-dars"

            blocks.append(
                "\n".join([
                    f"📘 *{grade.lesson.group.name}*",
                    "",
                    f"📚 *Dars:* {lesson_title}",
                    "",
                    f"⭐ *Baho:* {self._format_grade_percentage(grade.score)}",
                    "",
                    f"📝 *Izoh:* {grade.note or 'Izoh yo‘q'}",
                ])
            )

        return "📊 *So‘nggi baholaringiz*\n\n" + "\n\n━━━━━━━━━━━━━━━\n\n".join(blocks)

    def _build_homework_text(self, student: User) -> str:
        recent_lessons = self._get_relevant_lessons(str(student.id))
        lessons = [lesson for lesson in recent_lessons if lesson.homework]

        if not lessons:
            if not recent_lessons:
                return (
                    "📝 *Vazifalarim*\n\n"
                    "Hozircha siz uchun vazifa topilmadi.\n\n"
                    "📌 Vazifa kiritilgach, shu yerda ko‘rinadi."
                )

            lesson_rows = []

            for lesson in recent_lessons[:5]:
                title = lesson.topic or f"{lesson.lesson_number}-dars"

                lesson_rows.append(
                    "\n".join([
                        f"📘 *{lesson.group.name}*",
                        "",
                        f"📚 *Dars:* {title}",
                        "",
                        f"📅 *Sana:* {self._format_plain_date(lesson.lesson_date)}",
                        "",
                        f"🏫 *Xona:* {self._format_room(lesson.group)}",
                        "",
                        "⚠️ *Vazifa:* hali kiritilmagan",
                    ])
                )

            return "📝 *So‘nggi darslar bo‘yicha holat*\n\n" + "\n\n━━━━━━━━━━━━━━━\n\n".join(lesson_rows)

        blocks = []

        for lesson in lessons[:8]:
            title = lesson.topic or f"{lesson.lesson_number}-dars"

            blocks.append(
                "\n".join([
                    f"📘 *{lesson.group.name}*",
                    "",
                    f"📚 *Dars:* {title}",
                    "",
                    f"📅 *Sana:* {self._format_plain_date(lesson.lesson_date)}",
                    "",
                    f"🏫 *Xona:* {self._format_room(lesson.group)}",
                    "",
                    "📝 *Vazifa:*",
                    f"{lesson.homework}",
                ])
            )

        return "📝 *So‘nggi vazifalar*\n\n" + "\n\n━━━━━━━━━━━━━━━\n\n".join(blocks)

    def _build_payments_text(self, student: User) -> str:
        enrollments = self._get_active_enrollments(str(student.id))
        payments = self._get_recent_payments(str(student.id))

        if not payments:
            if not enrollments:
                return (
                    "💳 *To‘lovlarim*\n\n"
                    "Hozircha to‘lov ma’lumotlari topilmadi."
                )

            blocks = []

            for enrollment in enrollments:
                group = enrollment.group

                blocks.append(
                    "\n".join([
                        f"📘 *{group.name}*",
                        "",
                        f"💰 *Oylik to‘lov:* {self._format_money(group.monthly_fee)}",
                        "",
                        "⚠️ *Holat:* hali to‘lov kiritilmagan",
                    ])
                )

            return "💳 *Sizning to‘lov holatingiz*\n\n" + "\n\n━━━━━━━━━━━━━━━\n\n".join(blocks)

        blocks = []

        for payment in payments:
            blocks.append(
                "\n".join([
                    f"💰 *{payment.group.name}*",
                    "",
                    f"💵 *Summa:* {self._format_money(payment.amount)}",
                    "",
                    f"📅 *Sana:* {self._format_date(payment.paid_at)}",
                    "",
                    f"📆 *Oy:* {payment.month_for.strftime('%Y-%m')}",
                    "",
                    f"📊 *Holat:* {payment.status.value}",
                ])
            )

        return "💳 *So‘nggi to‘lovlaringiz*\n\n" + "\n\n━━━━━━━━━━━━━━━\n\n".join(blocks)

    def notify_new_grade(self, grade: Grade) -> None:
        student = self.db.execute(
            select(User)
            .options(selectinload(User.student_profile))
            .where(User.id == grade.student_id)
        ).scalar_one_or_none()
        if not student or not student.student_profile or not student.student_profile.telegram_chat_id:
            return
        lesson = self.db.execute(
            select(Lesson).options(joinedload(Lesson.group)).where(Lesson.id == grade.lesson_id)
        ).scalar_one_or_none()
        if not lesson:
            return
        self.send_message(
            student.student_profile.telegram_chat_id,
            (
                "📊 Yangi baho qo'yildi!\n\n"
                f"• Guruh: {lesson.group.name}\n"
                f"• Dars: {lesson.topic or f'{lesson.lesson_number}-dars'}\n"
                f"• Baho: {self._format_grade_percentage(grade.score)}\n"
                f"• Izoh: {grade.note or 'Izoh yo`q'}"
            ),
            TELEGRAM_MENU_KEYBOARD,
        )

    def notify_new_lesson(self, lesson: Lesson) -> None:
        enrollments = list(
            self.db.execute(
                select(Enrollment)
                .options(joinedload(Enrollment.student).joinedload(User.student_profile))
                .where(Enrollment.group_id == lesson.group_id)
                .where(Enrollment.status == EnrollmentStatus.ACTIVE)
            ).scalars().unique()
        )
        for enrollment in enrollments:
            profile = enrollment.student.student_profile
            if not profile or not profile.telegram_chat_id:
                continue
            self.send_message(
                profile.telegram_chat_id,
                (
                    "🆕 Yangi dars qo'shildi!\n\n"
                    f"• Guruh: {lesson.group.name}\n"
                    f"• Sana: {self._format_plain_date(lesson.lesson_date)}\n"
                    f"• Mavzu: {lesson.topic or f'{lesson.lesson_number}-dars'}\n"
                    f"• Vazifa: {lesson.homework or 'Hozircha vazifa kiritilmagan'}"
                ),
                TELEGRAM_MENU_KEYBOARD,
            )

    def notify_new_payment(self, payment: Payment) -> None:
        student = self.db.execute(
            select(User)
            .options(selectinload(User.student_profile))
            .where(User.id == payment.student_id)
        ).scalar_one_or_none()
        if not student or not student.student_profile or not student.student_profile.telegram_chat_id:
            return
        self.send_message(
            student.student_profile.telegram_chat_id,
            (
                "💳 To'lovingiz tizimga kiritildi!\n\n"
                f"• Guruh: {payment.group.name}\n"
                f"• Summa: {self._format_money(payment.amount)}\n"
                f"• Sana: {self._format_date(payment.paid_at)}\n"
                f"• Oy: {payment.month_for.strftime('%Y-%m')}"
            ),
            TELEGRAM_MENU_KEYBOARD,
        )

    def notify_new_attendance(self, attendance: Attendance) -> None:
        student = self.db.execute(
            select(User)
            .options(selectinload(User.student_profile))
            .where(User.id == attendance.student_id)
        ).scalar_one_or_none()
        if not student or not student.student_profile or not student.student_profile.telegram_chat_id:
            return

        lesson = self.db.execute(
            select(Lesson).options(joinedload(Lesson.group)).where(Lesson.id == attendance.lesson_id)
        ).scalar_one_or_none()
        if not lesson:
            return

        attendance_label = "Keldi" if attendance.status.value == "present" else "Kelmadi"
        self.send_message(
            student.student_profile.telegram_chat_id,
            (
                "📍 Davomat yangilandi!\n\n"
                f"• Guruh: {lesson.group.name}\n"
                f"• Dars: {lesson.topic or f'{lesson.lesson_number}-dars'}\n"
                f"• Sana: {self._format_plain_date(lesson.lesson_date)}\n"
                f"• Holat: {attendance_label}\n"
                f"• Izoh: {attendance.note or 'Izoh yo`q'}"
            ),
            TELEGRAM_MENU_KEYBOARD,
        )
