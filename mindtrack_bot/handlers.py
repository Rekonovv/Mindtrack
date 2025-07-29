from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler, JobQueue
from utils import save_food, save_water, get_water_summary, save_reflection, get_day_summary
import os
from datetime import datetime
# отключено GPT
# from ai_analysis import analyze_food, analyze_reflection

# ===== Task Tracker =====
TASKS_DIR = "tasks"
os.makedirs(TASKS_DIR, exist_ok=True)

TASK_ADD = 1000  # новое состояние для добавления задачи

def get_tasks_file(chat_id):
    return os.path.join(TASKS_DIR, f"tasks_{chat_id}.txt")

def load_tasks(chat_id):
    path = get_tasks_file(chat_id)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    tasks = []
    for line in lines:
        # Формат: задача|дата1,дата2,...
        if "|" in line:
            name, dates = line.split("|", 1)
            done_dates = set(dates.split(",")) if dates else set()
        else:
            name = line
            done_dates = set()
        tasks.append({"name": name, "done": done_dates})
    return tasks

def save_tasks(chat_id, tasks):
    path = get_tasks_file(chat_id)
    with open(path, "w", encoding="utf-8") as f:
        for t in tasks:
            dates = ",".join(sorted(t["done"]))
            f.write(f"{t['name']}|{dates}\n")

async def addtask_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❔ Что добавить в задачи? Напиши текст задачи.")
    return TASK_ADD

async def addtask_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    task_name = update.message.text.strip()
    if not task_name:
        await update.message.reply_text("❕ Задача не может быть пустой! Попробуй ещё раз.")
        return TASK_ADD
    tasks = load_tasks(chat_id)
    tasks.append({"name": task_name, "done": set()})
    save_tasks(chat_id, tasks)
    await update.message.reply_text(f"➕ Задача добавлена: {task_name}")
    return ConversationHandler.END

async def mytasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    tasks = load_tasks(chat_id)
    if not tasks:
        await update.message.reply_text("❕ У тебя пока нет задач. Добавь через /addtask")
        return
    today = datetime.now().strftime("%Y-%m-%d")
    msg = "<b>Твои задачи:</b>\n"
    for i, t in enumerate(tasks, 1):
        status = "✅" if today in t["done"] else "⬜"
        msg += f"{i}. {t['name']} {status}\n"
    msg += "\n<b>❕ Чтобы отметить задачу выполненной: /donetask номер</b>"
    await update.message.reply_text(msg, parse_mode="HTML")

async def donetask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    tasks = load_tasks(chat_id)
    if not tasks:
        await update.message.reply_text("❕ Нет задач для отметки. Добавь через /addtask")
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("<b>❕ Используй:</b> /donetask номер задачи", parse_mode="HTML")
        return
    idx = int(context.args[0]) - 1
    if idx < 0 or idx >= len(tasks):
        await update.message.reply_text("❕ Неверный номер задачи.")
        return
    today = datetime.now().strftime("%Y-%m-%d")
    tasks[idx]["done"].add(today)
    save_tasks(chat_id, tasks)
    await update.message.reply_text(f"❕ Задача '{tasks[idx]['name']}' отмечена как выполненная сегодня!")

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler, JobQueue
from utils import save_food, save_water, get_water_summary, save_reflection, get_day_summary

import os
from datetime import datetime
from ai_analysis import analyze_food, analyze_reflection
import asyncio

# Универсальная команда отмены для завершения любого диалога
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❕ Действие отменено. Можешь ввести новую команду!",
        parse_mode="HTML"
    )
    return ConversationHandler.END


# Состояния
FOOD, REFLECTION, WATER = range(3)

# Список цитат для утренних сообщений
MORNING_QUOTES = [
    "Каждое утро — это новый шанс начать сначала.",
    "Улыбнись новому дню и он улыбнётся тебе в ответ!",
    "Сегодня — лучший день, чтобы стать лучше, чем вчера.",
    "Пусть этот день принесёт тебе радость и вдохновение!",
    "Верь в себя — и всё получится!",
    "Сделай сегодня то, о чём завтра будешь гордиться.",
    "Пусть твои мысли будут светлыми, а сердце — спокойным.",
    "Каждый день — это маленькая жизнь.",
    "Начни утро с благодарности и день сложится удачно.",
    "Ты способен(на) на большее, чем думаешь!"
]

