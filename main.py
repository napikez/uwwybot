import asyncio
import random
import os
import json
import time

# ===== ФИКС ДЛЯ НОВЫХ ВЕРСИЙ PYTHON (ДО ИМПОРТА PYROGRAM) =====
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import emoji as emoji_lib

from pyrogram import Client, filters
from pyrogram.types import (
    InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup,
    InlineKeyboardButton, CallbackQuery, Message
)
from pyrogram.enums import ParseMode
from aiohttp import web

# ===== ВЕБ-СЕРВЕР ДЛЯ RENDER =====
async def health_check(request):
    return web.Response(text="UwU Bot is alive")

async def start_web_server():
    app_web = web.Application()
    app_web.router.add_get('/', health_check)
    runner = web.AppRunner(app_web)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Веб-сервер запущен на порту {port}")
    while True:
        await asyncio.sleep(3600)

# ===== НАСТРОЙКИ БОТА =====
API_ID = int(os.getenv("API_ID", 37635168))
API_HASH = os.getenv("API_HASH", "47e36b7f99b31f55be222b4200ea94ca")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ID администраторов
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "816984329").split(",")]

# ===== ФАЙЛЫ БД =====
USER_EMOJIS_FILE = "user_emojis.json"   # { "user_id": ["😀", "🔥", ...] }
SETTINGS_FILE = "bot_settings.json"     # { "start_text": str|None, "start_gif": str|None }

bot_logs = []
auth_steps = {}

def add_bot_log(message):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    bot_logs.append(log_entry)
    if len(bot_logs) > 150:
        bot_logs.pop(0)
    print(f"[ЛОГ] {log_entry}")

def load_json(filename, default):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_user_emojis():
    return load_json(USER_EMOJIS_FILE, {})

def save_user_emojis(data):
    save_json(USER_EMOJIS_FILE, data)

def load_settings():
    return load_json(SETTINGS_FILE, {"start_text": None, "start_gif": None})

def save_settings(data):
    save_json(SETTINGS_FILE, data)

