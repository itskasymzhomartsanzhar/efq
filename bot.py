
BOT_TOKEN = "8952102870:AAFHMEjHp6egsrrUrW1I3zyXCCDWnMdebgU"
import asyncio
import datetime
import html
import random
from typing import Any

import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Update,
)

try:
    from . import storage
except ImportError:
    import storage

users: dict[str, str] = {}

msg = False
debug =  False

superadmins = ["5128389615"]

db = {
    "5128389615" : "260699544",
    "5141963843" : "251060947",
    "1355944788" : "260320422",
    "7041340121" : "260842845",
    "1030359267" : "260624255",
    "7926952004" : "260604047"

}
BASE_URL = "https://quizzer.aiplus.kz"
PAGE_SIZE = 40

DEFAULT_PASSWORDS = ("123456", "654321")

SUBJECT_NAMES = {
    "math": "Математика",
    "math_literacy": "Мат. грамотность",
    "kz_history": "История Казахстана",
    "informatics": "Информатика",
    "reading_literacy": "Грамотность чтения",
}

sessions: dict[int, aiohttp.ClientSession] = {}

user_tokens: dict[int, str] = {}

user_logins: dict[int, str] = {}

user_subjects: dict[int, list[str]] = {}

user_navigation: dict[int, dict[str, Any]] = {}

pending_quiz: dict[int, dict[str, Any]] = {}

task_queues: dict[int, list[dict[str, Any]]] = {}

queue_workers: dict[int, asyncio.Task] = {}

TECH_BREAK = "Включен технический перерыв. Мы скоро вернемся."

DEPRECATION_NOTE = (
    "<b><i>Запись от 2026-10-11, оставленная неким owola-swydk:</i></b>\n\n"
    "Привет! Если ты читаешь это... значит проект остановлен.\n\n"
    "Было принято решение задепрекейтить проект...\n\n"
    "Идея создать этого бота появилась от фразы - "
    "\"У меня греется телефон, когда я прохожу Quizzer\".\n\n"
    "<b>Всего за 35 секунд</b> были найдены первые уязвимости в API Quizzer. "
    "Через час ещё 2.\n"
    "Через день я понял, что можно автоматизировать процесс.\n\n"
    "Далее были написаны:\n"
    "Beta версия - успешно прошла тесты инъекции через API\n"
    "v0.0.0.1 - алгоритм на 50 строк, что просто делать 1 post запрос\n"
    "v0.924.0.2 - добавлена авторизация от имени пользователя. "
    "К слову, пароль был предельно прост - [123456, 654321]\n"
    "v0.98.33.0.4.8.3.9 - обход системы, методов отправки ложных выполнений заданий\n"
    "v1.0 - бот по автоматическому прохождению теста готов.\n\n"
    "От IT департамента AiPlus поступало много обновлений продукта, "
    "что значит - они обнаружат уязвимости рано или поздно.\n"
    "Был создан совет директоров во главе с owola-swydk, также iacc, gpro, zemnix, "
    "команда vetryx и <s>ещё одним независимым лицом(скрыто)</s>.\n"
    "Спустя 5 часов совещания было принято решение закрыть проект.\n\n\n"
    "Последним известным обновлением было v1.22.09.2.0.0.9IRLA-505:\n"
    "-Бот перенесен на сервера Майами, США\n"
    "-Добавлена защита конфиденциальности\n"
    "-Добавлены кнопки Сделать ещё и Сделать 3\n\n\n"
    "Последнее обновление - закомчено, git push...\n\n"
    "Важно то, что мы хотели, чтобы ученики учились, а не боялись Quizzer.\n"
    "Мы не знали что делаем, просто пробовали.\n\n\n"
    "Пришли к решению. Quizzer EF - deprecated.\n"
    "<b>Мы действовали добросовестно, результаты действительны "
    "и не могут быть изменены.</b>\n\n\n"
    "<i>Осталось...\n"
    "Стоп, кое что я забыл...\n"
    "Может...не помню. Пусть. Пазл можно собрать имея всего лишь 5 из 6 деталек?...</i>"
)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML,
    ),
)

dp = Dispatcher()


class NotAuthorized(Exception):
    pass


async def safe_edit(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    try:
        await message.edit_text(
            text,
            reply_markup=reply_markup,
        )

    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise


def is_super(tg_id: str) -> bool:
    return tg_id in superadmins


def day_since_iso() -> str:
    start = datetime.datetime.now().replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    return start.isoformat(timespec="seconds")


def week_since_iso() -> str:
    start = datetime.datetime.now() - datetime.timedelta(days=7)
    return start.isoformat(timespec="seconds")


async def gate_reply(event: Update, text: str) -> None:
    try:
        if event.callback_query:
            await event.callback_query.answer(text, show_alert=True)
        elif event.message:
            await event.message.answer(text)
    except Exception:
        pass


async def gate_middleware(handler, event: Update, data):
    user = None

    if event.message and event.message.from_user:
        user = event.message.from_user
    elif event.callback_query and event.callback_query.from_user:
        user = event.callback_query.from_user

    if user is None:
        return await handler(event, data)

    tg_id = str(user.id)

    if tg_id not in db:
        return

    if is_super(tg_id):
        return await handler(event, data)

    if debug:
        await gate_reply(event, TECH_BREAK)
        return

    if storage.is_blocked(tg_id):
        await gate_reply(event, "Вам ограничен доступ.")
        return

    return await handler(event, data)


dp.update.outer_middleware(gate_middleware)


def get_headers() -> dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }


def create_session() -> aiohttp.ClientSession:
    return aiohttp.ClientSession(
        base_url=BASE_URL,
        headers=get_headers(),
        cookie_jar=aiohttp.CookieJar(),
        connector=aiohttp.TCPConnector(ssl=False),
    )


async def get_session(user_id: int) -> aiohttp.ClientSession:
    session = sessions.get(user_id)

    if session is not None and not session.closed:
        return session

    token = user_tokens.get(user_id)

    if not token:
        raise NotAuthorized(
            "Сессия не найдена. Отправьте /start, чтобы войти."
        )

    session = create_session()
    session.cookie_jar.update_cookies(
        {"ent.session-token": token}
    )

    sessions[user_id] = session

    return session


async def close_session(user_id: int) -> None:
    user_tokens.pop(user_id, None)
    user_subjects.pop(user_id, None)
    pending_quiz.pop(user_id, None)

    session = sessions.pop(user_id, None)

    if session is not None and not session.closed:
        await session.close()


def extract_session_token(
    session: aiohttp.ClientSession,
) -> str | None:
    for cookie in session.cookie_jar:
        if "session-token" in cookie.key:
            return cookie.value

    return None


