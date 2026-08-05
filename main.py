import asyncio
import random
import os
import json
import time
from pyrogram import Client, filters
from pyrogram.types import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from aiohttp import web

# ===== ФИКС ДЛЯ PYTHON =====
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# ===== ВЕБ-СЕРВЕР ДЛЯ RENDER =====
async def health_check(request):
    return web.Response(text="UwU Bot is alive")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Веб-сервер запущен на порту {port}")
    while True:
        await asyncio.sleep(3600)

# ===== НАСТРОЙКИ БОТА И БД =====
API_ID = int(os.getenv("API_ID", 37635168))
API_HASH = os.getenv("API_HASH", "47e36b7f99b31f55be222b4200ea94ca")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Твой ID администратора уже вписан сюда
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "816984329").split(",")]

ALLOWED_USERS_FILE = "allowed_users.json"

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
        except:
            return default
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_allowed_users():
    # Твой ID также добавлен в список пользователей по умолчанию
    default_users = [816984329]
    users = load_json(ALLOWED_USERS_FILE, default_users)
    return [int(u) for u in users]

def save_allowed_users(users):
    save_json(ALLOWED_USERS_FILE, list(set(users)))

app = Client("uwu_inline_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# === ЛОГИКА УВУ-ФИКАЦИИ ===
last_actions = []

EMOJIS = [
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

def modify_word(w):
    if len(w) < 2:
        return w
    if w[0].isalpha() and random.random() < 0.4:
        stutters = random.randint(1, 2)
        prefix = "-".join([w[0].lower()] * stutters)
        w = f"{prefix}-{w.lower()}"
    if random.random() < 0.4:
        vowels = "аеёиоуыэюяАЕЁИОУЫЭЮЯ"
        for i in range(len(w)-1, -1, -1):
            if w[i] in vowels:
                w = w[:i] + w[i]*random.randint(1, 2) + w[i:]
                break
        w += "~"
    if random.random() < 0.35:
        w += " " + random.choice(EMOJIS)
    return w

def cringe_text(t):
    if not t: return t
    words = t.split()
    if not words: return t
    new_words = [modify_word(w) for w in words]
    action = get_random_action()
    action_emoji = random.choice(EMOJIS)
    return " ".join(new_words) + f"\n{action} {action_emoji}"

# === ИНЛАЙН ОБРАБОТЧИК ===
@app.on_inline_query()
async def inline_uwu(client, query):
    user_id = query.from_user.id
    allowed = load_allowed_users()
    
    # БЛОКИРОВКА ДОСТУПА В ИНЛАЙН РЕЖИМЕ
    if user_id not in allowed and user_id not in ADMIN_IDS:
        await query.answer(
            results=[
                InlineQueryResultArticle(
                    title="❌ У вас нет доступа!",
                    description="Обратитесь к администратору для выдачи прав.",
                    input_message_content=InputTextMessageContent("❌ У меня нет доступа.") # Отправляется без тегов бота
                )
            ],
            cache_time=0
        )
        return

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

    uwu_text = cringe_text(text)
    
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
def get_start_keyboard(user_id):
    buttons = []
    if user_id in ADMIN_IDS:
        buttons.append([InlineKeyboardButton("Логи", callback_data="logs"), InlineKeyboardButton("Юзеры", callback_data="users")])
        buttons.append([InlineKeyboardButton("➕ Добавить юзера", callback_data="add_user"), InlineKeyboardButton("➖ Убрать юзера", callback_data="remove_user")])
    return InlineKeyboardMarkup(buttons)

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    user_id = message.from_user.id
    if user_id in auth_steps: del auth_steps[user_id]
    
    allowed = load_allowed_users()
    if user_id not in allowed and user_id not in ADMIN_IDS:
        await message.reply(
            f"У вас нет доступа к боту.\nВаш ID: <code>{user_id}</code>\n\n"
            f"Для покупки доступа обратитесь к администратору.",
            parse_mode=ParseMode.HTML
        )
        add_bot_log(f"Попытка входа без доступа: ID {user_id}")
        return

    bot_info = await client.get_me()
    text = (
        f"<b>Приветик! Я УВУ-бот 🌸</b>\n\n"
        f"Я работаю прямо в строке ввода в любом чате.\n\n"
        f"Просто напиши мой юзернейм, а затем свой текст:\n"
        f"<code>@{bot_info.username} Привет, как дела?</code>\n\n"
        f"И я мгновенно переделаю твой текст!"
    )
    
    kb = get_start_keyboard(user_id)
    if kb.inline_keyboard:
        await message.reply(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        await message.reply(text, parse_mode=ParseMode.HTML)

@app.on_callback_query()
async def callback_handler(client, query: CallbackQuery):
    try:
        user_id = query.from_user.id
        
        if user_id not in ADMIN_IDS:
            await query.answer("Нет доступа!", show_alert=True)
            return

        data = query.data

        if data == "menu":
            if user_id in auth_steps: del auth_steps[user_id]
            bot_info = await client.get_me()
            text = (
                f"<b>Приветик! Я УВУ-бот 🌸</b>\n\n"
                f"Я работаю прямо в строке ввода в любом чате.\n\n"
                f"Просто напиши мой юзернейм, а затем свой текст:\n"
                f"<code>@{bot_info.username} Привет, как дела?</code>\n\n"
                f"И я мгновенно переделаю твой текст!"
            )
            kb = get_start_keyboard(user_id)
            await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)

        elif data == "add_user":
            auth_steps[user_id] = {"step": "wait_add_user"}
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="menu")]])
            await query.message.edit_text("<b>Добавление пользователя</b>\n\nВведите ID пользователя (только цифры):", reply_markup=kb, parse_mode=ParseMode.HTML)
            
        elif data == "remove_user":
            auth_steps[user_id] = {"step": "wait_remove_user"}
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="menu")]])
            await query.message.edit_text("<b>Удаление пользователя</b>\n\nВведите ID пользователя (только цифры):", reply_markup=kb, parse_mode=ParseMode.HTML)

        elif data == "logs":
            logs_text = "\n".join(bot_logs[-15:]) if bot_logs else "Логов пока нет"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("В меню", callback_data="menu")]])
            await query.message.edit_text(f"<b>Последние логи:</b>\n\n<code>{logs_text}</code>", reply_markup=kb, parse_mode=ParseMode.HTML)
            
        elif data == "users":
            allowed = load_allowed_users()
            users_list = "\n".join([f"• <code>{u}</code>" for u in allowed]) if allowed else "Список пуст"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("В меню", callback_data="menu")]])
            await query.message.edit_text(f"<b>Пользователи с доступом:</b>\n\n{users_list}", reply_markup=kb, parse_mode=ParseMode.HTML)
    finally:
        try:
            await query.answer()
        except:
            pass

