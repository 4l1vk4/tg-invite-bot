#!/usr/bin/env python3
"""
Telegram Mini App Invite Bot for Holiday Events
Запуск: python bot.py
"""

import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ─── ЗАГРУЗКА .ENV ───────────────────────────────────────────────────────────
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬ_СЮДА_ТОКЕН_ОТ_BOTFATHER").strip()
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com").strip()
if WEBAPP_URL and not WEBAPP_URL.startswith("http://") and not WEBAPP_URL.startswith("https://"):
    WEBAPP_URL = "https://" + WEBAPP_URL
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip()

# Файл для хранения ответов
DATA_FILE = "responses.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ─── ХРАНИЛИЩЕ ───────────────────────────────────────────────────────────────
def load_responses():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка чтения {DATA_FILE}: {e}")
            return {}
    return {}


def save_responses(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка записи в {DATA_FILE}: {e}")


def get_admin_id():
    if not ADMIN_CHAT_ID:
        return None
    try:
        return int(ADMIN_CHAT_ID)
    except ValueError:
        return ADMIN_CHAT_ID if ADMIN_CHAT_ID.startswith("@") else f"@{ADMIN_CHAT_ID}"


# ─── КОМАНДЫ ─────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главная команда — отправляет персональное приглашение с кнопкой Mini App"""
    user = update.effective_user
    first_name = user.first_name or "Друг"

    # Генерируем персональную ссылку с параметрами (с антикешем v)
    import time
    personal_url = f"{WEBAPP_URL}?user_id={user.id}&name={first_name}&v={int(time.time())}"

    # Инлайн-кнопка под сообщением
    keyboard = [
        [InlineKeyboardButton("🎉 Открыть приглашение и роадмап", web_app=WebAppInfo(url=personal_url))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        f"Привет, {first_name}! 🌴✨\n\n"
        f"Ты приглашен(а) на мероприятие по важному случаю \n\n"
        f"Нажми на кнопку ниже, чтобы открыть карточку приглашения 👇"
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

    # Настраиваем постоянную кнопку в нижнем меню Telegram (слева от поля ввода)
    try:
        from telegram import MenuButtonWebApp
        await context.bot.set_chat_menu_button(
            chat_id=user.id,
            menu_button=MenuButtonWebApp(text="🎉 Приглашение", web_app=WebAppInfo(url=personal_url)),
        )
    except Exception as e:
        logger.debug(f"Не удалось настроить MenuButton: {e}")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда статистики ответов (для организатора)"""
    data = load_responses()

    accepted = [r for r in data.values() if r.get("status") == "accepted"]
    declined = [r for r in data.values() if r.get("status") == "declined"]
    total = len(data)

    total_guests = sum(int(r.get("guests", 1)) for r in accepted)

    text = (
        f"📊 *Статистика приглашений*\n\n"
        f"✅ Приняли: *{len(accepted)}* (всего человек: *{total_guests}*)\n"
        f"❌ Отказались: *{len(declined)}*\n"
        f"📨 Всего ответов: *{total}*\n\n"
    )

    if accepted:
        text += "🎉 *Идут на праздник:*\n"
        for r in accepted:
            name = r.get("name", "Гость")
            username = f" (@{r['username']})" if r.get("username") else ""
            plus_one = f" (+{int(r.get('guests', 1)) - 1})" if int(r.get("guests", 1)) > 1 else ""
            drink = f" | 🍷 {r.get('drink')}" if r.get("drink") else ""
            dishes = r.get("selected_dishes", [])
            refused = r.get("refused_dishes", [])
            dishes_str = f" | ⭐ {len(dishes)}" if dishes else ""
            refused_str = f" | 🚫 {len(refused)}" if refused else ""
            text += f"• {name}{username}{plus_one}{drink}{dishes_str}{refused_str}\n"
        text += "\n"

    if declined:
        text += "😢 *Не смогут:*\n"
        for r in declined:
            name = r.get("name", "Гость")
            username = f" (@{r['username']})" if r.get("username") else ""
            text += f"• {name}{username}\n"

    if not data:
        text += "_Пока никто не ответил на приглашение._"

    await update.message.reply_text(text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка по командам бота"""
    help_text = (
        "🤖 *Команды бота:*\n\n"
        "/start — Получить приглашение и открыть роадмап\n"
        "/stats — Посмотреть список гостей и статистику (для организатора)\n"
        "/help — Эта справка\n"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


# ─── ИНЛАЙН-ОТВЕТЫ (CALLBACK) ────────────────────────────────────────────────
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кликов по инлайн-кнопкам прямо в чате"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    status = "accepted" if query.data == "rsvp_accept" else "declined"

    response = {
        "user_id": user.id,
        "name": user.first_name or "Друг",
        "username": user.username,
        "status": status,
        "guests": 1,
        "source": "telegram_inline_button",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    responses = load_responses()
    responses[str(user.id)] = response
    save_responses(responses)

    admin_id = get_admin_id()

    if status == "accepted":
        await query.edit_message_text(
            f"🎉 *Ура, {user.first_name}! Ты в деле!*\n\n"
            f"Мы записали твой ответ. Меню всех 5 кухонь ты всегда можешь посмотреть по кнопке внизу!",
            parse_mode="Markdown",
        )
        if admin_id:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"📨 *Новый ответ (из чата)!*\n\n"
                         f"👤 {response['name']} (@{response['username'] or 'нет'})\n"
                         f"✅ ПРИНЯЛ(А) ПРИГЛАШЕНИЕ\n"
                         f"🕐 {response['timestamp']}",
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.error(f"Ошибка отправки админу: {e}")
    else:
        await query.edit_message_text(
            f"😢 *Очень жаль, {user.first_name}, что не получается.*\n\n"
            f"Если планы изменятся — напиши /start и нажми кнопку участия!",
            parse_mode="Markdown",
        )
        if admin_id:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"📨 *Новый ответ (из чата)!*\n\n"
                         f"👤 {response['name']} (@{response['username'] or 'нет'})\n"
                         f"❌ ОТКАЗАЛСЯ(АСЬ)\n"
                         f"🕐 {response['timestamp']}",
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.error(f"Ошибка отправки админу: {e}")


# ─── ОБРАБОТКА ДАННЫХ ИЗ МИНИ-АППА ──────────────────────────────────────────
async def webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получает структурированные данные из Mini App"""
    try:
        raw_data = update.effective_message.web_app_data.data
        data = json.loads(raw_data)
        user = update.effective_user

        status = data.get("status", "accepted")
        name = data.get("name") or user.first_name or "Гость"
        guests = int(data.get("guests", 1))
        drink = data.get("drink", "")
        selected_dishes = data.get("selected_dishes", [])
        refused_dishes = data.get("refused_dishes", [])
        comment = data.get("comment", "")

        response = {
            "user_id": user.id,
            "name": name,
            "username": user.username,
            "status": status,
            "guests": guests,
            "drink": drink,
            "selected_dishes": selected_dishes,
            "refused_dishes": refused_dishes,
            "comment": comment,
            "source": "mini_app",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Сохраняем ответ
        responses = load_responses()
        responses[str(user.id)] = response
        save_responses(responses)

        # Отвечаем пользователю
        if status == "accepted":
            details_str = ""
            if guests > 1:
                details_str += f"\n👥 Гостей: {guests}"
            if drink:
                details_str += f"\n🍷 Любимый напиток: {drink}"
            if selected_dishes:
                details_str += f"\n⭐ В приоритете ({len(selected_dishes)}): {', '.join(selected_dishes)}"
            if refused_dishes:
                details_str += f"\n🚫 Отказано ({len(refused_dishes)}): {', '.join(refused_dishes)}"
            if comment:
                details_str += f"\n💬 Комментарий: {comment}"

            await update.message.reply_text(
                f"🎉 *Отлично, {name}! Твоё участие подтверждено!*\n"
                f"{details_str}\n\n"
                f"Меню всех 5 кухонь доступно в мини-аппе в любое время 👆",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                "😢 *Очень жаль, что ты не сможешь прийти.*\n\n"
                "Если передумаешь — открой мини-апп снова или напиши /start!",
                parse_mode="Markdown",
            )

        # Уведомляем админа
        admin_id = get_admin_id()
        if admin_id:
            status_text = "✅ ПРИНЯЛ(А)" if status == "accepted" else "❌ ОТКАЗАЛСЯ(АСЬ)"
            admin_msg = (
                f"📨 *Новый ответ из Mini App!*\n\n"
                f"👤 {name} (@{user.username or 'нет'})\n"
                f"📌 Статус: {status_text}\n"
                f"👥 Человек: {guests}\n"
            )
            if drink:
                admin_msg += f"🍷 Напитки: {drink}\n"
            if selected_dishes:
                admin_msg += f"⭐ В приоритете ({len(selected_dishes)}): {', '.join(selected_dishes)}\n"
            if refused_dishes:
                admin_msg += f"🚫 Отказано ({len(refused_dishes)}): {', '.join(refused_dishes)}\n"
            if comment:
                admin_msg += f"💬 Заметка: {comment}\n"
            admin_msg += f"🕐 Время: {response['timestamp']}"

            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_msg,
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление админу: {e}")

        logger.info(f"Response saved for user {user.id}: {response}")

    except Exception as e:
        logger.error(f"Ошибка обработки данных webapp: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка при сохранении ответа. Попробуй ещё раз.")


# ─── ЗАПУСК ──────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("🚀 Запуск Telegram Invite Bot...")
    print(f"📁 Файл базы ответов: {DATA_FILE}")

    if not TOKEN or TOKEN in ["ВСТАВЬ_СЮДА_ТОКЕН_ОТ_BOTFATHER", "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"]:
        print("\n❌ ОШИБКА: BOT_TOKEN не указан или содержит пример!")
        print("1. Открой файл .env в папке проекта")
        print("2. Вставь свой реальный токен: BOT_TOKEN=твой_токен_от_BotFather")
        print("=" * 60)
        return

    if not WEBAPP_URL or WEBAPP_URL in ["https://твой-домен.com", "https://example.com", "https://твой-домен.vercel.app"]:
        print("\n⚠️  ВНИМАНИЕ: WEBAPP_URL имеет значение по умолчанию.")
        print("   Для работы Mini App в Telegram укажи публичный HTTPS адрес")
        print("   (например, через: npx localtunnel --port 8000)")
        print("   и обнови WEBAPP_URL в файле .env\n")
    else:
        print(f"🌐 WebApp URL: {WEBAPP_URL}")

    admin_id = get_admin_id()
    if admin_id:
        print(f"👤 Админ Chat ID: {admin_id}")

    print("=" * 60)

    try:
        app = Application.builder().token(TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("stats", stats))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CallbackQueryHandler(button_callback, pattern=r"^rsvp_"))
        app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_data))

        print("🤖 Бот успешно запущен и слушает события! Нажми Ctrl+C для остановки.")
        app.run_polling()
    except Exception as e:
        if "InvalidToken" in type(e).__name__ or "Unauthorized" in str(e):
            print(f"\n❌ Ошибка авторизации в Telegram API:")
            print(f"   Указанный токен бота недействителен.")
            print(f"   Проверь BOT_TOKEN в файле .env (получить правильный токен можно у @BotFather).")
        else:
            print(f"\n❌ Ошибка при запуске бота: {e}")


if __name__ == "__main__":
    main()