async def authorize(
    user_id: int,
    login: str,
    password: str,
) -> str:
    await close_session(user_id)

    session = create_session()
    authorized = False

    try:
        async with session.get(
            "/api/auth/csrf",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            response.raise_for_status()
            csrf_token = (await response.json())["csrfToken"]

        async with session.post(
            "/api/auth/callback/credentials",
            data={
                "login": login,
                "password": password,
                "csrfToken": csrf_token,
                "callbackUrl": f"{BASE_URL}/login",
            },
            allow_redirects=False,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            response.raise_for_status()

        session_token = extract_session_token(session)

        if not session_token:
            raise NotAuthorized(
                "Неверный логин или пароль."
            )

        sessions[user_id] = session
        user_tokens[user_id] = session_token
        authorized = True

        return session_token

    finally:
        if not authorized and not session.closed:
            await session.close()


async def authorize_any(
    user_id: int,
    login: str,
    passwords: tuple[str, ...] = DEFAULT_PASSWORDS,
) -> str:
    last_error: NotAuthorized | None = None

    for password in passwords:
        try:
            return await authorize(user_id, login, password)

        except NotAuthorized as error:
            last_error = error

    raise last_error or NotAuthorized(
        "Неверный логин или пароль."
    )


async def get_profile(user_id: int) -> dict[str, Any]:
    data = await get_json(
        user_id,
        "/api/auth/session",
    )

    profile = (
        data.get("user")
        if isinstance(data, dict)
        else None
    )

    if not isinstance(profile, dict):
        raise NotAuthorized(
            "Сессия недействительна. Отправьте /start."
        )

    return profile


def get_first_name(name: str) -> str:
    parts = name.split()

    return parts[0] if parts else name


async def get_json(
    user_id: int,
    endpoint: str,
    params: dict[str, Any] | None = None,
) -> Any:
    session = await get_session(user_id)

    async with session.get(
        endpoint,
        params=params,
        timeout=aiohttp.ClientTimeout(total=30),
    ) as response:
        response.raise_for_status()
        return await response.json()


async def post_json(
    user_id: int,
    endpoint: str,
    payload: dict[str, Any],
) -> Any:
    session = await get_session(user_id)

    async with session.post(
        endpoint,
        json=payload,
        timeout=aiohttp.ClientTimeout(total=30),
    ) as response:
        response.raise_for_status()
        return await response.json()


async def post_empty(
    user_id: int,
    endpoint: str,
) -> Any:
    session = await get_session(user_id)

    async with session.post(
        endpoint,
        timeout=aiohttp.ClientTimeout(total=30),
    ) as response:
        response.raise_for_status()

        if response.content_type == "application/json":
            return await response.json()

        return await response.text()


async def post_result(
    user_id: int,
    payload: dict[str, Any],
) -> tuple[int, str]:
    session = await get_session(user_id)

    async with session.post(
        "/api/ent/result",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=aiohttp.ClientTimeout(total=30),
    ) as response:
        return response.status, await response.text()


def normalize_topics(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("topics", "items", "data", "results"):
            value = data.get(key)

            if isinstance(value, list):
                return value

    return []


def topic_id(topic: dict[str, Any]) -> str:
    return str(
        topic.get("id")
        or topic.get("topicId")
        or topic.get("_id")
        or ""
    )


def topic_title(topic: dict[str, Any]) -> str:
    return str(
        topic.get("title")
        or topic.get("name")
        or topic.get("label")
        or "Без названия"
    )


def topic_number(
    topic: dict[str, Any],
    fallback: int,
) -> str:
    order = topic.get("order")

    if isinstance(order, int):
        return str(order)

    if isinstance(order, str) and order.isdigit():
        return order

    return str(fallback)


def topic_label(
    topic: dict[str, Any],
    fallback: int,
) -> str:
    title = topic_title(topic)

    if title[:1].isdigit():
        return title

    return f"{topic_number(topic, fallback)}. {title}"


def is_parent_topic(topic: dict[str, Any]) -> bool:
    if topic.get("isParent") is True:
        return True

    child_count = topic.get("childCount")

    if isinstance(child_count, int):
        return child_count > 0

    if isinstance(child_count, str) and child_count.isdigit():
        return int(child_count) > 0

    return False


async def get_root_topics(
    user_id: int,
    subject: str,
) -> list[dict[str, Any]]:
    data = await get_json(
        user_id,
        "/api/ent/topics",
        params={"subject": subject},
    )

    return normalize_topics(data)


async def get_children(
    user_id: int,
    subject: str,
    parent_id: str,
) -> list[dict[str, Any]]:
    data = await get_json(
        user_id,
        "/api/ent/topics",
        params={
            "subject": subject,
            "parent": parent_id,
        },
    )

    return normalize_topics(data)


def extract_question_ids(data: Any) -> list[str]:
    result: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            possible_id = (
                value.get("questionId")
                or value.get("questionID")
                or value.get("id")
            )

            if possible_id is not None:
                value_id = str(possible_id)

                if value_id not in result:
                    result.append(value_id)

            for child in value.values():
                walk(child)

        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(data)

    return result


def get_page_count(items: list[Any]) -> int:
    return max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)


def get_page_items(
    items: list[Any],
    page: int,
) -> list[Any]:
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE

    return items[start:end]


def build_subject_keyboard(
    subjects: list[str],
    overdue: int = 0,
    soon: int = 0,
) -> InlineKeyboardMarkup:
    rows = []

    for subject in subjects:
        rows.append(
            [
                InlineKeyboardButton(
                    text=SUBJECT_NAMES.get(subject, subject),
                    callback_data=f"subject:{subject}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text=f"Долги ({overdue})",
                callback_data="asg:overdue",
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=f"Закреплено ({soon})",
                callback_data="asg:soon",
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="Личный кабинет",
                callback_data="cab:open",
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="Последняя запись",
                callback_data="note",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def is_mastered(topic: dict[str, Any]) -> bool:
    need = int(topic.get("masteryMax") or 0)
    done = int(topic.get("passes90") or 0)

    return need >= 1 and done >= need


def build_topic_keyboard(
    topics: list[dict[str, Any]],
    page: int,
    total_pages: int,
    can_go_back: bool,
) -> InlineKeyboardMarkup:
    rows = []

    for index, topic in enumerate(topics):
        current_id = topic_id(topic)

        if not current_id:
            continue

        label = topic_label(
            topic,
            page * PAGE_SIZE + index + 1,
        )[:27]

        if is_mastered(topic):
            label += " ✅"

        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"topic:{current_id}",
                )
            ]
        )

    navigation_row = []

    if page > 0:
        navigation_row.append(
            InlineKeyboardButton(
                text="Назад",
                callback_data="page:prev",
            )
        )

    if page < total_pages - 1:
        navigation_row.append(
            InlineKeyboardButton(
                text="Далее",
                callback_data="page:next",
            )
        )

    if navigation_row:
        rows.append(navigation_row)

    if can_go_back:
        rows.append(
            [
                InlineKeyboardButton(
                    text="Назад к разделу",
                    callback_data="nav:back",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="Предметы",
                callback_data="subjects",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_processing_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Предметы",
                    callback_data="subjects",
                )
            ]
        ]
    )


async def get_allowed_subjects(user_id: int) -> list[str]:
    cached = user_subjects.get(user_id)

    if cached is not None:
        return cached

    stats = await get_json(
        user_id,
        "/api/ent/stats",
    )

    subjects = stats.get("allowedSubjects", [])

    if not isinstance(subjects, list):
        subjects = []

    subjects = [str(subject) for subject in subjects]

    if "reading_literacy" not in subjects:
        subjects.append("reading_literacy")

    user_subjects[user_id] = subjects

    return subjects


async def get_assignments(user_id: int) -> dict[str, Any]:
    data = await get_json(user_id, "/api/ent/assignments")

    return data if isinstance(data, dict) else {}


def filter_assignments(
    data: dict[str, Any],
    overdue: bool,
    soon: bool,
) -> list[dict[str, Any]]:
    items = data.get("assignments", [])

    if not isinstance(items, list):
        return []

    return [
        item
        for item in items
        if bool(item.get("overdue")) == overdue
        and bool(item.get("soon")) == soon
    ]


async def assignment_counts(user_id: int) -> tuple[int, int]:
    try:
        data = await get_assignments(user_id)
    except Exception:
        return 0, 0

    return (
        len(filter_assignments(data, True, False)),
        len(filter_assignments(data, False, True)),
    )


def resolve_subject(
    state: dict[str, Any] | None,
    topic_id_value: str,
) -> str | None:
    topic = find_topic(state, topic_id_value)

    if topic and topic.get("subject"):
        return str(topic["subject"])

    return state.get("subject") if state else None


def nav_title(state: dict[str, Any] | None) -> str:
    label = state.get("label") if state else None

    if label:
        return label

    subject = state.get("subject") if state else None

    if subject:
        return SUBJECT_NAMES.get(subject, subject)

    return "Темы"


async def load_current_topics(
    user_id: int,
) -> list[dict[str, Any]]:
    state = user_navigation.get(user_id)

    if not state:
        return []

    subject = state["subject"]
    parent_id = state["parent_id"]

    if parent_id is None:
        return await get_root_topics(
            user_id,
            subject,
        )

    return await get_children(
        user_id,
        subject,
        parent_id,
    )


async def show_topics(
    callback: CallbackQuery,
    subject: str,
    parent_id: str | None = None,
    page: int = 0,
) -> None:
    user_id = callback.from_user.id

    topics = (
        await get_root_topics(user_id, subject)
        if parent_id is None
        else await get_children(
            user_id,
            subject,
            parent_id,
        )
    )

    total_pages = get_page_count(topics)

    page = max(0, min(page, total_pages - 1))

    user_navigation[user_id] = {
        "subject": subject,
        "parent_id": parent_id,
        "page": page,
        "topics": topics,
    }

    page_topics = get_page_items(
        topics,
        page,
    )

    title = SUBJECT_NAMES.get(
        subject,
        subject,
    )

    text = (
        f"<b>{title}</b>\n\n"
        f"Страница <b>{page + 1}</b> из <b>{total_pages}</b>\n"
        f"Тем на странице: <b>{len(page_topics)}</b>"
    )

    await safe_edit(callback.message,
        text,
        reply_markup=build_topic_keyboard(
            page_topics,
            page,
            total_pages,
            parent_id is not None,
        ),
    )


async def show_subjects(
    callback: CallbackQuery,
) -> None:
    user_id = callback.from_user.id

    subjects = await get_allowed_subjects(user_id)
    overdue, soon = await assignment_counts(user_id)

    user_navigation.pop(
        user_id,
        None,
    )

    await safe_edit(callback.message,
        "<b>Выберите предмет:</b>",
        reply_markup=build_subject_keyboard(subjects, overdue, soon),
    )


def find_topic(
    state: dict[str, Any] | None,
    topic_id_value: str,
) -> dict[str, Any] | None:
    if not state:
        return None

    for topic in state.get("topics", []):
        if topic_id(topic) == topic_id_value:
            return topic

    return None


async def show_confirmation(
    callback: CallbackQuery,
    topic_id_value: str,
) -> None:
    user_id = callback.from_user.id

    topic = find_topic(
        user_navigation.get(user_id),
        topic_id_value,
    )

    if topic is not None:
        title = topic_label(topic, 0)
        done = int(topic.get("passes90") or 0)
        need = int(topic.get("masteryMax") or 0)
        deadline = topic.get("deadline")
        overdue = bool(topic.get("overdue"))
        soon = bool(topic.get("soon"))
    else:
        title = "Тема"
        done = 0
        need = 0
        deadline = None
        overdue = False
        soon = False

    is_assignment = bool(topic and topic.get("subject"))

    first_row = [
        InlineKeyboardButton(
            text="Сделать 1",
            callback_data=f"do:{topic_id_value}",
        )
    ]

    if is_assignment:
        first_row.append(
            InlineKeyboardButton(
                text="Сделать 3",
                callback_data=f"do3:{topic_id_value}",
            )
        )

    rows = [first_row]

    if need >= 2 and done < need:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"Сделать все {need}",
                    callback_data=f"doall:{topic_id_value}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="Предметы",
                callback_data="subjects",
            )
        ]
    )

    if need >= 1:
        body = (
            f"Сделано: <b>{done}</b> из <b>{need}</b>\n"
            f"Осталось: <b>{max(0, need - done)}</b>\n\n"
        )
    elif deadline:
        status = (
            "просрочено"
            if overdue
            else ("скоро дедлайн" if soon else "")
        )
        body = (
            f"Дедлайн: <b>{html.escape(str(deadline))}</b>"
            + (f" — {status}" if status else "")
            + "\n\n"
        )
    else:
        body = ""

    await safe_edit(callback.message,
        f"<b>{html.escape(title)}</b>\n\n" + body,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


async def process_topic(
    callback: CallbackQuery,
    selected_topic_id: str,
) -> None:
    user_id = callback.from_user.id

    state = user_navigation.get(user_id)

    if not state:
        await callback.answer(
            "Сначала выбери предмет.",
            show_alert=True,
        )
        return

    subject = resolve_subject(state, selected_topic_id)

    children = await get_children(
        user_id,
        subject,
        selected_topic_id,
    )

    if children:
        user_navigation[user_id] = {
            "subject": subject,
            "parent_id": selected_topic_id,
            "page": 0,
            "topics": children,
        }

        total_pages = get_page_count(children)

        await safe_edit(callback.message,
            f"<b>{SUBJECT_NAMES.get(subject, subject)}</b>\n\n"
            f"Страница <b>1</b> из <b>{total_pages}</b>\n"
            f"Тем на странице: <b>{min(PAGE_SIZE, len(children))}</b>",
            reply_markup=build_topic_keyboard(
                get_page_items(children, 0),
                0,
                total_pages,
                True,
            ),
        )

        return

    await show_confirmation(
        callback,
        selected_topic_id,
    )


def score_options(total: int) -> list[int]:
    if total > 6:
        return [1, 2, 3, total - 3, total - 2, total - 1, total]

    return list(range(1, total + 1))


def build_score_keyboard(total: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []

    for value in score_options(total):
        row.append(
            InlineKeyboardButton(
                text=str(value),
                callback_data=f"score:{value}",
            )
        )

        if len(row) == 4:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append(
        [
            InlineKeyboardButton(
                text="Предметы",
                callback_data="subjects",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def show_score_options(
    callback: CallbackQuery,
    subject: str,
    total: int,
) -> None:
    await safe_edit(callback.message,
        f"<b>{SUBJECT_NAMES.get(subject, subject)}</b>\n\n"
        f"Всего вопросов: <b>{total}</b>\n\n"
        f"Сколько правильных отправить? Выберите число:",
        reply_markup=build_score_keyboard(total),
    )


async def enqueue_task(
    user_id: int,
    task: dict[str, Any],
) -> int:
    queue = task_queues.setdefault(user_id, [])
    queue.append(task)

    worker = queue_workers.get(user_id)

    if worker is None or worker.done():
        queue_workers[user_id] = asyncio.create_task(
            queue_worker(user_id)
        )

    return len(queue)


def worker_active(user_id: int) -> bool:
    worker = queue_workers.get(user_id)
    return worker is not None and not worker.done()


_batch_seq = 0


def next_batch_id() -> int:
    global _batch_seq
    _batch_seq += 1
    return _batch_seq


def build_more_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Сделать ещё",
                    callback_data="more",
                )
            ]
        ]
    )


async def _safe_send(
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> int | None:
    try:
        message = await bot.send_message(
            chat_id, text, reply_markup=reply_markup
        )
        return getattr(message, "message_id", None)
    except Exception:
        return None


async def _safe_edit_msg(
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> int | None:
    try:
        await bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=reply_markup,
        )
        return message_id
    except TelegramBadRequest as error:
        if "message is not modified" in str(error):
            return message_id
    except Exception:
        pass

    return await _safe_send(chat_id, text, reply_markup)


async def prepare_task(task: dict[str, Any]) -> bool:
    if task.get("sleeps") is not None:
        return True

    user_id = int(task["tg_id"])
    pool = task.get("pool")

    if not pool:
        quiz = await get_json(
            user_id,
            f"/api/ent/quiz/{task['topic_id']}",
        )

        question_ids = extract_question_ids(quiz)

        if not question_ids:
            return False

        if task["subject"] in {"math", "math_literacy", "physics"}:
            pool = random.sample(
                question_ids,
                min(5, len(question_ids)),
            )
        else:
            pool = question_ids

        task["pool"] = pool

    total = len(pool)

    low, high = (
        (2, 6)
        if storage.get_human_delays(str(user_id))
        else (1, 5)
    )

    task["sleeps"] = [random.uniform(low, high) for _ in range(total)]
    task["duration"] = round(sum(task["sleeps"]))

    score = task["score"] if task["score"] is not None else total
    task["score_final"] = max(1, min(score, total))

    return True


async def process_one(task: dict[str, Any]) -> dict[str, Any]:
    user_id = int(task["tg_id"])
    topic_id = task["topic_id"]
    subject = task["subject"]
    title = task["title"]
    pool = task["pool"]
    sleeps = task["sleeps"]
    duration = task["duration"]
    score = task["score_final"]
    total = len(pool)

    next_heartbeat_after = random.randint(3, 6)

    for index in range(total):
        await post_json(
            user_id,
            "/api/ent/quiz-pulse",
            {
                "topicId": topic_id,
                "answered": index + 1,
                "answeredNow": True,
            },
        )

        if index + 1 >= next_heartbeat_after:
            await post_empty(user_id, "/api/heartbeat")
            next_heartbeat_after = index + 1 + random.randint(3, 6)

        await asyncio.sleep(sleeps[index])

    shuffled_ids = pool.copy()
    random.shuffle(shuffled_ids)

    right_ids = shuffled_ids[:score]
    wrong_ids = shuffled_ids[score:]

    payload = {
        "topicId": topic_id,
        "score": score,
        "total": total,
        "questionIds": pool,
        "durationSec": duration,
        "answerSec": [max(1, round(s)) for s in sleeps],
        "wrongIds": wrong_ids,
        "rightIds": right_ids,
    }

    status, _ = await post_result(user_id, payload)
    ok = 200 <= status < 300

    storage.log_action(
        str(user_id),
        user_logins.get(user_id, db.get(str(user_id), "")),
        subject,
        topic_id,
        title,
        score,
        total,
        status,
        ok,
    )

    return {
        "title": title,
        "score": score,
        "total": total,
        "right": len(right_ids),
        "wrong": len(wrong_ids),
        "status": status,
        "ok": ok,
    }


def start_fragment(task: dict[str, Any]) -> str:
    size = task["batch_size"]
    times = f" ×{size}" if size > 1 else ""
    per = " за прогон" if size > 1 else ""

    return (
        f"<b>{html.escape(task['title'])}</b>{times}\n"
        f"Вопросов: {len(task['pool'])} · ~{task['duration']} сек{per}"
    )


def completion_text(
    title: str,
    size: int,
    done: int,
    last: dict[str, Any],
) -> str:
    if size > 1:
        return (
            f"Готово: <b>{html.escape(title)}</b> — выполнено {done}/{size}\n"
            f"Последний score: {last['score']}/{last['total']} · "
            f"ответ {last['status']}"
        )

    status_word = "готово" if last["ok"] else "ошибка"

    return (
        f"Готово: <b>{html.escape(title)}</b>\n"
        f"Score: {last['score']}/{last['total']} · "
        f"right {last['right']} / wrong {last['wrong']}\n"
        f"Ответ сервера: {last['status']} ({status_word})"
    )


async def queue_worker(user_id: int) -> None:
    start_announced = False
    status_id = None

    while True:
        queue = task_queues.get(user_id)

        if not queue:
            break

        head = queue[0]
        chat_id = head["chat_id"]
        current_batch = head["batch_id"]
        batch_size = head["batch_size"]
        batch_title = head["title"]

        try:
            ready = await prepare_task(head)
        except Exception as error:
            queue.pop(0)
            await _safe_send(chat_id, f"Ошибка загрузки: {error}")
            start_announced = False
            continue

        if not ready:
            queue.pop(0)
            await _safe_send(
                chat_id,
                f"«{html.escape(batch_title)}»: вопросы не найдены.",
            )
            start_announced = False
            continue

        if not start_announced:
            start_text = "Начинаю: " + start_fragment(head)
            status_id = head.get("message_id")

            if status_id:
                status_id = await _safe_edit_msg(
                    chat_id, status_id, start_text, build_more_keyboard()
                )
            else:
                status_id = await _safe_send(
                    chat_id, start_text, build_more_keyboard()
                )

        done = 0
        last = None

        while True:
            queue = task_queues.get(user_id)

            if not queue or queue[0]["batch_id"] != current_batch:
                break

            task = queue[0]

            try:
                if not await prepare_task(task):
                    queue.pop(0)
                    continue

                queue.pop(0)
                last = await process_one(task)

            except Exception as error:
                queue.pop(0)
                await _safe_send(chat_id, f"Ошибка обработки: {error}")
                continue

            done += 1

            after = task_queues.get(user_id)

            if after and after[0]["batch_id"] == current_batch:
                await asyncio.sleep(2)

        if last is None:
            start_announced = False
            continue

        message = completion_text(batch_title, batch_size, done, last)
        queue = task_queues.get(user_id)

        if queue:
            try:
                next_ready = await prepare_task(queue[0])
            except Exception:
                next_ready = False

            if next_ready:
                message += "\n\nНачинаю: " + start_fragment(queue[0])
                start_announced = True
            else:
                message += "\n\nПродолжаю очередь..."
                start_announced = False

            # очередь не пуста -> обновляем статус-сообщение редактированием
            if status_id:
                status_id = await _safe_edit_msg(
                    chat_id, status_id, message, build_more_keyboard()
                )
            else:
                status_id = await _safe_send(
                    chat_id, message, build_more_keyboard()
                )

            await asyncio.sleep(2)
        else:
            # вся очередь готова -> отдельное сообщение «Готово»
            message += "\n\nОчередь пуста."
            start_announced = False
            await _safe_send(chat_id, message, build_more_keyboard())


@dp.callback_query(F.data == "more")
async def more_callback(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    user_id = callback.from_user.id
    login = db.get(str(user_id))

    if not login:
        return

    try:
        await ensure_auth(user_id, login)
        subjects = await get_allowed_subjects(user_id)
        overdue, soon = await assignment_counts(user_id)

        user_navigation.pop(user_id, None)

        await callback.message.answer(
            "<b>Добавить в очередь — выберите предмет:</b>",
            reply_markup=build_subject_keyboard(subjects, overdue, soon),
        )

    except Exception as error:
        await report_error(callback, error)


@dp.callback_query(F.data == "note")
async def note_callback(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    await safe_edit(callback.message,
        DEPRECATION_NOTE,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Предметы",
                        callback_data="subjects",
                    )
                ]
            ]
        ),
    )