@app.on_message(filters.text & filters.private)
async def fsm_handler(client, message):
    user_id = message.from_user.id
    if user_id not in auth_steps:
        return 

    state = auth_steps[user_id]
    step = state["step"]
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("В меню", callback_data="menu")]])

    if step == "wait_add_user":
        try:
            new_user = int(message.text.strip())
            allowed = load_allowed_users()
            if new_user not in allowed:
                allowed.append(new_user)
                save_allowed_users(allowed)
                await message.reply(f"✅ Пользователь <code>{new_user}</code> успешно добавлен в белый список.", reply_markup=kb, parse_mode=ParseMode.HTML)
                add_bot_log(f"Выдан доступ ID: {new_user}")
            else:
                await message.reply("У этого пользователя уже есть доступ.", reply_markup=kb)
            del auth_steps[user_id]
        except ValueError:
            await message.reply("ID должен быть числом! Попробуйте еще раз или нажмите Отмена.", reply_markup=kb)
            
    elif step == "wait_remove_user":
        try:
            target_user = int(message.text.strip())
            allowed = load_allowed_users()
            if target_user in allowed:
                allowed.remove(target_user)
                save_allowed_users(allowed)
                await message.reply(f"❌ Доступ для пользователя <code>{target_user}</code> успешно закрыт.", reply_markup=kb, parse_mode=ParseMode.HTML)
                add_bot_log(f"Забран доступ у ID: {target_user}")
            else:
                await message.reply("Этого пользователя и так нет в списке.", reply_markup=kb)
            del auth_steps[user_id]
        except ValueError:
            await message.reply("ID должен быть числом! Попробуйте еще раз или нажмите Отмена.", reply_markup=kb)


# === ЗАПУСК ===
def run_bot():
    if not BOT_TOKEN:
        print("❌ Ошибка: Вставь BOT_TOKEN в код или добавь в переменные среды Render!")
        return
        
    print("🚀 Уву-бот запускается в инлайн-режиме (с системой доступов)...")
    loop = asyncio.get_event_loop()
    loop.create_task(start_web_server())
    app.run()

if __name__ == "__main__":
    run_bot()
