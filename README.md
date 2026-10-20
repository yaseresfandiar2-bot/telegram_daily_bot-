# ربات تلگرام امور روزمره (Daily Assistant Bot)

ربات شخصی برای مدیریت کارهای روزانه با امکانات کامل.

## ویژگی‌ها

| قابلیت | دستورات |
|--------|---------|
| **لیست کارها** | `/todo add` `/todo list` `/todo done` `/todo del` |
| **یادداشت** | `/note add` `/note list` `/note del` |
| **یادآوری** | `/remind متن \| زمان` |
| **آب‌وهوا** | `/weather نام شهر` |
| **ماشین‌حساب** | `/calc عبارت` |
| **تبدیل واحد** | `/convert 10 km to mile` |
| **هزینه‌ها** | `/expense add` `/expense list` `/expense report` |
| **تقویم** | `/event add` `/event list` |

## نصب و راه‌اندازی

### ۱. ساخت ربات در تلگرام
1. به [@BotFather](https://t.me/BotFather) پیام بده
2. دستور `/newbot` را بزن
3. نام و یوزرنیم ربات را انتخاب کن
4. توکنی که می‌دهد را کپی کن

### ۲. نصب وابستگی‌ها
```bash
cd telegram_daily_bot
python3 -m venv venv
source venv/bin/activate   # در ویندوز: venv\Scripts\activate
pip install -r requirements.txt
```

### ۳. تنظیم فایل .env
```bash
cp .env.example .env
```
سپس فایل `.env` را باز کن و مقادیر را پر کن:

```
BOT_TOKEN=توکنی_که_از_BotFather_گرفتی
OPENWEATHER_API_KEY=کلید_اختیاری_آب‌وهوا
```

> برای آب‌وهوا: از [openweathermap.org](https://openweathermap.org/api) ثبت‌نام کن و کلید رایگان بگیر.

### ۴. اجرای ربات
```bash
python bot.py
```

ربات آماده است! در تلگرام به رباتت پیام `/start` بده.

## مثال‌های استفاده

```
/todo add خرید میوه و سبزی
/todo list
/todo done 1

/note add ایده برای پروژه جدید

/remind تماس با مامان | فردا 10:00
/remind جلسه مهم | 2 ساعت دیگه
/remind خرید نان | 18:30

/weather تهران
/weather Isfahan

/calc 1500000 * 0.09
/convert 10 km to mile
/convert 100 usd to irr

/expense add 250000 خوراک ناهار رستوران
/expense report

/event add جلسه تیم | 2025-10-22 15:00
/event list
```

## نکات مهم

- همه داده‌ها در فایل `daily_bot.db` (SQLite) ذخیره می‌شوند.
- زمان‌ها بر اساس منطقه زمانی **تهران** هستند.
- برای اجرای دائمی روی سرور، از `systemd` یا `pm2` یا `screen` استفاده کن.
- نرخ تبدیل ارز تقریبی است و فقط برای نمونه قرار داده شده.

## پشتیبانی از زبان فارسی
ربات کاملاً به فارسی پاسخ می‌دهد و اعداد فارسی را هم می‌فهمد.