@dp.callback_query(F.data.startswith("do:"))
async def do_callback(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    topic_id_value = callback.data.split(
        ":",
        1,
    )[1]

    user_id = callback.from_user.id
    state = user_navigation.get(user_id)

    if not state:
        await safe_edit(callback.message,
            "Сначала выберите предмет. Отправьте /start."
        )
        return

    subject = resolve_subject(state, topic_id_value)

    try:
        await safe_edit(callback.message,
            "Загружаю вопросы...",
            reply_markup=build_processing_keyboard(),
        )

        quiz = await get_json(
            user_id,
            f"/api/ent/quiz/{topic_id_value}",
        )

        question_ids = extract_question_ids(quiz)

        if not question_ids:
            await safe_edit(callback.message,
                "В этой теме не удалось найти questionId.",
                reply_markup=build_processing_keyboard(),
            )
            return

        if subject in {
            "math",
            "math_literacy",
            "physics"
        }:
            pool = random.sample(
                question_ids,
                min(5, len(question_ids)),
            )
        else:
            pool = question_ids

        topic = find_topic(state, topic_id_value)
        title = topic_label(topic, 0) if topic else "Тема"

        pending_quiz[user_id] = {
            "topic_id": topic_id_value,
            "subject": subject,
            "pool": pool,
            "title": title,
        }

        await show_score_options(
            callback,
            subject,
            len(pool),
        )

    except Exception as error:
        await report_error(callback, error)


async def enqueue_topic_batch(
    callback: CallbackQuery,
    topic_id_value: str,
    count: int,
) -> None:
    user_id = callback.from_user.id
    state = user_navigation.get(user_id)

    if not state:
        await safe_edit(callback.message,
            "Сначала выберите предмет. Отправьте /start.",
        )
        return

    topic = find_topic(state, topic_id_value)

    if topic is None:
        await safe_edit(callback.message,
            "Тема не найдена. Выберите заново.",
        )
        return

    subject = resolve_subject(state, topic_id_value)
    title = topic_label(topic, 0)

    busy = bool(task_queues.get(user_id)) or worker_active(user_id)

    batch_id = next_batch_id()
    position = 0

    for _ in range(count):
        position = await enqueue_task(
            user_id,
            {
                "chat_id": callback.message.chat.id,
                "message_id": callback.message.message_id,
                "tg_id": str(user_id),
                "topic_id": topic_id_value,
                "subject": subject,
                "title": title,
                "score": None,
                "pool": None,
                "batch_id": batch_id,
                "batch_size": count,
            },
        )

    if busy:
        await safe_edit(callback.message,
            f"В очередь добавлено задач: <b>{count}</b>\n"
            f"Тема: «{html.escape(title)}», score — максимум.\n"
            f"Всего в очереди: <b>{position}</b>.",
        )


@dp.callback_query(F.data.startswith("doall:"))
async def doall_callback(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    topic_id_value = callback.data.split(":", 1)[1]
    topic = find_topic(
        user_navigation.get(callback.from_user.id),
        topic_id_value,
    )

    need = int(topic.get("masteryMax") or 0) if topic else 0
    done = int(topic.get("passes90") or 0) if topic else 0
    remaining = max(1, need - done)

    await enqueue_topic_batch(callback, topic_id_value, remaining)


@dp.callback_query(F.data.startswith("do3:"))
async def do3_callback(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    topic_id_value = callback.data.split(":", 1)[1]
    await enqueue_topic_batch(callback, topic_id_value, 3)


@dp.callback_query(F.data.startswith("score:"))
async def score_callback(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    user_id = callback.from_user.id
    pending = pending_quiz.get(user_id)

    if not pending:
        await safe_edit(callback.message,
            "Выбор устарел. Выберите тему заново."
        )
        return

    try:
        score = int(callback.data.split(":", 1)[1])
    except ValueError:
        return

    pool = pending["pool"]
    score = max(1, min(score, len(pool)))

    busy = bool(task_queues.get(user_id)) or worker_active(user_id)

    position = await enqueue_task(
        user_id,
        {
            "chat_id": callback.message.chat.id,
            "message_id": callback.message.message_id,
            "tg_id": str(user_id),
            "topic_id": pending["topic_id"],
            "subject": pending["subject"],
            "title": pending.get("title", "Тема"),
            "score": score,
            "pool": pool,
            "batch_id": next_batch_id(),
            "batch_size": 1,
        },
    )

    pending_quiz.pop(user_id, None)

    if busy:
        await safe_edit(callback.message,
            f"Задача в очереди (позиция <b>{position}</b>).\n"
            f"Правильных: <b>{score}</b>.",
        )


async def report_error(
    callback: CallbackQuery,
    error: Exception,
) -> None:
    if isinstance(error, NotAuthorized):
        text = str(error)

    elif isinstance(error, aiohttp.ClientResponseError):
        if error.status in {401, 403}:
            await close_session(callback.from_user.id)

            text = (
                "Сессия истекла. "
                "Отправьте /start, чтобы войти заново."
            )
        else:
            text = f"Ошибка API: HTTP {error.status}"

    else:
        text = f"Ошибка: {error}"

    await safe_edit(callback.message,text)


async def ensure_profile(user_id: int, login: str) -> str:
    name = users.get(login)

    if name is None:
        profile = await get_profile(user_id)
        name = str(profile.get("name") or login)
        users[login] = name

    return name


async def open_menu(
    message: Message,
    user_id: int,
    login: str,
) -> None:
    name = await ensure_profile(user_id, login)
    subjects = await get_allowed_subjects(user_id)
    overdue, soon = await assignment_counts(user_id)

    user_navigation.pop(user_id, None)

    await message.answer(
        f"Добро пожаловать, "
        f"<b>{html.escape(get_first_name(name))}</b>, "
        f"выберите предмет:",
        reply_markup=build_subject_keyboard(subjects, overdue, soon),
    )


@dp.message(CommandStart())
async def start_handler(
    message: Message,
) -> None:
    user_id = message.from_user.id
    login = db.get(str(user_id))

    if not login:
        return

    try:
        if user_id not in user_tokens:
            await authorize_any(user_id, login)
            user_logins[user_id] = login

        await open_menu(message, user_id, login)

    except aiohttp.ClientResponseError as error:
        if error.status in {401, 403}:
            try:
                await authorize_any(user_id, login)
                user_logins[user_id] = login
                await open_menu(message, user_id, login)
            except Exception as retry_error:
                await message.answer(f"Ошибка: {retry_error}")

            return

        await message.answer(
            f"Ошибка API: HTTP {error.status}"
        )

    except NotAuthorized as error:
        await message.answer(str(error))

    except Exception as error:
        await message.answer(f"Ошибка: {error}")


async def ensure_auth(user_id: int, login: str) -> None:
    if user_id not in user_tokens:
        await authorize_any(user_id, login)
        user_logins[user_id] = login


# ---------- личный кабинет ----------

async def render_cabinet(
    user_id: int,
    login: str,
) -> tuple[str, InlineKeyboardMarkup]:
    profile = await get_profile(user_id)
    name = str(profile.get("name") or login)

    users[login] = name
    storage.set_name(str(user_id), name)

    subjects = await get_allowed_subjects(user_id)
    subjects_text = ", ".join(
        SUBJECT_NAMES.get(subject, subject) for subject in subjects
    ) or "—"

    done_today = storage.user_action_count(str(user_id), day_since_iso())
    done_week = storage.user_action_count(str(user_id), week_since_iso())

    human = storage.get_human_delays(str(user_id))

    text = (
        f"<b>Личный кабинет</b>\n\n"
        f"Имя: <b>{html.escape(name)}</b>\n"
        f"Логин: <code>{login}</code>\n"
        f"Класс: {profile.get('grade', '—')} · "
        f"Город: {profile.get('city', '—')}\n\n"
        f"<b>Профильные предметы:</b>\n{subjects_text}\n\n"
        f"<b>Статистика:</b>\n"
        f"Квизов сегодня: <b>{done_today}</b>\n"
        f"За 7 дней: <b>{done_week}</b>\n\n"
        f"<b>Настройки:</b>\n"
        f"Задержки 2–6с (более безопасно): <b>{'включены' if human else 'выключены'}</b>"
    )

    toggle = (
        "Выключить задержки 2–6с"
        if human
        else "Включить задержки 2–6с"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=toggle,
                    callback_data="cab:delays",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Предметы",
                    callback_data="subjects",
                )
            ],
        ]
    )

    return text, keyboard


@dp.message(Command("cabinet"))
async def cabinet_handler(
    message: Message,
) -> None:
    user_id = message.from_user.id
    login = db.get(str(user_id))

    if not login:
        return

    try:
        await ensure_auth(user_id, login)
        text, keyboard = await render_cabinet(user_id, login)
        await message.answer(text, reply_markup=keyboard)

    except Exception as error:
        await message.answer(f"Ошибка: {error}")


@dp.callback_query(F.data == "cab:delays")
async def cabinet_toggle(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    user_id = callback.from_user.id
    login = db.get(str(user_id))

    if not login:
        return

    storage.set_human_delays(
        str(user_id),
        not storage.get_human_delays(str(user_id)),
    )

    try:
        await ensure_auth(user_id, login)
        text, keyboard = await render_cabinet(user_id, login)
        await safe_edit(callback.message, text, reply_markup=keyboard)

    except Exception as error:
        await report_error(callback, error)


@dp.callback_query(F.data == "cab:open")
async def cabinet_open_callback(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    user_id = callback.from_user.id
    login = db.get(str(user_id))

    if not login:
        return

    try:
        await ensure_auth(user_id, login)
        text, keyboard = await render_cabinet(user_id, login)
        await safe_edit(callback.message, text, reply_markup=keyboard)

    except Exception as error:
        await report_error(callback, error)


@dp.callback_query(F.data.startswith("asg:"))
async def assignments_callback(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    kind = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id

    if kind == "overdue":
        want_overdue, want_soon, label = True, False, "Долги"
    else:
        want_overdue, want_soon, label = False, True, "Закреплено"

    try:
        data = await get_assignments(user_id)
        items = filter_assignments(data, want_overdue, want_soon)

        if not items:
            await safe_edit(callback.message,
                f"<b>{label}</b>\n\nПусто.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Предметы",
                                callback_data="subjects",
                            )
                        ]
                    ]
                ),
            )
            return

        user_navigation[user_id] = {
            "subject": None,
            "label": label,
            "parent_id": None,
            "page": 0,
            "topics": items,
        }

        total_pages = get_page_count(items)

        await safe_edit(callback.message,
            f"<b>{label}</b>\n\n"
            f"Всего: <b>{len(items)}</b>\n"
            f"Страница <b>1</b> из <b>{total_pages}</b>",
            reply_markup=build_topic_keyboard(
                get_page_items(items, 0),
                0,
                total_pages,
                False,
            ),
        )

    except Exception as error:
        await report_error(callback, error)


