import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

import db
from security import hash_password, gen_password, parse_amount

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# ================== BOT SENDER ==================

class BotSender:
    async def notify_new_order(self, order_id: int):
        o = db.get_order(order_id)
        if not o:
            return

        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Approve", callback_data=f"approve:{order_id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"reject:{order_id}")
        ]])

        text = (
            "🆕 New Package Request\n\n"
            f"📱 Phone: {o['phone']}\n"
            f"👤 User: {o['user_number']}\n\n"
            f"📦 Package: {o['package_name']}\n"
            f"💰 Price: {db.fmt_lbp(int(o['package_price']))} LBP\n"
            f"💳 Current Balance: {db.fmt_lbp(int(o['balance']))} LBP\n\n"
            f"🧾 Order ID: {o['id']}"
        )

        await bot.send_message(ADMIN_ID, text, reply_markup=kb)

bot_sender = BotSender()

# ================== COMMANDS ==================

@dp.message(Command("start"))
async def start_cmd(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return
    await msg.answer(
        "Admin Panel ✅\n\n"
        "/createuser PHONE [PASSWORD]\n"
        "/userinfo PHONE\n"
        "/addbalance PHONE AMOUNT\n"
        "/setbalance PHONE AMOUNT\n"
        "/deductbalance PHONE AMOUNT\n"
        "/packages\n"
    )

# ---------- USERS ----------

@dp.message(Command("createuser"))
async def createuser_cmd(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return

    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Usage: /createuser PHONE [PASSWORD]")
        return

    phone = parts[1]
    password = parts[2] if len(parts) >= 3 else gen_password(6)

    if db.get_user_by_phone(phone):
        await msg.answer("❌ User already exists")
        return

    db.create_user(phone, hash_password(password))
    await msg.answer(f"✅ User Created\n📱 Phone: {phone}\n🔑 Password: {password}")

# ================== CALLBACKS ==================

@dp.callback_query()
async def callbacks(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer()
        return

    try:
        action, oid_s = call.data.split(":")
        oid = int(oid_s)
    except Exception:
        await call.answer()
        return

    o = db.get_order(oid)
    if not o:
        await call.answer("Order not found", show_alert=True)
        return

    if action == "approve":
        if int(o["balance"]) < int(o["package_price"]):
            await call.answer("Not enough balance", show_alert=True)
            return

        db.deduct_balance(o["phone"], int(o["package_price"]))
        db.update_order_status(oid, "approved")

        await call.message.edit_text(
            "✅ Order Approved",
            reply_markup=None
        )
        await call.answer("Approved")

    elif action == "reject":
        db.update_order_status(oid, "rejected")

        await call.message.edit_text(
            "❌ Order Rejected",
            reply_markup=None
        )
        await call.answer("Rejected")

# ================== RUN ==================

async def run_polling():
    await dp.start_polling(bot)