app = Client("uwu_inline_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# === ЛОГИКА УВУ-ФИКАЦИИ ===
last_actions = []

DEFAULT_EMOJIS = [
    "<emoji id=5226632585395869585>🌸</emoji>", "<emoji id=5249483516512580976>🌸</emoji>",
    "<emoji id=5373355660433962421>🌸</emoji>", "<emoji id=5249347825610798910>🌸</emoji>",
    "<emoji id=5249205894121534423>🌸</emoji>", "<emoji id=5247256215192353637>🌸</emoji>",
    "<emoji id=5247229667999495079>🌸</emoji>", "<emoji id=5246902769448662937>🌸</emoji>",
    "<emoji id=5246765626847933225>🌸</emoji>", "<emoji id=5249080253443226488>🌸</emoji>",
    "<emoji id=5247159423809368431>🌸</emoji>", "<emoji id=5249302745634060646>🌸</emoji>",
    "<emoji id=5249095109735103154>🌸</emoji>", "<emoji id=5248997519488202086>🌸</emoji>",
    "<emoji id=5249295568743709387>🌸</emoji>", "<emoji id=5246739500561872447>🌸</emoji>",
    "<emoji id=5249492501584164118>🌸</emoji>", "<emoji id=5249150935720017805>🌸</emoji>",
    "✨", "🌸", "💖", "🥺", "🎀"
]

ACTIONS = [
    "*обнимает*", "*шлёпает*", "*прижимается*", "*краснеет*", "*смотрит глазками*",
    "*делает кусь*", "*мурлычет*", "*прячет взгляд*", "*виляет хвостиком*",
    "*целует в щёчку*", "*тянет ручки*", "*прячет лицо в ладошках*",
    "*смущенно улыбается*", "*нежно кусает*", "*теребит волосы*", "*дует губки*",
    "*прыгает на ручки*", "*тихо сопит*", "*накручивает прядь на палец*",
    "*жмётся ближе*", "*отводит глазки*", "*хлопает ресничками*", "*зарывается носом в шею*",
    "*урчит*", "*переминается с ножки на ножку*", "*прячется за спину*",
    "*гладит по щеке*", "*смотрит снизу вверх*", "*виновато опускает ушки*"
]

def get_random_action():
    global last_actions
    available = [a for a in ACTIONS if a not in last_actions[-5:]]
    if not available:
        available = ACTIONS.copy()
        last_actions.clear()
    choice = random.choice(available)
    last_actions.append(choice)
    if len(last_actions) > 15:
        last_actions.pop(0)
    return choice

def extract_emojis(text):
    """Достаёт отдельные юникод-эмодзи из текста (корректно разбивает ZWJ-последовательности, флаги и т.д.)."""
    if not text:
        return []
    return [item["emoji"] for item in emoji_lib.emoji_list(text)]

def get_user_emoji_pool(user_id):
    """Возвращает пул эмодзи для юзера: дефолтные + его собственные добавленные (если есть)."""
    custom = load_user_emojis().get(str(user_id), [])
    return DEFAULT_EMOJIS + custom if custom else DEFAULT_EMOJIS

def modify_word(w, emoji_pool):
    if len(w) < 2:
        return w
    if w[0].isalpha() and random.random() < 0.4:
        stutters = random.randint(1, 2)
        prefix = "-".join([w[0].lower()] * stutters)
        w = f"{prefix}-{w.lower()}"
    if random.random() < 0.4:
        vowels = "аеёиоуыэюяАЕЁИОУЫЭЮЯ"
        for i in range(len(w) - 1, -1, -1):
            if w[i] in vowels:
                w = w[:i] + w[i] * random.randint(1, 2) + w[i:]
                break
        w += "~"
    if random.random() < 0.35:
        w += " " + random.choice(emoji_pool)
    return w

def cringe_text(t, user_id):
    if not t:
        return t
    words = t.split()
    if not words:
        return t
    emoji_pool = get_user_emoji_pool(user_id)
    new_words = [modify_word(w, emoji_pool) for w in words]
    action = get_random_action()
    action_emoji = random.choice(emoji_pool)
    return " ".join(new_words) + f"\n{action} {action_emoji}"

# === ИНЛАЙН ОБРАБОТЧИК (доступен всем, без вайтлиста) ===
@app.on_inline_query()
async def inline_uwu(client, query):
    user_id = query.from_user.id
    text = query.query.strip()

    if not text:
        await query.answer(
            results=[
                InlineQueryResultArticle(
                    title="🌸 Введи текст для уву-фикации...",
                    description="Начни писать, и я его преобразую!",
                    input_message_content=InputTextMessageContent("Введите текст после юзернейма бота!")
                )
            ],
            cache_time=0
        )
        return

    uwu_text = cringe_text(text, user_id)

    await query.answer(
        results=[
            InlineQueryResultArticle(
                title="✨ Отправить УВУ-текст",
                description=uwu_text[:60] + "...",
                input_message_content=InputTextMessageContent(uwu_text, parse_mode=ParseMode.HTML)
            )
        ],
        cache_time=0
    )

# === СИСТЕМА УПРАВЛЕНИЯ БОТОМ (МЕНЮ) ===
DEFAULT_START_TEXT = (
    "<b>Приветик! Я УВУ-бот 🌸</b>\n\n"
    "Я работаю прямо в строке ввода в любом чате.\n\n"
    "Просто напиши мой юзернейм, а затем свой текст:\n"
    "<code>@{username} Привет, как дела?</code>\n\n"
    "И я мгновенно переделаю твой текст!"
)

def get_start_keyboard(user_id):
    buttons = []
    buttons.append([InlineKeyboardButton("➕ Добавить эмодзи", callback_data="add_emojis")])

    if user_id in ADMIN_IDS:
        buttons.append([InlineKeyboardButton("📋 Логи", callback_data="logs")])
        buttons.append([InlineKeyboardButton("✏️ Текст /start", callback_data="add_start_text")])
        buttons.append([
            InlineKeyboardButton("🎞 GIF /start", callback_data="add_gif"),
            InlineKeyboardButton("🗑 Убрать GIF", callback_data="remove_gif")
        ])
    return InlineKeyboardMarkup(buttons)

async def build_start_content(client, user_id):
    """Возвращает (menu_text, gif_file_id_or_none) — обычный текст меню для команды /start."""
    settings = load_settings()
    bot_info = await client.get_me()
    text = DEFAULT_START_TEXT.format(username=bot_info.username)
    gif = settings.get("start_gif")
    return text, gif

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message: Message):
    user_id = message.from_user.id
    if user_id in auth_steps:
        del auth_steps[user_id]

    settings = load_settings()
    promo_text = settings.get("start_text")

    # Для обычных юзеров сначала кидаем рекламный текст (если он задан админом)
    if user_id not in ADMIN_IDS and promo_text:
        await message.reply(promo_text, parse_mode=ParseMode.HTML)

    # А затем — обычное меню, как и раньше
    text, gif = await build_start_content(client, user_id)
    kb = get_start_keyboard(user_id)

    if gif:
        await message.reply_animation(gif, caption=text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        await message.reply(text, reply_markup=kb, parse_mode=ParseMode.HTML)

@app.on_callback_query()
async def callback_handler(client, query: CallbackQuery):
    try:
        user_id = query.from_user.id
        data = query.data

        if data == "menu":
            if user_id in auth_steps:
                del auth_steps[user_id]
            text, _ = await build_start_content(client, user_id)
            kb = get_start_keyboard(user_id)
            try:
                await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
            except Exception:
                # если исходное сообщение было гифкой (caption), текст не редактируется тем же методом
                await query.message.edit_caption(text, reply_markup=kb, parse_mode=ParseMode.HTML)

        elif data == "add_emojis":
            auth_steps[user_id] = {"step": "wait_add_emojis"}
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="menu")]])
            await query.message.edit_text(
                "<b>Добавление эмодзи</b>\n\n"
                "Отправь одним сообщением любые эмодзи подряд (можно вперемешку, без запятых) — "
                "я их распознаю и буду использовать вместе с обычными в твоих уву-текстах.",
                reply_markup=kb, parse_mode=ParseMode.HTML
            )

        elif data == "add_start_text" and user_id in ADMIN_IDS:
            auth_steps[user_id] = {"step": "wait_add_start_text"}
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="menu")]])
            await query.message.edit_text(
                "<b>Текст для /start</b>\n\n"
                "Отправь текст (можно с HTML-разметкой), который будут видеть обычные пользователи "
                "при команде /start.",
                reply_markup=kb, parse_mode=ParseMode.HTML
            )

        elif data == "add_gif" and user_id in ADMIN_IDS:
            auth_steps[user_id] = {"step": "wait_add_gif"}
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="menu")]])
            await query.message.edit_text(
                "<b>GIF для /start</b>\n\n"
                "Пришли GIF-анимацию (как файл/анимацию в Telegram), она будет прикрепляться "
                "к сообщению /start у всех пользователей.",
                reply_markup=kb, parse_mode=ParseMode.HTML
            )

        elif data == "remove_gif" and user_id in ADMIN_IDS:
            settings = load_settings()
            settings["start_gif"] = None
            save_settings(settings)
            await query.answer("GIF удалён!", show_alert=True)
            text, _ = await build_start_content(client, user_id)
            kb = get_start_keyboard(user_id)
            try:
                await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
            except Exception:
                pass
            return

        elif data == "logs" and user_id in ADMIN_IDS:
            logs_text = "\n".join(bot_logs[-15:]) if bot_logs else "Логов пока нет"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("В меню", callback_data="menu")]])
            await query.message.edit_text(f"<b>Последние логи:</b>\n\n<code>{logs_text}</code>", reply_markup=kb, parse_mode=ParseMode.HTML)

    finally:
        try:
            await query.answer()
        except Exception:
            pass