# ---------- админ-панель ----------

def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Пользователи", callback_data="adm:users")],
            [InlineKeyboardButton(text="Обновить имена (прогнать всех)", callback_data="adm:names")],
            [InlineKeyboardButton(text="Лента действий", callback_data="adm:feed")],
            [InlineKeyboardButton(text="Счётчики", callback_data="adm:stats")],
            [InlineKeyboardButton(text="Рассылки", callback_data="adm:bcast")],
            [InlineKeyboardButton(text="Разослать запись", callback_data="adm:notebcast")],
        ]
    )


def admin_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="adm:menu")]
        ]
    )


async def show_admin_users(callback: CallbackQuery) -> None:
    rows_users = storage.list_users()

    lines = ["<b>Пользователи</b>\n"]
    keyboard_rows = []

    for user in rows_users:
        tg_id = user["tg_id"]
        name = user["name"] or "—"
        login = user["login"] or "—"
        status = "заблокирован" if user["blocked"] else "активен"

        lines.append(
            f"<code>{tg_id}</code> · {html.escape(name)} · "
            f"{login} · {status}"
        )

        action = "Разблокировать" if user["blocked"] else "Заблокировать"
        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text=f"{action}: {name}"[:60],
                    callback_data=f"adm:block:{tg_id}",
                )
            ]
        )

    keyboard_rows.append(
        [InlineKeyboardButton(text="Назад", callback_data="adm:menu")]
    )

    await safe_edit(callback.message,
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows),
    )


