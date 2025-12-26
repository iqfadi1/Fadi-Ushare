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
        "/addpackage PRICE NAME\n"
        "/setprice PACKAGE_ID PRICE\n"
        "/setname PACKAGE_ID NAME\n"
        "/disablepackage PACKAGE_ID\n"
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

@dp.message(Command("userinfo"))
async def userinfo_cmd(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return

    parts = msg.text.split()
    if len(parts) != 2:
        await msg.answer("Usage: /userinfo PHONE")
        return

    u = db.get_user_by_phone(parts[1])
    if not u:
        await msg.answer("❌ User not found")
        return

    await msg.answer(
        f"👤 User Info\n"
        f"📱 Phone: {u['phone']}\n"
        f"💰 Balance: {db.fmt_lbp(int(u['balance']))} LBP\n"
        f"🆔 ID: {u['id']}"
    )

@dp.message(Command("addbalance"))
async def addbalance_cmd(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return

    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        await msg.answer("Usage: /addbalance PHONE AMOUNT")
        return

    phone = parts[1]
    amt = parse_amount(parts[2])

    if not db.get_user_by_phone(phone):
        await msg.answer("❌ User not found")
        return

    db.add_balance(phone, amt)
    await msg.answer(f"✅ Added {db.fmt_lbp(amt)} LBP to {phone}")

@dp.message(Command("setbalance"))
async def setbalance_cmd(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return

    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        await msg.answer("Usage: /setbalance PHONE AMOUNT")
        return

    phone = parts[1]
    amt = parse_amount(parts[2])

    db.set_balance(phone, amt)
    await msg.answer(f"✅ Balance set to {db.fmt_lbp(amt)} LBP for {phone}")

@dp.message(Command("deductbalance"))
async def deductbalance_cmd(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return

    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        await msg.answer("Usage: /deductbalance PHONE AMOUNT")
        return

    phone = parts[1]
    amt = parse_amount(parts[2])

    db.deduct_balance(phone, amt)
    await msg.answer(f"✅ Deducted {db.fmt_lbp(amt)} LBP from {phone}")

# ---------- PACKAGES ----------

@dp.message(Command("packages"))
async def packages_cmd(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return

    pkgs = db.list_packages(active_only=False)
    text = "📦 Packages:\n\n"
    for p in pkgs:
        status = "✅" if int(p["active"]) == 1 else "❌"
        text += f"{status} ID {p['id']} | {p['name']} | {db.fmt_lbp(int(p['price']))} LBP\n"

    await msg.answer(text)

@dp.message(Command("addpackage"))
async def addpackage_cmd(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return

    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        await msg.answer("Usage: /addpackage PRICE NAME")
        return

    price = parse_amount(parts[1])
    name = parts[2]

    db.add_package(name, price)
    await msg.answer(f"✅ Package added: {name}")

@dp.message(Command("setprice"))
async def setprice_cmd(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return

    parts = msg.text.split()
    if len(parts) != 3:
        await msg.answer("Usage: /setprice PACKAGE_ID PRICE")
        return

    pid = int(parts[1])
    price = parse_amount(parts[2])

    db.set_package_price(pid, price)
    await msg.answer("✅ Price updated")

@dp.message(Command("setname"))
async def setname_cmd(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return

    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        await msg.answer("Usage: /setname PACKAGE_ID NAME")
        return

    pid = int(parts[1])
    name = parts[2]

    db.set_package_name(pid, name)
    await msg.answer("✅ Name updated")

@dp.message(Command("disablepackage"))
async def disablepackage_cmd(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return

    parts = msg.text.split()
    if len(parts) != 2:
        await msg.answer("Usage: /disablepackage PACKAGE_ID")
        return

    pid = int(parts[1])
    db.disable_package(pid)
    await msg.answer("✅ Package disabled")

# ================== CALLBACKS ==================

@dp.callback_query()
async def callbacks(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    try:
        action, oid_s = call.data.split(":")
        oid = int(oid_s)
    except Exception:
        await call.answer("Bad callback", show_alert=True)
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
        await call.message.edit_text("✅ Order Approved")
        await call.answer("Approved")

    elif action == "reject":
        db.update_order_status(oid, "rejected")
        await call.message.edit_text("❌ Order Rejected")
        await call.answer("Rejected")

# ================== RUN ==================

async def run_polling():
    await dp.start_polling(bot)