import random

async def send_morning_quote(context: ContextTypes.DEFAULT_TYPE):
    quote = random.choice(MORNING_QUOTES)
    for chat_id in list(registered_chats):
        try:
            await context.bot.send_message(chat_id=chat_id, text=f"⛅ Доброе утро!\n<b>{quote}</b>", parse_mode="HTML")
        except Exception:
            pass


async def delete_message_later(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data['chat_id']
    message_id = context.job.data['message_id']
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

async def water_reminder(context: ContextTypes.DEFAULT_TYPE):
    # Берём актуальный список чатов на каждый вызов
    for chat_id in list(registered_chats):
        try:
            msg = await context.bot.send_message(chat_id=chat_id, text="🔔 Не забудь выпить воды!")
            # Запланировать удаление через 10 минут (600 секунд)
            context.job_queue.run_once(
                delete_message_later,
                when=600,
                data={'chat_id': chat_id, 'message_id': msg.message_id}
            )
        except Exception:
            pass

REGISTERED_CHATS_FILE = "registered_chats.txt"
def load_registered_chats():
    if os.path.exists(REGISTERED_CHATS_FILE):
        with open(REGISTERED_CHATS_FILE, "r", encoding="utf-8") as f:
            return set(int(line.strip()) for line in f if line.strip().isdigit())
    return set()

def save_registered_chats():
    with open(REGISTERED_CHATS_FILE, "w", encoding="utf-8") as f:
        for chat_id in registered_chats:
            f.write(f"{chat_id}\n")

registered_chats = load_registered_chats()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    registered_chats.add(update.effective_chat.id)
    save_registered_chats()
    await update.message.reply_text(
        "<b>Привет! 🤍</b>\n"
        "\n"
        "Здесь ты можешь быть настоящим.\n"
        "Запиши то, что хочешь сохранить — даже если это просто мысль.\n"
        "\n"
        "<b>\"Будь собой. Все остальные роли уже заняты.\"\n"
        "— Оскар Уайльд</b>",
        parse_mode="HTML"
    )

# Еда
async def eat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Что ты ел? 🍽️\n"
        "Напиши, например: завтрак - овсянка и банан.\n"
        "\n"
        "<b>Пусть каждый приём пищи станет маленьким ритуалом заботы о себе!</b>",
        parse_mode="HTML"
    )
    return FOOD

async def handle_food(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id
    if "-" in text:
        label, meal = map(str.strip, text.split("-", 1))
        save_food(label, meal, chat_id)
        # GPT-анализ еды (через executor)
        try:
            loop = asyncio.get_running_loop()
            advice = await loop.run_in_executor(None, analyze_food, meal)
        except Exception:
            import traceback
            print("[GPT FOOD ERROR]", traceback.format_exc())
            advice = ""
        await update.message.reply_text(
            f"➕ Приём пищи записан!\n\n<b>Совет: {advice}</b>",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "❕ Пожалуйста, используй формат: завтрак - овсянка и банан.\n"
            "\n"
            "<b>Это поможет мне лучше понимать твои привычки!</b>",
            parse_mode="HTML"
        )
    return ConversationHandler.END

# Вода
async def drink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Сколько воды ты выпил? 💧\n"
        "Напиши количество в мл, например: 250\n"
        "\n"
        "<b>Вода — твой источник энергии!</b>",
        parse_mode="HTML"
    )
    return WATER

async def handle_water(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id
    try:
        amount = int(text)
        save_water(amount, chat_id)
        await update.message.reply_text(
            f"➕ Записано: {amount} мл воды\n"
            "\n"
            "<b>Ты заботишься о себе!</b>",
            parse_mode="HTML"
        )
    except ValueError:
        await update.message.reply_text(
            "❕ Пожалуйста, введи число (например, 250).\n"
            "\n"
            "<b>Я помогу тебе отслеживать водный баланс!</b>",
            parse_mode="HTML"
        )
    return ConversationHandler.END

# Рефлексия
async def reflect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💭 Как прошёл твой день? Что ты чувствовал?\n"
        "\n"
        "<b>Поделись любыми мыслями или эмоциями. Я здесь, чтобы выслушать.</b>",
        parse_mode="HTML"
    )
    return REFLECTION