async def harvest_names() -> None:
    for tg_id, login in db.items():
        try:
            user_id = int(tg_id)
            await authorize_any(user_id, login)
            profile = await get_profile(user_id)
            name = str(profile.get("name") or login)

            users[login] = name
            user_logins[user_id] = login
            storage.set_name(tg_id, name)

        except Exception as error:
            print(f"harvest {tg_id}: {error}")

        await asyncio.sleep(2)


async def show_admin_feed(callback: CallbackQuery) -> None:
    actions = storage.recent_actions(15)

    if not actions:
        await safe_edit(callback.message,
            "Лента пуста.",
            reply_markup=admin_back_keyboard(),
        )
        return

    lines = ["<b>Последние действия</b>\n"]

    for action in actions:
        mark = "ok" if action["ok"] else f"err {action['status']}"
        when = action["ts"][5:16].replace("T", " ")
        lines.append(
            f"{when} · {action['login']} · "
            f"{html.escape((action['topic_title'] or '')[:28])} · "
            f"{action['score']}/{action['total']} · {mark}"
        )

    await safe_edit(callback.message,
        "\n".join(lines),
        reply_markup=admin_back_keyboard(),
    )


async def show_admin_stats(callback: CallbackQuery) -> None:
    day = day_since_iso()
    week = week_since_iso()

    lines = [
        "<b>Счётчики</b>\n",
        f"Квизов сегодня: <b>{storage.count_since(day)}</b>",
        f"За 7 дней: <b>{storage.count_since(week)}</b>\n",
        "<b>За 7 дней по предметам:</b>",
    ]

    by_subject = storage.count_by_subject(week)

    if by_subject:
        for subject, count in by_subject:
            lines.append(f"  {SUBJECT_NAMES.get(subject, subject)}: {count}")
    else:
        lines.append("  —")

    lines.append("\n<b>За 7 дней по ученикам:</b>")

    by_user = storage.count_by_user(week)

    if by_user:
        for tg_id, login, count in by_user:
            user = storage.get_user(tg_id)
            name = (user and user["name"]) or login
            lines.append(f"  {html.escape(name)}: {count}")
    else:
        lines.append("  —")

    await safe_edit(callback.message,
        "\n".join(lines),
        reply_markup=admin_back_keyboard(),
    )


