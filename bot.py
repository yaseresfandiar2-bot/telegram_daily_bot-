#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ربات تلگرام امور روزمره (Daily Assistant Bot)
ویژگی‌ها:
- لیست کارها (To-Do)
- یادداشت‌ها
- یادآوری (Reminder)
- آب‌وهوا
- ماشین‌حساب و تبدیل واحد
- مدیریت هزینه‌ها
- تقویم و قرار ملاقات
"""

import os
import re
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
import requests

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

# بارگذاری متغیرهای محیطی
load_dotenv()

# تنظیمات لاگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# توکن و کلیدها از فایل .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
TIMEZONE = ZoneInfo("Asia/Tehran")

# مسیر دیتابیس
DB_PATH = os.path.join(os.path.dirname(__file__), "daily_bot.db")

# وضعیت‌های مکالمه
(
    ADD_TODO,
    ADD_NOTE,
    ADD_EXPENSE_AMOUNT,
    ADD_EXPENSE_CATEGORY,
    ADD_EXPENSE_DESC,
    ADD_EVENT_TITLE,
    ADD_EVENT_DATETIME,
    ADD_REMINDER_TEXT,
    ADD_REMINDER_TIME,
) = range(9)


# ==================== دیتابیس ====================

def init_db():
    """ایجاد جداول دیتابیس"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT NOT NULL,
            done INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL NOT NULL,
            category TEXT,
            description TEXT,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            event_datetime TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT NOT NULL,
            remind_at TEXT NOT NULL,
            job_id TEXT,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    conn.commit()
    conn.close()


def get_conn():
    return sqlite3.connect(DB_PATH)


def ensure_user(user_id: int, username: str = None, first_name: str = None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (user_id, username, first_name, created_at) VALUES (?, ?, ?, ?)",
            (user_id, username, first_name, datetime.now(TIMEZONE).isoformat()),
        )
        conn.commit()
    conn.close()


# ==================== کمکی ====================

def format_dt(dt_str: str) -> str:
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%Y/%m/%d %H:%M")
    except Exception:
        return dt_str


def parse_persian_numbers(text: str) -> str:
    """تبدیل اعداد فارسی به انگلیسی"""
    persian = "۰۱۲۳۴۵۶۷۸۹"
    english = "0123456789"
    trans = str.maketrans(persian, english)
    return text.translate(trans)