async def handle_reflection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    save_reflection(update.message.text, chat_id)
    # GPT-анализ рефлексии (через executor)
    try:
        loop = asyncio.get_running_loop()
        gpt_reply = await loop.run_in_executor(None, analyze_reflection, update.message.text)
    except Exception:
        import traceback
        print("[GPT REFLECTION ERROR]", traceback.format_exc())
        gpt_reply = "Анализ временно недоступен."
    await update.message.reply_text(
        f"➕ Рефлексия записана!\n\nGPT: {gpt_reply}\n\n<b>Спасибо, что доверяешь свои мысли!</b>",
        parse_mode="HTML"
    )
    return ConversationHandler.END

# Сводка
async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    summary_text = get_day_summary(chat_id)
    if not summary_text or summary_text.strip() == "":
        await update.message.reply_text(
            "➖ Пока нет записей. Всё пусто!\n"
            "\n"
            "<b>Начни с маленького шага — запиши что-нибудь!</b>",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "Вот твоя личная сводка за сегодня:\n\n" + summary_text
        )

# Сводка за выбранную дату
async def summary_by_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text(
            "Укажи дату в формате ДД.ММ.ГГГГ.\n"
            "\n"
            "<b>Например: /summarydate 25.05.2025</b>\n",
            parse_mode="HTML"
        )
        return
    date_str = context.args[0]
    try:
        # Проверяем формат даты ДД.ММ.ГГГГ
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
        date_iso = date_obj.strftime("%Y-%m-%d")
    except ValueError:
        await update.message.reply_text(
            "❕ Неверный формат даты. Используй ДД.ММ.ГГГГ\n"
            "\n"
            "<b>Например: 25.05.2025</b>\n",
            parse_mode="HTML"
        )
        return
    from utils import get_day_summary
    summary = get_day_summary(chat_id, date_override=date_iso)
    if not summary or summary.strip() == "":
        await update.message.reply_text(
            f"❕ Нет записей за {date_str}.\n\n<b>Попробуй другую дату!</b>",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            f"Твоя сводка за <b>{date_str}:</b>\n\n" + summary,
            parse_mode="HTML"
        )

# Очистка логов
async def clear_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from utils import get_today_folder
    chat_id = update.effective_chat.id
    folder = get_today_folder(chat_id)
    try:
        for filename in ["food.txt", "water.txt", "reflection.txt"]:
            path = os.path.join(folder, filename)
            if os.path.exists(path):
                os.remove(path)
        await update.message.reply_text(
            "❕ Все твои записи за сегодня удалены.\n"
            "\n"
            "<b>Новый день — новые возможности!</b>\n",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"Ошибка при очистке: {e}")

# Остановка напоминаний
async def stop_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in registered_chats:
        registered_chats.remove(chat_id)
        save_registered_chats()
        await update.message.reply_text(
            "🔕 Напоминания о воде отключены. Забота о себе — в твоих руках!"
        )
    else:
        await update.message.reply_text(
            "❕ У тебя и так не было активных напоминаний."
        )

# Регистрация хендлеров
def register_handlers(app):
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("addtask", addtask_start)],
        states={
            TASK_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, addtask_save)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    ))
    app.add_handler(CommandHandler("mytasks", mytasks))
    app.add_handler(CommandHandler("donetask", donetask))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("clear", clear_logs))
    app.add_handler(CommandHandler("stopreminder", stop_reminder))
    app.add_handler(CommandHandler("summarydate", summary_by_date))


    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("eat", eat)],
        states={FOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_food)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("drink", drink)],
        states={WATER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_water)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("reflect", reflect)],
        states={REFLECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reflection)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    ))

    # Запуск напоминания каждые 2 часа и утренней цитаты в 10:00
    async def schedule_reminders(app):
        job_queue = app.job_queue
        job_queue.run_repeating(water_reminder, interval=2*60*60, first=0)
        # Планируем отправку цитаты каждый день в 6:00 утра по локальному времени сервера
        from datetime import time
        job_queue.run_daily(send_morning_quote, time(hour=6, minute=0, second=0))
    app.post_init = schedule_reminders