async def show_admin_bcast(callback: CallbackQuery) -> None:
    pending = storage.pending_broadcasts()

    lines = [
        "<b>Рассылки</b>\n",
        "Отправить сейчас:",
        "<code>/broadcast all текст</code>",
        "<code>/broadcast 5128389615 текст</code>",
        "<code>/broadcast 111,222 текст</code>\n",
        "Отложить:",
        "<code>/schedule tomorrow 09:00 all текст</code>",
        "<code>/schedule 2026-10-10 18:30 all текст</code>\n",
        f"Запланировано: <b>{len(pending)}</b>",
    ]

    for item in pending:
        lines.append(
            f"  #{item['id']} {item['ts_run'][:16]} → "
            f"{item['target']}: {html.escape(item['text'][:30])}"
        )

    await safe_edit(callback.message,
        "\n".join(lines),
        reply_markup=admin_back_keyboard(),
    )


@dp.message(Command("admin"))
async def admin_handler(
    message: Message,
) -> None:
    if not is_super(str(message.from_user.id)):
        return

    await message.answer(
        "<b>Админ-панель</b>",
        reply_markup=admin_menu_keyboard(),
    )


@dp.callback_query(F.data.startswith("adm:"))
async def admin_callback(
    callback: CallbackQuery,
) -> None:
    if not is_super(str(callback.from_user.id)):
        await callback.answer("Недоступно", show_alert=True)
        return

    await callback.answer()

    action = callback.data.split(":", 1)[1]

    try:
        if action == "menu":
            await safe_edit(callback.message,
                "<b>Админ-панель</b>",
                reply_markup=admin_menu_keyboard(),
            )
        elif action == "users":
            await show_admin_users(callback)
        elif action == "names":
            await safe_edit(callback.message, "Прогоняю всех, собираю имена...")
            await harvest_names()
            await show_admin_users(callback)
        elif action == "feed":
            await show_admin_feed(callback)
        elif action == "stats":
            await show_admin_stats(callback)
        elif action == "bcast":
            await show_admin_bcast(callback)
        elif action == "notebcast":
            await safe_edit(callback.message,
                f"Разослать «Последнюю запись» всем <b>{len(db)}</b> пользователям?\n\n"
                f"Дойдёт только тем, кто запускал бота. "
                f"После отправки отменить нельзя.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Да, разослать всем",
                                callback_data="adm:notebcast_go",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="Отмена",
                                callback_data="adm:menu",
                            )
                        ],
                    ]
                ),
            )
        elif action == "notebcast_go":
            await safe_edit(callback.message, "Рассылаю запись...")
            ok, fail = await send_broadcast("all", DEPRECATION_NOTE)
            await safe_edit(callback.message,
                f"Запись разослана.\n"
                f"Отправлено: <b>{ok}</b>, не доставлено: <b>{fail}</b>",
                reply_markup=admin_back_keyboard(),
            )
        elif action.startswith("block:"):
            tg_id = action.split(":", 1)[1]
            user = storage.get_user(tg_id)
            storage.set_blocked(tg_id, not (user and user["blocked"]))
            await show_admin_users(callback)

    except Exception as error:
        await safe_edit(callback.message, f"Ошибка: {error}")