# ==================== دستورات اصلی ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user.id, user.username, user.first_name)

    keyboard = [
        [KeyboardButton("📋 کارها"), KeyboardButton("📝 یادداشت")],
        [KeyboardButton("⏰ یادآوری"), KeyboardButton("🌤 آب‌وهوا")],
        [KeyboardButton("💰 هزینه‌ها"), KeyboardButton("📅 تقویم")],
        [KeyboardButton("🧮 ماشین‌حساب"), KeyboardButton("ℹ️ راهنما")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    text = (
        f"سلام {user.first_name}! 👋\n\n"
        "من ربات امور روزمره هستم.\n"
        "می‌تونم کمکت کنم با:\n"
        "• لیست کارها (To-Do)\n"
        "• یادداشت‌برداری\n"
        "• یادآوری کارها\n"
        "• آب‌وهوا\n"
        "• مدیریت هزینه‌ها\n"
        "• تقویم و قرار ملاقات\n"
        "• ماشین‌حساب و تبدیل واحد\n\n"
        "از دکمه‌های پایین یا دستورات استفاده کن.\n"
        "برای راهنمای کامل /help رو بزن."
    )
    await update.message.reply_text(text, reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
📖 <b>راهنمای کامل ربات</b>

<b>📋 کارها (To-Do)</b>
/todo add متن کار
/todo list — نمایش کارها
/todo done شماره — علامت زدن انجام‌شده
/todo del شماره — حذف کار

<b>📝 یادداشت</b>
/note add متن یادداشت
/note list
/note del شماره

<b>⏰ یادآوری</b>
/remind متن | زمان
مثال: /remind خرید نان | 18:30
یا: /remind تماس با مامان | فردا 10:00
یا: /remind جلسه | 2 ساعت دیگه

<b>🌤 آب‌وهوا</b>
/weather نام شهر
مثال: /weather تهران

<b>💰 هزینه‌ها</b>
/expense add مبلغ دسته توضیح
مثال: /expense add 150000 خوراک ناهار
/expense list
/expense report — گزارش ماهانه

<b>📅 تقویم</b>
/event add عنوان | تاریخ ساعت
مثال: /event add جلسه کاری | 2025-10-20 14:00
/event list

<b>🧮 ماشین‌حساب</b>
/calc عبارت
مثال: /calc 25*4+10
/convert 10 km to mile
/convert 100 usd to irr

برای لغو هر عملیات در حال انجام: /cancel
"""
    await update.message.reply_text(text, parse_mode="HTML")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("عملیات لغو شد. ✅")
    return ConversationHandler.END


# ==================== To-Do ====================

async def todo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(user_id)
    args = context.args

    if not args:
        await update.message.reply_text(
            "استفاده:\n"
            "/todo add متن کار\n"
            "/todo list\n"
            "/todo done شماره\n"
            "/todo del شماره"
        )
        return

    action = args[0].lower()

    if action == "add":
        if len(args) < 2:
            await update.message.reply_text("لطفاً متن کار را بنویس:\n/todo add خرید میوه")
            return
        text = " ".join(args[1:])
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO todos (user_id, text, created_at) VALUES (?, ?, ?)",
            (user_id, text, datetime.now(TIMEZONE).isoformat()),
        )
        conn.commit()
        todo_id = cur.lastrowid
        conn.close()
        await update.message.reply_text(f"✅ کار اضافه شد (شماره {todo_id}):\n{text}")

    elif action == "list":
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, text, done FROM todos WHERE user_id = ? ORDER BY done, id DESC",
            (user_id,),
        )
        rows = cur.fetchall()
        conn.close()
        if not rows:
            await update.message.reply_text("هنوز هیچ کاری ثبت نشده. 📭")
            return
        lines = []
        for tid, text, done in rows:
            status = "✅" if done else "⬜️"
            lines.append(f"{status} <b>{tid}</b> — {text}")
        await update.message.reply_text("📋 <b>لیست کارها:</b>\n\n" + "\n".join(lines), parse_mode="HTML")

    elif action == "done":
        if len(args) < 2 or not args[1].isdigit():
            await update.message.reply_text("شماره کار را وارد کن:\n/todo done 3")
            return
        tid = int(args[1])
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE todos SET done = 1 WHERE id = ? AND user_id = ?", (tid, user_id))
        if cur.rowcount:
            conn.commit()
            await update.message.reply_text(f"✅ کار شماره {tid} انجام شد.")
        else:
            await update.message.reply_text("کار پیدا نشد.")
        conn.close()

    elif action == "del":
        if len(args) < 2 or not args[1].isdigit():
            await update.message.reply_text("شماره کار را وارد کن:\n/todo del 3")
            return
        tid = int(args[1])
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM todos WHERE id = ? AND user_id = ?", (tid, user_id))
        if cur.rowcount:
            conn.commit()
            await update.message.reply_text(f"🗑 کار شماره {tid} حذف شد.")
        else:
            await update.message.reply_text("کار پیدا نشد.")
        conn.close()

    else:
        await update.message.reply_text("دستور نامعتبر. از /help استفاده کن.")


# ==================== Notes ====================

async def note_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(user_id)
    args = context.args

    if not args:
        await update.message.reply_text(
            "استفاده:\n/note add متن\n/note list\n/note del شماره"
        )
        return

    action = args[0].lower()

    if action == "add":
        if len(args) < 2:
            await update.message.reply_text("متن یادداشت را بنویس:\n/note add ایده پروژه جدید")
            return
        text = " ".join(args[1:])
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO notes (user_id, text, created_at) VALUES (?, ?, ?)",
            (user_id, text, datetime.now(TIMEZONE).isoformat()),
        )
        conn.commit()
        note_id = cur.lastrowid
        conn.close()
        await update.message.reply_text(f"📝 یادداشت ذخیره شد (شماره {note_id})")

    elif action == "list":
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, text, created_at FROM notes WHERE user_id = ? ORDER BY id DESC LIMIT 20",
            (user_id,),
        )
        rows = cur.fetchall()
        conn.close()
        if not rows:
            await update.message.reply_text("یادداشتی وجود ندارد.")
            return
        lines = [f"<b>{nid}</b> — {text}\n<code>{format_dt(created)}</code>" for nid, text, created in rows]
        await update.message.reply_text("📝 <b>یادداشت‌ها:</b>\n\n" + "\n\n".join(lines), parse_mode="HTML")

    elif action == "del":
        if len(args) < 2 or not args[1].isdigit():
            await update.message.reply_text("شماره یادداشت:\n/note del 2")
            return
        nid = int(args[1])
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", (nid, user_id))
        if cur.rowcount:
            conn.commit()
            await update.message.reply_text(f"🗑 یادداشت {nid} حذف شد.")
        else:
            await update.message.reply_text("یادداشت پیدا نشد.")
        conn.close()


# ==================== Weather ====================

async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not OPENWEATHER_API_KEY:
        await update.message.reply_text(
            "⚠️ کلید API آب‌وهوا تنظیم نشده.\n"
            "در فایل .env مقدار OPENWEATHER_API_KEY را قرار دهید.\n"
            "از سایت openweathermap.org کلید رایگان بگیرید."
        )
        return

    if not context.args:
        await update.message.reply_text("نام شهر را بنویس:\n/weather تهران\n/weather Mashhad")
        return

    city = " ".join(context.args)
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "fa",
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()

        if resp.status_code != 200:
            await update.message.reply_text(f"شهر پیدا نشد یا خطا: {data.get('message', 'نامشخص')}")
            return

        name = data["name"]
        temp = data["main"]["temp"]
        feels = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        desc = data["weather"][0]["description"]
        wind = data["wind"]["speed"]

        text = (
            f"🌤 <b>آب‌وهوای {name}</b>\n\n"
            f"🌡️ دما: <b>{temp}°C</b>\n"
            f"🤗 حس می‌شود: {feels}°C\n"
            f"💧 رطوبت: {humidity}%\n"
            f"💨 باد: {wind} m/s\n"
            f"☁️ وضعیت: {desc}"
        )
        await update.message.reply_text(text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Weather error: {e}")
        await update.message.reply_text("خطا در دریافت اطلاعات آب‌وهوا. بعداً دوباره امتحان کن.")


# ==================== Calculator & Convert ====================

async def calc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "عبارت ریاضی را بنویس:\n"
            "/calc 25*4+10\n"
            "/calc (100-20)/4"
        )
        return

    expr = " ".join(context.args)
    expr = parse_persian_numbers(expr)
    # امنیت: فقط اعداد و عملگرهای مجاز
    if not re.match(r"^[\d\s\+\-\*\/\.\(\)%]+$", expr):
        await update.message.reply_text("فقط اعداد و عملگرهای + - * / ( ) مجاز هستند.")
        return

    try:
        result = eval(expr, {"__builtins__": {}}, {})
        await update.message.reply_text(f"🧮 نتیجه:\n<code>{expr} = {result}</code>", parse_mode="HTML")
    except Exception:
        await update.message.reply_text("عبارت نامعتبر است.")


# نرخ‌های تقریبی تبدیل (برای نمونه؛ در عمل می‌توان از API گرفت)
CONVERSIONS = {
    ("km", "mile"): 0.621371,
    ("mile", "km"): 1.60934,
    ("kg", "lb"): 2.20462,
    ("lb", "kg"): 0.453592,
    ("c", "f"): lambda c: c * 9 / 5 + 32,
    ("f", "c"): lambda f: (f - 32) * 5 / 9,
    ("m", "ft"): 3.28084,
    ("ft", "m"): 0.3048,
}


async def convert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 4 or context.args[2].lower() != "to":
        await update.message.reply_text(
            "فرمت:\n/convert 10 km to mile\n"
            "/convert 100 usd to irr\n"
            "/convert 25 c to f\n\n"
            "واحدهای پشتیبانی‌شده: km/mile, kg/lb, m/ft, c/f, usd/irr (تقریبی)"
        )
        return

    try:
        amount = float(parse_persian_numbers(context.args[0]))
        from_u = context.args[1].lower()
        to_u = context.args[3].lower()

        key = (from_u, to_u)
        if key in CONVERSIONS:
            factor = CONVERSIONS[key]
            result = factor(amount) if callable(factor) else amount * factor
            await update.message.reply_text(f"🔄 {amount} {from_u} = <b>{result:.4g}</b> {to_u}", parse_mode="HTML")
            return

        # ارز تقریبی (نرخ ثابت نمونه — بهتر است از API واقعی استفاده شود)
        if from_u == "usd" and to_u == "irr":
            rate = 580000  # نمونه تقریبی
            result = amount * rate
            await update.message.reply_text(
                f"💵 {amount} USD ≈ <b>{result:,.0f}</b> IRR\n"
                f"<i>(نرخ تقریبی — برای نرخ دقیق از سایت معتبر استفاده کنید)</i>",
                parse_mode="HTML",
            )
            return
        if from_u == "irr" and to_u == "usd":
            rate = 580000
            result = amount / rate
            await update.message.reply_text(
                f"💵 {amount:,.0f} IRR ≈ <b>{result:.2f}</b> USD\n"
                f"<i>(نرخ تقریبی)</i>",
                parse_mode="HTML",
            )
            return

        await update.message.reply_text("تبدیل این واحدها پشتیبانی نمی‌شود.")
    except ValueError:
        await update.message.reply_text("مقدار عددی نامعتبر است.")


# ==================== Expenses ====================

async def expense_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(user_id)
    args = context.args

    if not args:
        await update.message.reply_text(
            "استفاده:\n"
            "/expense add مبلغ دسته توضیح\n"
            "مثال: /expense add 250000 خوراک ناهار رستوران\n"
            "/expense list\n"
            "/expense report"
        )
        return

    action = args[0].lower()

    if action == "add":
        if len(args) < 3:
            await update.message.reply_text("فرمت: /expense add مبلغ دسته [توضیح]")
            return
        try:
            amount = float(parse_persian_numbers(args[1]))
        except ValueError:
            await update.message.reply_text("مبلغ باید عدد باشد.")
            return
        category = args[2]
        description = " ".join(args[3:]) if len(args) > 3 else ""

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO expenses (user_id, amount, category, description, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, description, datetime.now(TIMEZONE).isoformat()),
        )
        conn.commit()
        eid = cur.lastrowid
        conn.close()
        await update.message.reply_text(
            f"💰 هزینه ثبت شد (شماره {eid})\n"
            f"مبلغ: {amount:,.0f}\nدسته: {category}\n{description}"
        )

    elif action == "list":
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, amount, category, description, created_at FROM expenses "
            "WHERE user_id = ? ORDER BY id DESC LIMIT 15",
            (user_id,),
        )
        rows = cur.fetchall()
        conn.close()
        if not rows:
            await update.message.reply_text("هنوز هزینه‌ای ثبت نشده.")
            return
        lines = []
        for eid, amount, cat, desc, created in rows:
            lines.append(f"<b>{eid}</b> | {amount:,.0f} | {cat} | {desc or '-'}\n<code>{format_dt(created)}</code>")
        await update.message.reply_text("💰 <b>آخرین هزینه‌ها:</b>\n\n" + "\n\n".join(lines), parse_mode="HTML")

    elif action == "report":
        conn = get_conn()
        cur = conn.cursor()
        # هزینه‌های ۳۰ روز اخیر
        since = (datetime.now(TIMEZONE) - timedelta(days=30)).isoformat()
        cur.execute(
            "SELECT category, SUM(amount), COUNT(*) FROM expenses "
            "WHERE user_id = ? AND created_at >= ? GROUP BY category ORDER BY SUM(amount) DESC",
            (user_id, since),
        )
        rows = cur.fetchall()
        cur.execute(
            "SELECT SUM(amount) FROM expenses WHERE user_id = ? AND created_at >= ?",
            (user_id, since),
        )
        total = cur.fetchone()[0] or 0
        conn.close()

        if not rows:
            await update.message.reply_text("در ۳۰ روز اخیر هزینه‌ای ثبت نشده.")
            return

        lines = [f"📊 <b>گزارش ۳۰ روز اخیر</b>\n\nمجموع کل: <b>{total:,.0f}</b>\n"]
        for cat, s, cnt in rows:
            lines.append(f"• {cat}: {s:,.0f} ({cnt} مورد)")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    else:
        await update.message.reply_text("دستور نامعتبر.")


# ==================== Events / Calendar ====================

async def event_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(user_id)
    args = context.args

    if not args:
        await update.message.reply_text(
            "استفاده:\n"
            "/event add عنوان | تاریخ ساعت\n"
            "مثال: /event add جلسه تیم | 2025-10-20 15:30\n"
            "/event list"
        )
        return

    action = args[0].lower()

    if action == "add":
        full = " ".join(args[1:])
        if "|" not in full:
            await update.message.reply_text("فرمت: /event add عنوان | YYYY-MM-DD HH:MM")
            return
        title, dt_part = [x.strip() for x in full.split("|", 1)]
        dt_part = parse_persian_numbers(dt_part)
        try:
            # پشتیبانی از چند فرمت
            for fmt in ("%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M", "%Y-%m-%d", "%Y/%m/%d"):
                try:
                    event_dt = datetime.strptime(dt_part, fmt).replace(tzinfo=TIMEZONE)
                    break
                except ValueError:
                    continue
            else:
                raise ValueError
        except ValueError:
            await update.message.reply_text("تاریخ نامعتبر. مثال: 2025-10-20 14:00")
            return

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO events (user_id, title, event_datetime, created_at) VALUES (?, ?, ?, ?)",
            (user_id, title, event_dt.isoformat(), datetime.now(TIMEZONE).isoformat()),
        )
        conn.commit()
        eid = cur.lastrowid
        conn.close()
        await update.message.reply_text(
            f"📅 رویداد ثبت شد (شماره {eid})\n"
            f"عنوان: {title}\nزمان: {event_dt.strftime('%Y/%m/%d %H:%M')}"
        )

    elif action == "list":
        conn = get_conn()
        cur = conn.cursor()
        now = datetime.now(TIMEZONE).isoformat()
        cur.execute(
            "SELECT id, title, event_datetime FROM events "
            "WHERE user_id = ? AND event_datetime >= ? ORDER BY event_datetime LIMIT 10",
            (user_id, now),
        )
        rows = cur.fetchall()
        conn.close()
        if not rows:
            await update.message.reply_text("رویداد آینده‌ای ثبت نشده.")
            return
        lines = [f"<b>{eid}</b> — {title}\n🕒 {format_dt(dt)}" for eid, title, dt in rows]
        await update.message.reply_text("📅 <b>رویدادهای آینده:</b>\n\n" + "\n\n".join(lines), parse_mode="HTML")


# ==================== Reminders ====================

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    """کال‌بک ارسال یادآوری"""
    job = context.job
    data = job.data
    try:
        await context.bot.send_message(
            chat_id=data["chat_id"],
            text=f"⏰ <b>یادآوری!</b>\n\n{data['text']}",
            parse_mode="HTML",
        )
        # حذف از دیتابیس
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM reminders WHERE id = ?", (data.get("reminder_id"),))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Reminder send error: {e}")


def parse_reminder_time(time_str: str) -> Optional[datetime]:
    """پارس کردن زمان یادآوری به صورت نسبی یا مطلق"""
    time_str = parse_persian_numbers(time_str.strip())
    now = datetime.now(TIMEZONE)

    # نسبی: "2 ساعت دیگه" / "30 دقیقه" / "فردا 10:00"
    relative_patterns = [
        (r"(\d+)\s*ساعت\s*(دیگه|دیگر)?", lambda m: now + timedelta(hours=int(m.group(1)))),
        (r"(\d+)\s*دقیقه\s*(دیگه|دیگر)?", lambda m: now + timedelta(minutes=int(m.group(1)))),
        (r"فردا\s*(\d{1,2}):(\d{2})", lambda m: (now + timedelta(days=1)).replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)),
        (r"پس‌فردا\s*(\d{1,2}):(\d{2})", lambda m: (now + timedelta(days=2)).replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)),
    ]
    for pattern, func in relative_patterns:
        m = re.search(pattern, time_str)
        if m:
            return func(m)

    # مطلق: HH:MM امروز یا تاریخ کامل
    m = re.match(r"^(\d{1,2}):(\d{2})$", time_str)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        candidate = now.replace(hour=h, minute=mi, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    for fmt in ("%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(time_str, fmt).replace(tzinfo=TIMEZONE)
        except ValueError:
            continue

    return None


async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    ensure_user(user_id)

    if not context.args:
        await update.message.reply_text(
            "فرمت:\n/remind متن یادآوری | زمان\n\n"
            "مثال‌ها:\n"
            "/remind خرید نان | 18:30\n"
            "/remind تماس با مامان | فردا 10:00\n"
            "/remind جلسه مهم | 2 ساعت دیگه\n"
            "/remind ورزش | 30 دقیقه دیگه"
        )
        return

    full = " ".join(context.args)
    if "|" not in full:
        await update.message.reply_text("حتماً از | برای جدا کردن متن و زمان استفاده کن.")
        return

    text, time_part = [x.strip() for x in full.split("|", 1)]
    remind_at = parse_reminder_time(time_part)

    if not remind_at:
        await update.message.reply_text(
            "زمان قابل فهم نیست.\n"
            "مثال‌های معتبر: 18:30 | فردا 09:00 | 2 ساعت دیگه | 45 دقیقه دیگه"
        )
        return

    if remind_at <= datetime.now(TIMEZONE):
        await update.message.reply_text("زمان باید در آینده باشد.")
        return

    # ذخیره در دیتابیس
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO reminders (user_id, text, remind_at, created_at) VALUES (?, ?, ?, ?)",
        (user_id, text, remind_at.isoformat(), datetime.now(TIMEZONE).isoformat()),
    )
    conn.commit()
    reminder_id = cur.lastrowid
    conn.close()

    # زمان‌بندی با JobQueue
    delay = (remind_at - datetime.now(TIMEZONE)).total_seconds()
    job = context.job_queue.run_once(
        send_reminder,
        when=delay,
        data={"chat_id": chat_id, "text": text, "reminder_id": reminder_id},
        name=f"reminder_{reminder_id}",
    )

    # به‌روزرسانی job_id
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE reminders SET job_id = ? WHERE id = ?", (job.id if job else None, reminder_id))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"⏰ یادآوری تنظیم شد!\n\n"
        f"متن: {text}\n"
        f"زمان: {remind_at.strftime('%Y/%m/%d %H:%M')}\n"
        f"(شماره {reminder_id})"
    )


# ==================== دکمه‌های کیبورد ====================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاسخ به دکمه‌های کیبورد اصلی"""
    text = update.message.text.strip()

    mapping = {
        "📋 کارها": (
            "📋 مدیریت کارها:\n"
            "/todo add متن کار\n"
            "/todo list\n"
            "/todo done شماره\n"
            "/todo del شماره"
        ),
        "📝 یادداشت": (
            "📝 یادداشت‌ها:\n"
            "/note add متن\n"
            "/note list\n"
            "/note del شماره"
        ),
        "⏰ یادآوری": (
            "⏰ یادآوری:\n"
            "/remind متن | زمان\n"
            "مثال: /remind خرید | 18:30"
        ),
        "🌤 آب‌وهوا": "نام شهر را با دستور بفرست:\n/weather تهران",
        "💰 هزینه‌ها": (
            "💰 هزینه‌ها:\n"
            "/expense add مبلغ دسته توضیح\n"
            "/expense list\n"
            "/expense report"
        ),
        "📅 تقویم": (
            "📅 تقویم:\n"
            "/event add عنوان | تاریخ ساعت\n"
            "/event list"
        ),
        "🧮 ماشین‌حساب": (
            "🧮 ماشین‌حساب:\n"
            "/calc 25*4+10\n"
            "/convert 10 km to mile\n"
            "/convert 100 usd to irr"
        ),
        "ℹ️ راهنما": None,  # به help_command می‌رود
    }

    if text == "ℹ️ راهنما":
        await help_command(update, context)
        return

    if text in mapping:
        await update.message.reply_text(mapping[text])
    else:
        # اگر پیام عادی بود، راهنمایی کوتاه
        await update.message.reply_text(
            "از دکمه‌های پایین یا دستورات (/help) استفاده کن.\n"
            "برای شروع /start را بزن."
        )


# ==================== راه‌اندازی ====================

def main():
    if not BOT_TOKEN:
        print("❌ خطا: BOT_TOKEN در فایل .env تنظیم نشده است.")
        print("از @BotFather در تلگرام یک ربات بساز و توکنش را در .env قرار بده.")
        return

    init_db()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # دستورات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("todo", todo_command))
    application.add_handler(CommandHandler("note", note_command))
    application.add_handler(CommandHandler("weather", weather_command))
    application.add_handler(CommandHandler("calc", calc_command))
    application.add_handler(CommandHandler("convert", convert_command))
    application.add_handler(CommandHandler("expense", expense_command))
    application.add_handler(CommandHandler("event", event_command))
    application.add_handler(CommandHandler("remind", remind_command))

    # پیام‌های متنی (دکمه‌ها)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("✅ ربات امور روزمره در حال اجراست...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
