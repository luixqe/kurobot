from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import json
import os
import asyncio

# === НАСТРОЙКИ ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7893930092:AAGz7Ux2NQqN0hzHKyaTsZYc-s7p3f77Se8")
ADMIN_ID = 7433300763
DATA_FILE = "submissions.json"
PAGE_SIZE = 7

# Загрузка данных
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# Сохранение данных
def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Клавиатура обычного пользователя
def get_user_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("Я отправил заявку ✅")]],
        resize_keyboard=True,
        one_time_keyboard=False
    )

# Клавиатура админа
def get_admin_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("Все заявки 📋")],
            [KeyboardButton("Назад 🔙")]
        ],
        resize_keyboard=True
    )

# Главное сообщение
async def send_welcome_message(update: Update):
    message = (
        "☑️ПАРТНЕР СЕРВИСА ЯНДЕКС ЕДА В ПОИСКАХ КУРЬЕРОВ🔎\n\n"
        "Быстрое подключение и выход на ежедневный доход 📳\n\n"
        "❗Как начать выполнять заказы❓❗\n\n"
        "✔️ Пройди регистрацию по ссылке ниже;\n"
        "✔️ Заполни короткую анкету и пройди обучение;\n"
        "✔️ Приезжай на оформление в офис за экипировкой и коробом (бесплатно);\n"
        "✔️ Получай заказы и выплату на карту еженедельно\n\n"
        "👇👇👇\n\n"
        "https://clk.li/RHzy\n"
        "https://clk.li/RHzy\n"
        "https://clk.li/RHzy\n\n"
        "После отправки заявки, нажмите кнопку ниже"
    )
    await update.message.reply_text(message, reply_markup=get_user_keyboard())

# Обработка заявки
async def handle_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    username = user.username or "нет_юзернейма"
    first_name = user.first_name or ""
    last_name = user.last_name or ""

    data = load_data()

    if any(item["user_id"] == user_id for item in data):
        await update.message.reply_text("✅ Вы уже отправили заявку!", reply_markup=get_user_keyboard())
        return

    data.append({
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name
    })
    save_data(data)

    await update.message.reply_text(
        "✅ Отлично! Ваша заявка принята. Мы свяжемся с вами в ближайшее время!",
        reply_markup=get_user_keyboard()
    )

    # Уведомление админа (в фоне)
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🆕 Новая заявка!\nID: {user_id}\nUsername: @{username}\nИмя: {first_name} {last_name}"
        )
    except Exception as e:
        print(f"Ошибка уведомления админа: {e}")

# Отправка страницы заявок
async def send_page(query_or_update, context: ContextTypes.DEFAULT_TYPE, data, page):
    total = len(data)
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)

    text = f"📋 Заявки ({start + 1}-{end} из {total})\n\n"
    for item in data[start:end]:
        uid = item["user_id"]
        uname = item["username"]
        fname = item["first_name"]
        lname = item["last_name"]

        if uname != "нет_юзернейма":
            link = f"@{uname}"
        else:
            link = f"[ID {uid}](tg://user?id={uid})"

        text += f"• {fname} {lname} — {link}\n"

    # Кнопки пагинации
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"page_{page-1}"))
    if page < total_pages - 1:
        buttons.append(InlineKeyboardButton("▶️ Вперед", callback_data=f"page_{page+1}"))
    buttons.append(InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu"))

    markup = InlineKeyboardMarkup([buttons])

    # Определяем, откуда вызов: из callback или из сообщения
    if hasattr(query_or_update, 'callback_query') and query_or_update.callback_query:
        try:
            await query_or_update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
        except Exception as e:
            print(f"❌ Ошибка редактирования сообщения: {e}")
    else:
        try:
            await query_or_update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")
        except Exception as e:
            print(f"❌ Ошибка отправки сообщения: {e}")

# Обработка сообщений от всех
async def handle_any_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else ""

    # Админ
    if user_id == ADMIN_ID:
        if text == "Назад 🔙":
            await update.message.reply_text("🏠 Главное меню", reply_markup=get_user_keyboard())
        elif text == "Все заявки 📋":
            data = load_data()
            if not data:
                await update.message.reply_text("📭 Нет заявок", reply_markup=get_admin_keyboard())
            else:
                await send_page(update, context, data, page=0)
        else:
            # Любое другое сообщение → показываем админку
            await update.message.reply_text("🔧 Админ-меню", reply_markup=get_admin_keyboard())
        return

    # Обычный пользователь
    if text == "Я отправил заявку ✅":
        await handle_submission(update, context)
    else:
        await send_welcome_message(update)

# Обработка callback-кнопок (пагинация) — БЕЗ БЛОКИРОВКИ!
async def pagination_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # МГНОВЕННО отвечаем!

    # Запускаем обработку в фоне
    asyncio.create_task(handle_pagination_async(query, context))

async def handle_pagination_async(query, context):
    data = load_data()
    if not data:
        try:
            await query.edit_message_text("📭 Нет заявок")
        except Exception as e:
            print(f"❌ Ошибка при редактировании: {e}")
        return

    if query.data == "back_to_menu":
        try:
            await query.edit_message_text("🔧 Админ-меню", reply_markup=get_admin_keyboard())
        except Exception as e:
            print(f"❌ Ошибка при редактировании: {e}")
        return

    if query.data.startswith("page_"):
        try:
            page = int(query.data.split("_")[1])
            await send_page(query, context, data, page)
        except Exception as e:
            try:
                await query.edit_message_text("❌ Ошибка загрузки страницы.")
            except:
                pass

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_welcome_message(update)

# Команда /admin (на всякий случай)
async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("🔧 Админ-меню", reply_markup=get_admin_keyboard())
    else:
        await update.message.reply_text("❌ Доступ запрещён.")

# Запуск
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_menu))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_any_message))
    app.add_handler(CallbackQueryHandler(pagination_handler))

    print("✅ Бот запущен! Нажмите Ctrl+C для остановки.")
    app.run_polling()

if __name__ == "__main__":
    main()