# ---------- рассылки (команды) ----------

def parse_target(token: str) -> list[str]:
    if token == "all":
        return list(db.keys())

    return [part for part in token.split(",") if part]


async def send_broadcast(target: str, text: str) -> tuple[int, int]:
    ok = 0
    fail = 0

    for tg_id in parse_target(target):
        try:
            await bot.send_message(int(tg_id), text)
            ok += 1
        except Exception:
            fail += 1

    return ok, fail


def parse_run_at(date_str: str, time_str: str) -> datetime.datetime:
    today = datetime.date.today()

    if date_str == "today":
        day = today
    elif date_str == "tomorrow":
        day = today + datetime.timedelta(days=1)
    else:
        day = datetime.date.fromisoformat(date_str)

    hour, minute = time_str.split(":")

    return datetime.datetime(
        day.year,
        day.month,
        day.day,
        int(hour),
        int(minute),
    )


@dp.message(Command("broadcast"))
async def broadcast_command(
    message: Message,
) -> None:
    if not is_super(str(message.from_user.id)):
        return

    parts = (message.text or "").split(maxsplit=2)

    if len(parts) < 3:
        await message.answer(
            "Формат: /broadcast &lt;all|id|id,id&gt; текст"
        )
        return

    target, text = parts[1], parts[2]
    ok, fail = await send_broadcast(target, text)

    await message.answer(
        f"Отправлено: <b>{ok}</b>, не доставлено: <b>{fail}</b>"
    )