@app.on_message(filters.private & ~filters.command("start"))
async def fsm_handler(client, message: Message):
    user_id = message.from_user.id
    if user_id not in auth_steps:
        return

    state = auth_steps[user_id]
    step = state["step"]
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("В меню", callback_data="menu")]])

    if step == "wait_add_emojis":
        found = extract_emojis(message.text or "")

        if not found:
            await message.reply(
                "Не нашёл ни одного эмодзи в сообщении! Пришли их ещё раз одним сообщением.",
                reply_markup=kb
            )
            return

        data = load_user_emojis()
        current = data.get(str(user_id), [])
        merged = list(dict.fromkeys(current + found))  # без дублей, сохраняя порядок
        data[str(user_id)] = merged
        save_user_emojis(data)

        await message.reply(
            f"✅ Добавлено эмодзи: {len(found)} (всего сохранено: {len(merged)}).\n"
            f"Теперь они будут появляться в твоих уву-текстах! 🌸",
            reply_markup=kb
        )
        add_bot_log(f"Юзер {user_id} добавил {len(found)} эмодзи: {found}")
        del auth_steps[user_id]

    elif step == "wait_add_start_text":
        if user_id not in ADMIN_IDS:
            del auth_steps[user_id]
            return
        new_text = message.text or message.caption
        if not new_text:
            await message.reply("Пришли текстовое сообщение!", reply_markup=kb)
            return
        settings = load_settings()
        settings["start_text"] = new_text
        save_settings(settings)
        await message.reply("✅ Текст для /start обновлён!", reply_markup=kb, parse_mode=ParseMode.HTML)
        add_bot_log(f"Админ {user_id} обновил текст /start")
        del auth_steps[user_id]

    elif step == "wait_add_gif":
        if user_id not in ADMIN_IDS:
            del auth_steps[user_id]
            return
        if not message.animation:
            await message.reply("Это не похоже на GIF! Пришли анимацию (GIF-файл).", reply_markup=kb)
            return
        settings = load_settings()
        settings["start_gif"] = message.animation.file_id
        save_settings(settings)
        await message.reply("✅ GIF для /start обновлён!", reply_markup=kb)
        add_bot_log(f"Админ {user_id} обновил GIF /start")
        del auth_steps[user_id]


# === ЗАПУСК ===
def run_bot():
    if not BOT_TOKEN:
        print("❌ Ошибка: Вставь BOT_TOKEN в код или добавь в переменные среды Render!")
        return

    print("🚀 Уву-бот запускается в инлайн-режиме (доступ для всех + свои эмодзи)...")
    loop = asyncio.get_event_loop()
    loop.create_task(start_web_server())
    app.run()

if __name__ == "__main__":
    run_bot()