@dp.message(Command("schedule"))
async def schedule_command(
    message: Message,
) -> None:
    if not is_super(str(message.from_user.id)):
        return

    parts = (message.text or "").split(maxsplit=4)

    if len(parts) < 5:
        await message.answer(
            "Формат: /schedule &lt;YYYY-MM-DD|today|tomorrow&gt; "
            "&lt;HH:MM&gt; &lt;all|id|id,id&gt; текст"
        )
        return

    _, date_str, time_str, target, text = parts

    try:
        run_at = parse_run_at(date_str, time_str)
    except Exception:
        await message.answer(
            "Не понял дату/время. Пример:\n"
            "<code>/schedule tomorrow 09:00 all текст</code>"
        )
        return

    storage.add_broadcast(
        run_at.isoformat(timespec="seconds"),
        text,
        target,
    )

    await message.answer(
        f"Запланировано на <b>{run_at.strftime('%Y-%m-%d %H:%M')}</b> "
        f"для «{target}»."
    )


@dp.message()
async def fallback_handler(
    message: Message,
) -> None:
    await message.answer(
        "Отправьте /start, чтобы войти."
    )


@dp.callback_query(F.data == "subjects")
async def subjects_callback(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    try:
        await show_subjects(callback)

    except Exception as error:
        await report_error(callback, error)


@dp.callback_query(F.data.startswith("subject:"))
async def subject_callback(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    subject = callback.data.split(
        ":",
        1,
    )[1]

    try:
        await show_topics(
            callback,
            subject,
            None,
            0,
        )

    except Exception as error:
        await report_error(callback, error)


@dp.callback_query(F.data.startswith("topic:"))
async def topic_callback(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    selected_topic_id = callback.data.split(
        ":",
        1,
    )[1]

    try:
        await process_topic(
            callback,
            selected_topic_id,
        )

    except Exception as error:
        await report_error(callback, error)


@dp.callback_query(F.data == "page:next")
async def next_page_callback(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    user_id = callback.from_user.id
    state = user_navigation.get(user_id)

    if not state:
        return

    topics = state["topics"]
    current_page = state["page"]
    total_pages = get_page_count(topics)

    if current_page >= total_pages - 1:
        return

    state["page"] += 1

    page = state["page"]

    await safe_edit(callback.message,
        f"<b>{nav_title(state)}</b>\n\n"
        f"Страница <b>{page + 1}</b> из <b>{total_pages}</b>\n"
        f"Тем на странице: "
        f"<b>{len(get_page_items(topics, page))}</b>",
        reply_markup=build_topic_keyboard(
            get_page_items(topics, page),
            page,
            total_pages,
            state["parent_id"] is not None,
        ),
    )


@dp.callback_query(F.data == "page:prev")
async def previous_page_callback(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    user_id = callback.from_user.id
    state = user_navigation.get(user_id)

    if not state:
        return

    topics = state["topics"]
    current_page = state["page"]

    if current_page <= 0:
        return

    state["page"] -= 1

    page = state["page"]
    total_pages = get_page_count(topics)

    await safe_edit(callback.message,
        f"<b>{nav_title(state)}</b>\n\n"
        f"Страница <b>{page + 1}</b> из <b>{total_pages}</b>\n"
        f"Тем на странице: "
        f"<b>{len(get_page_items(topics, page))}</b>",
        reply_markup=build_topic_keyboard(
            get_page_items(topics, page),
            page,
            total_pages,
            state["parent_id"] is not None,
        ),
    )


@dp.callback_query(F.data == "nav:back")
async def navigation_back_callback(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    user_id = callback.from_user.id
    state = user_navigation.get(user_id)

    if not state:
        return

    subject = state["subject"]
    parent_id = state["parent_id"]

    try:
        if parent_id is None:
            await show_subjects(callback)
            return

        parent_topics = await get_children(
            user_id,
            subject,
            parent_id,
        )

        user_navigation[user_id] = {
            "subject": subject,
            "parent_id": None,
            "page": 0,
            "topics": parent_topics,
        }

        await show_topics(
            callback,
            subject,
            None,
            0,
        )

    except Exception as error:
        await report_error(callback, error)


async def broadcast_startup() -> None:
    for tg_id in db:
        try:
            await bot.send_message(
                int(tg_id),
                "Бот работает, можешь квизер делать",
            )

        except Exception as error:
            print(f"Не удалось отправить {tg_id}: {error}")


async def scheduler_loop() -> None:
    while True:
        try:
            for item in storage.due_broadcasts(storage.now_iso()):
                await send_broadcast(item["target"], item["text"])
                storage.mark_sent(item["id"])

        except Exception as error:
            print(f"scheduler: {error}")

        await asyncio.sleep(30)


async def shutdown() -> None:
    for session in sessions.values():
        if not session.closed:
            await session.close()

    await bot.session.close()


async def main() -> None:
    storage.init()
    storage.sync_users(db)

    if msg:
        await broadcast_startup()

    scheduler = asyncio.create_task(scheduler_loop())

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.cancel()
        await shutdown()


if __name__ == "__main__":
    asyncio.run(main())