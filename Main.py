# -*- coding: utf-8 -*-
import asyncio
import itertools
import logging
import sqlite3
from contextlib import contextmanager
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup as IKM,
    InlineKeyboardButton as IKB, BufferedInputFile
)

# ================= CONFIG =================
BOT_TOKEN = "9062068619:AAE0T3sL7zz66MSZsbRZSOgGj9ylYP2niFQ"  # BotFather থেকে নতুন Token দিন
MAIN_OWNER_IDS = [8614383351]
DB = "vpn.db"

# Payment / Support details: নিজের তথ্য বসান
PAYMENT_METHODS = {
    "bkash": "YOUR_BKASH_NUMBER",
    "nagad": "YOUR_NAGAD_NUMBER",
    "rocket": "YOUR_ROCKET_NUMBER",
}
SUPPORT_USERNAME = "@BangIadeshi"

# ================= Aᴍᴏɴ FONT (ORIGINAL STYLE) =================
_M = {
    **{chr(65+i): chr(0x1D400+i) for i in range(26)},
    **{chr(97+i): chr(0x1D41A+i) for i in range(26)},
    **{chr(48+i): chr(0x1D7CE+i) for i in range(10)}
}
def amon(t):
    return "".join(_M.get(c, c) for c in t)

# ================= DATABASE =================
def cn():
    db = sqlite3.connect(DB, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db

@contextmanager
def transaction():
    db = cn()
    try:
        db.execute("BEGIN IMMEDIATE")
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init():
    with cn() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            balance REAL DEFAULT 0,
            banned INTEGER DEFAULT 0,
            admin INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS stock(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, dtime TEXT, gmail TEXT, pw TEXT, exp TEXT,
            key TEXT, rate REAL, sold INTEGER DEFAULT 0, buyer INTEGER
        );
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid INTEGER, qty INTEGER, total REAL,
            ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS payments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid INTEGER, method TEXT, amount REAL, trx_id TEXT,
            status TEXT DEFAULT 'pending',
            ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_by INTEGER
        );
        CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY, value TEXT NOT NULL
        );
        """)
        # পুরোনো vpn.db থাকলেও নতুন কলাম যোগ হবে; পুরোনো ডেটা মুছবে না।
        cols = {r["name"] for r in db.execute("PRAGMA table_info(users)")}
        if "username" not in cols:
            db.execute("ALTER TABLE users ADD COLUMN username TEXT")
        if "full_name" not in cols:
            db.execute("ALTER TABLE users ADD COLUMN full_name TEXT")

DEFAULT_LABELS = {
    "u_buy": f"🛒 {amon('Bᴜʏ Pʀᴏᴅᴜᴄᴛ')}",
    "u_stock": f"📦 {amon('Sᴛᴏᴄᴋ')}",
    "u_addbal": f"💰 {amon('Aᴅᴅ Bᴀʟᴀɴᴄᴇ')}",
    "u_myinfo": f"👤 {amon('Mʏ Iɴғᴏ')}",
    "u_support": "📳 Support Team",
    "a_stock": "✅ Sᴛᴏᴄᴋ Aᴅᴅ",
    "a_rate": "💰 Rᴀᴛᴇ Uᴘᴅᴀᴛᴇ",
    "a_list": "👥 Aᴅᴍɪɴ Lɪsᴛ",
    "a_ban": "🚫 Bᴀɴ » Uɴʙᴀɴ",
    "a_bal": "💵 Bᴀʟᴀɴᴄᴇ +/-",
    "a_bc": "📢 Bʀᴏᴀᴅᴄᴀsᴛ",
    "a_addadm": "⚙️ Aᴅᴅ Aᴅᴍɪɴ",
    "a_edit": "✏️ Eᴅɪᴛ Bᴜᴛᴛᴏɴs",
}
def label(key):
    with cn() as db:
        row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else DEFAULT_LABELS[key]

def set_label(key, value):
    with cn() as db:
        db.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value)
        )

# ================= USER / ACCESS =================
def user(uid, username=None, full_name=None):
    with transaction() as db:
        db.execute(
            "INSERT OR IGNORE INTO users(user_id,username,full_name) VALUES(?,?,?)",
            (uid, username, full_name)
        )
        if username is not None or full_name is not None:
            db.execute(
                "UPDATE users SET username=COALESCE(?,username), "
                "full_name=COALESCE(?,full_name) WHERE user_id=?",
                (username, full_name, uid)
            )
        return db.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()

def is_own(uid):
    return uid in MAIN_OWNER_IDS

def is_adm(uid):
    if is_own(uid):
        return True
    with cn() as db:
        row = db.execute("SELECT admin FROM users WHERE user_id=?", (uid,)).fetchone()
    return bool(row and row["admin"])

def is_banned(uid):
    with cn() as db:
        row = db.execute("SELECT banned FROM users WHERE user_id=?", (uid,)).fetchone()
    return bool(row and row["banned"])

def stock_left():
    with cn() as db:
        return db.execute("SELECT COUNT(*) FROM stock WHERE sold=0").fetchone()[0]

# ================= KEYBOARDS =================
def kb_main(uid):
    rows = [
        [IKB(text=label("u_buy"), callback_data="buy")],
        [IKB(text=label("u_stock"), callback_data="stock")],
        [IKB(text=label("u_addbal"), callback_data="addbal")],
        [IKB(text=label("u_myinfo"), callback_data="myinfo")],
        [IKB(text=label("u_support"), callback_data="support")],
    ]
    if is_adm(uid):
        rows.append([IKB(text=f"⚙️ {amon('Aᴅᴍɪɴ Pᴀɴᴇʟ')}", callback_data="adpanel")])
    return IKM(inline_keyboard=rows)

def kb_back():
    return IKM(inline_keyboard=[[IKB(text="⬅️ Back", callback_data="menu")]])

def kb_admin(uid):
    rows = [
        [IKB(text=label("a_stock"), callback_data="a_stock")],
        [IKB(text=label("a_rate"), callback_data="a_rate")],
        [IKB(text=label("a_list"), callback_data="a_list")],
        [IKB(text=label("a_ban"), callback_data="a_ban")],
        [IKB(text=label("a_bal"), callback_data="a_bal")],
        [IKB(text=label("a_bc"), callback_data="a_bc")],
    ]
    if is_own(uid):
        rows += [
            [IKB(text=label("a_addadm"), callback_data="a_addadm")],
            [IKB(text=label("a_edit"), callback_data="a_edit")],
        ]
    rows.append([IKB(text="♻️ Bᴀᴄᴋ Mᴇɴᴜ", callback_data="menu")])
    return IKM(inline_keyboard=rows)

# ================= STATES =================
class S(StatesGroup):
    qty = State()
    stock = State()
    bal_uid = State()
    bal_amt = State()
    ban = State()
    addadm = State()
    bc = State()
    rate = State()
    pay_method = State()
    pay_amount = State()
    pay_trx = State()
    edit_choose = State()
    edit_text = State()

# ================= BOT =================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
SPIN = itertools.cycle(["◐", "◓", "◑", "◒"])

async def animate(msg, base, steps=3):
    for _ in range(steps):
        try:
            await msg.edit_text(f"{base}  {next(SPIN)}")
        except Exception:
            pass
        await asyncio.sleep(0.25)
    try:
        await msg.edit_text(base)
    except Exception:
        pass

async def admin_guard(c):
    if not is_adm(c.from_user.id):
        await c.answer("⛔ Admin access required", show_alert=True)
        return False
    return True

async def owner_guard(c):
    if not is_own(c.from_user.id):
        await c.answer("⛔ Owner only", show_alert=True)
        return False
    return True

# ================= START / MENU =================
@dp.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    u = user(m.from_user.id, m.from_user.username, m.from_user.full_name)
    if u["banned"]:
        return await m.answer("🚫 আপনি ব্যান হয়েছেন।")
    msg = await m.answer("✨")
    await animate(
        msg,
        f"👋 {amon('Wᴇʟᴄᴏᴍᴇ')} {m.from_user.first_name}!\n\n"
        f"🎯 {amon('Pʀᴇᴍɪᴜᴍ Vᴘɴ')} — নিচে থেকে বেছে নিন 👇",
        steps=4
    )
    await msg.edit_reply_markup(reply_markup=kb_main(m.from_user.id))

@dp.callback_query(F.data == "menu")
async def menu(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.answer()
    if is_banned(c.from_user.id):
        return await c.message.edit_text("🚫 আপনি ব্যান হয়েছেন।")
    await c.message.edit_text(
        f"🏠 {amon('Mᴀɪɴ Mᴇɴᴜ')}\n\nনিচে থেকে বেছে নিন 👇",
        reply_markup=kb_main(c.from_user.id)
    )

@dp.callback_query(F.data == "support")
async def support(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.answer()
    await c.message.edit_text(
        f"📳 {amon('Sᴜᴘᴘᴏʀᴛ Tᴇᴀᴍ')}\n\n"
        f"যেকোনো সমস্যায় যোগাযোগ করুন:\n{SUPPORT_USERNAME}",
        reply_markup=kb_back()
    )

# ================= BUY / DELIVERY =================
@dp.callback_query(F.data == "buy")
async def buy(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.answer()
    if is_banned(c.from_user.id):
        return await c.answer("🚫 আপনি ব্যান হয়েছেন।", show_alert=True)
    if stock_left() <= 0:
        await c.message.edit_text(
            "❌ Sᴛᴏᴄᴋ Nᴏ Aᴠᴀɪʟᴀʙʟᴇ\n\nঅ্যাডমিনকে স্টক যোগ করতে বলুন।",
            reply_markup=kb_back()
        )
        for owner_id in MAIN_OWNER_IDS:
            try:
                await bot.send_message(owner_id, f"⛔ Sᴛᴏᴄᴋ Sᴏʟᴅ Oᴜᴛ!\nUser: {c.from_user.id}")
            except Exception:
                pass
        return
    await c.message.edit_text(
        "🛒 আপনি কয়টি Vᴘɴ নিতে চান? সংখ্যা লিখুন (যেমন: 1, 2, 3)",
        reply_markup=kb_back()
    )
    await state.set_state(S.qty)

@dp.message(S.qty)
async def do_qty(m: Message, state: FSMContext):
    if is_banned(m.from_user.id):
        await state.clear()
        return await m.answer("🚫 আপনি ব্যান হয়েছেন।")
    try:
        q = int((m.text or "").strip())
        if q < 1 or q > 50:
            raise ValueError
    except (ValueError, TypeError):
        return await m.answer("⚠️ ১ থেকে ৫০-এর মধ্যে সঠিক সংখ্যা লিখুন।")

    msg = await m.answer("⏳")
    await animate(msg, "⏳ আপনার Oʀᴅᴇʀ রেডি করা হচ্ছে...", 3)

    # একই transaction-এ stock reserve, balance check ও deduction হয়।
    with transaction() as db:
        rows = db.execute(
            "SELECT * FROM stock WHERE sold=0 ORDER BY id LIMIT ?", (q,)
        ).fetchall()
        if len(rows) < q:
            rows = None
        else:
            total = sum(float(r["rate"] or 0) for r in rows)
            u = db.execute("SELECT balance FROM users WHERE user_id=?",
                           (m.from_user.id,)).fetchone()
            balance = float(u["balance"] if u else 0)
            if balance < total:
                rows = "LOW_BALANCE"
            else:
                ids = [r["id"] for r in rows]
                db.executemany(
                    "UPDATE stock SET sold=1,buyer=? WHERE id=? AND sold=0",
                    [(m.from_user.id, item_id) for item_id in ids]
                )
                db.execute(
                    "UPDATE users SET balance=balance-? WHERE user_id=?",
                    (total, m.from_user.id)
                )
                db.execute(
                    "INSERT INTO orders(uid,qty,total) VALUES(?,?,?)",
                    (m.from_user.id, q, total)
                )

    if rows is None:
        await msg.edit_text(
            f"❌ স্টক অপর্যাপ্ত। আছে: {stock_left()}",
            reply_markup=kb_back()
        )
        return await state.clear()

    if rows == "LOW_BALANCE":
        await msg.edit_text(
            f"❌ Bᴀʟᴀɴᴄᴇ কম।\nপ্রয়োজন: {total:.2f} TK\n"
            f"আছে: {balance:.2f} TK\n\nAdd Balance ব্যবহার করুন।",
            reply_markup=kb_back()
        )
        return await state.clear()

    def block(it):
        return f"""===========================
{it['name']}  ( Dᴇʟɪᴠᴇʀʏ Tɪᴍᴇ : {it['dtime']} ) ✅
===========================
Gᴍᴀɪʟ : {it['gmail']}
Pᴀss : {it['pw']}
Exᴘɪʀɪʀᴇᴅ Tɪᴍᴇ : {it['exp']}

Gᴍᴀɪʟ এবং Pᴀss কাজ না করলে
Kᴇʏ ব্যবহার করুন...✅

Aᴄᴛɪᴠᴇ Kᴇʏ : {it['key']}
==============
Uᴘᴅᴀᴛᴇ Rᴀᴛᴇ : {it['rate']}
==============
Tʜᴀɴᴋs Fᴏʀ Sᴜᴘᴘᴏʀᴛ ❤️‍🔥"""

    txt = "\n\n".join(block(item) for item in rows)
    doc = BufferedInputFile(txt.encode("utf-8"), filename=f"VPN_{q}pcs.txt")
    try:
        await m.answer_document(
            document=doc,
            caption=f"✅ আপনার {q} টি Oʀᴅᴇʀ রেডি!\n"
                    f"💵 Tᴏᴛᴀʟ Aᴍᴏᴜɴᴛ : {total:.2f} TK\n\n"
                    "Tʜᴀɴᴋ Yᴏᴜ Cᴜsᴛᴏᴍᴇʀ ❤️‍🔥"
        )
    except Exception:
        # Delivery ব্যর্থ হলে স্বয়ংক্রিয় refund + stock release।
        with transaction() as db:
            db.execute("UPDATE users SET balance=balance+? WHERE user_id=?",
                       (total, m.from_user.id))
            db.execute("UPDATE stock SET sold=0,buyer=NULL WHERE buyer=? AND id IN (%s)" %
                       ",".join("?" for _ in rows),
                       [m.from_user.id] + [r["id"] for r in rows])
            db.execute("DELETE FROM orders WHERE id=(SELECT MAX(id) FROM orders WHERE uid=?)",
                       (m.from_user.id,))
        await m.answer("❌ ডকুমেন্ট পাঠানো যায়নি। টাকা ফেরত দেওয়া হয়েছে; আবার চেষ্টা করুন।")
        return await state.clear()

    await m.answer(
        "আরও কিনতে চান?",
        reply_markup=IKM(inline_keyboard=[
            [IKB(text="♻️ Nᴇᴡ Oʀᴅᴇʀ", callback_data="buy")],
            [IKB(text="🏠 Mᴀɪɴ Mᴇɴᴜ", callback_data="menu")]
        ])
    )
    if stock_left() == 0:
        for owner_id in MAIN_OWNER_IDS:
            try:
                await bot.send_message(
                    owner_id,
                    f"⚠️ Sᴛᴏᴄᴋ Oᴜᴛ!\nLᴀsᴛ Cᴜsᴛᴏᴍᴇʀ: {m.from_user.id} ({q} Pᴄs)"
                )
            except Exception:
                pass
    await state.clear()

# ================= STOCK / MY INFO =================
@dp.callback_query(F.data == "stock")
async def stock(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.answer()
    with cn() as db:
        sold = db.execute("SELECT COUNT(*) FROM stock WHERE sold=1").fetchone()[0]
    await c.message.edit_text(
        f"📦 {amon('Sᴛᴏᴄᴋ Dᴇᴛᴀɪʟs')}\n\n"
        f"✅ Aᴠᴀɪʟᴀʙʟᴇ : {stock_left()}\n🛒 Sᴏʟᴅ Oᴜᴛ : {sold}",
        reply_markup=kb_back()
    )

@dp.callback_query(F.data == "myinfo")
async def myinfo(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.answer()
    u = user(c.from_user.id, c.from_user.username, c.from_user.full_name)
    with cn() as db:
        stats = db.execute(
            "SELECT COUNT(*) orders, COALESCE(SUM(qty),0) pcs, "
            "COALESCE(SUM(total),0) spent FROM orders WHERE uid=?",
            (c.from_user.id,)
        ).fetchone()
        history = db.execute(
            "SELECT id,qty,total,ts FROM orders WHERE uid=? "
            "ORDER BY id DESC LIMIT 10", (c.from_user.id,)
        ).fetchall()
    uname = f"@{c.from_user.username}" if c.from_user.username else "Not Set"
    text = (
        f"👤 {amon('Mʏ Aᴄᴄᴏᴜɴᴛ Iɴғᴏ')}\n\n"
        f"🆔 User ID : {c.from_user.id}\n"
        f"👤 Name : {c.from_user.full_name}\n"
        f"📛 Username : {uname}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"💰 Balance : {float(u['balance']):.2f} TK\n"
        f"🛒 Total Orders : {stats['orders']}\n"
        f"📦 Total Products : {stats['pcs']} Pcs\n"
        f"💵 Total Spent : {float(stats['spent']):.2f} TK\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 {amon('Rᴇᴄᴇɴᴛ Oʀᴅᴇʀ Hɪsᴛᴏʀʏ')}\n\n"
    )
    if history:
        for order in history:
            text += (
                f"🆔 Order #{order['id']}\n"
                f"📦 Quantity : {order['qty']} Pcs\n"
                f"💰 Amount : {float(order['total']):.2f} TK\n"
                f"📅 Date : {order['ts']}\n"
                "━━━━━━━━━━━━━━━━━━\n"
            )
    else:
        text += "❌ এখনো কোনো Product কেনা হয়নি।"
    await c.message.edit_text(text, reply_markup=kb_back())

# ================= ADD BALANCE / PAYMENT APPROVAL =================
@dp.callback_query(F.data == "addbal")
async def addbal(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.answer()
    rows = [
        [IKB(text="📱 bKash", callback_data="pay_bkash")],
        [IKB(text="📱 Nagad", callback_data="pay_nagad")],
        [IKB(text="📱 Rocket", callback_data="pay_rocket")],
        [IKB(text="⬅️ Back", callback_data="menu")]
    ]
    await c.message.edit_text(
        f"💰 {amon('Aᴅᴅ Bᴀʟᴀɴᴄᴇ')}\n\n"
        "Payment Method নির্বাচন করুন।\n"
        "পেমেন্ট করার পর Amount ও Transaction ID দিতে হবে।\n"
        "Admin যাচাই করে Balance যোগ করবেন।",
        reply_markup=IKM(inline_keyboard=rows)
    )

@dp.callback_query(F.data.in_({"pay_bkash", "pay_nagad", "pay_rocket"}))
async def choose_payment(c: CallbackQuery, state: FSMContext):
    await c.answer()
    method = c.data.replace("pay_", "")
    number = PAYMENT_METHODS.get(method, "")
    await state.update_data(method=method)
    await c.message.edit_text(
        f"📱 {method.upper()} Payment\n\n"
        f"Send Money Number: {number}\n\n"
        "কত টাকা পাঠিয়েছেন? শুধু Amount লিখুন:",
        reply_markup=kb_back()
    )
    await state.set_state(S.pay_amount)

@dp.message(S.pay_amount)
async def payment_amount(m: Message, state: FSMContext):
    try:
        amount = float((m.text or "").strip())
        if amount <= 0 or amount > 100000:
            raise ValueError
    except (ValueError, TypeError):
        return await m.answer("⚠️ সঠিক Amount লিখুন।")
    await state.update_data(amount=amount)
    await m.answer("এখন Payment-এর Transaction ID (TrxID) পাঠান:")
    await state.set_state(S.pay_trx)

@dp.message(S.pay_trx)
async def payment_trx(m: Message, state: FSMContext):
    trx = (m.text or "").strip()
    if len(trx) < 4 or len(trx) > 100:
        return await m.answer("⚠️ সঠিক Transaction ID দিন।")
    data = await state.get_data()
    with transaction() as db:
        cur = db.execute(
            "INSERT INTO payments(uid,method,amount,trx_id) VALUES(?,?,?,?)",
            (m.from_user.id, data["method"], data["amount"], trx)
        )
        payment_id = cur.lastrowid
    await m.answer(
        f"✅ Payment Request জমা হয়েছে।\n"
        f"Request ID: #{payment_id}\n"
        "Admin যাচাই করার পর Balance যোগ হবে।"
    )
    for owner_id in MAIN_OWNER_IDS:
        try:
            await bot.send_message(
                owner_id,
                f"💳 NEW PAYMENT REQUEST #{payment_id}\n"
                f"User: {m.from_user.id}\nMethod: {data['method'].upper()}\n"
                f"Amount: {data['amount']:.2f} TK\nTrxID: {trx}",
                reply_markup=IKM(inline_keyboard=[[
                    IKB(text="✅ Approve", callback_data=f"payok:{payment_id}"),
                    IKB(text="❌ Reject", callback_data=f"payno:{payment_id}")
                ]])
            )
        except Exception:
            pass
    await state.clear()

@dp.callback_query(F.data.startswith("payok:"))
async def approve_payment(c: CallbackQuery):
    if not await owner_guard(c):
        return
    pid = int(c.data.split(":")[1])
    with transaction() as db:
        p = db.execute("SELECT * FROM payments WHERE id=?", (pid,)).fetchone()
        if not p or p["status"] != "pending":
            await c.answer("এই Request আগে Review করা হয়েছে।", show_alert=True)
            return
        db.execute("UPDATE payments SET status='approved',reviewed_by=? WHERE id=?",
                   (c.from_user.id, pid))
        db.execute("UPDATE users SET balance=balance+? WHERE user_id=?",
                   (p["amount"], p["uid"]))
    await c.answer("Approved")
    await c.message.edit_reply_markup(reply_markup=None)
    try:
        await bot.send_message(
            p["uid"], f"✅ আপনার Payment Approved!\n"
                      f"💰 Added Balance: {p['amount']:.2f} TK"
        )
    except Exception:
        pass

@dp.callback_query(F.data.startswith("payno:"))
async def reject_payment(c: CallbackQuery):
    if not await owner_guard(c):
        return
    pid = int(c.data.split(":")[1])
    with transaction() as db:
        p = db.execute("SELECT * FROM payments WHERE id=?", (pid,)).fetchone()
        if not p or p["status"] != "pending":
            await c.answer("এই Request আগে Review করা হয়েছে।", show_alert=True)
            return
        db.execute("UPDATE payments SET status='rejected',reviewed_by=? WHERE id=?",
                   (c.from_user.id, pid))
    await c.answer("Rejected")
    await c.message.edit_reply_markup(reply_markup=None)
    try:
        await bot.send_message(p["uid"], f"❌ Payment Request #{pid} Rejected হয়েছে।")
    except Exception:
        pass

# ================= ADMIN PANEL =================
@dp.callback_query(F.data == "adpanel")
async def adpanel(c: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await admin_guard(c):
        return
    await c.answer()
    await c.message.edit_text(
        f"⚙️ {amon('Aᴅᴍɪɴ Pᴀɴᴇʟ')}",
        reply_markup=kb_admin(c.from_user.id)
    )

@dp.callback_query(F.data == "a_stock")
async def a_stock(c: CallbackQuery, state: FSMContext):
    if not await admin_guard(c):
        return
    await c.answer()
    await c.message.edit_text(
        "✅ Sᴛᴏᴄᴋ Aᴅᴅ\n\nপ্রতি লাইনে একটি করে দিন:\n"
        "Name | Delivery | Gmail | Pass | Expired | Key | Rate\n\n"
        "উদাহরণ:\nExpressVPN | 5 min | a@gmail.com | 1234 | 30 days | KEY-XX | 50",
        reply_markup=kb_back()
    )
    await state.set_state(S.stock)

@dp.message(S.stock)
async def save_stock(m: Message, state: FSMContext):
    if not is_adm(m.from_user.id):
        return
    count = 0
    for line in (m.text or "").splitlines():
        parts = [x.strip() for x in line.split("|")]
        if len(parts) != 7 or not all(parts[:6]):
            continue
        try:
            rate = float(parts[6])
            if rate < 0:
                continue
            with cn() as db:
                db.execute(
                    "INSERT INTO stock(name,dtime,gmail,pw,exp,key,rate) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (*parts[:6], rate)
                )
            count += 1
        except (ValueError, sqlite3.Error):
            continue
    await m.answer(
        f"✅ {count} টি VPN স্টকে যোগ হয়েছে।",
        reply_markup=kb_admin(m.from_user.id)
    )
    await state.clear()

@dp.callback_query(F.data == "a_rate")
async def a_rate(c: CallbackQuery, state: FSMContext):
    if not await admin_guard(c):
        return
    await c.answer()
    await c.message.edit_text(
        "💰 সব Available VPN-এর নতুন Rate লিখুন (শুধু সংখ্যা):",
        reply_markup=kb_back()
    )
    await state.set_state(S.rate)

@dp.message(S.rate)
async def save_rate(m: Message, state: FSMContext):
    if not is_adm(m.from_user.id):
        return
    try:
        rate = float((m.text or "").strip())
        if rate < 0:
            raise ValueError
    except ValueError:
        return await m.answer("সঠিক সংখ্যা দিন।")
    with cn() as db:
        cur = db.execute("UPDATE stock SET rate=? WHERE sold=0", (rate,))
    await m.answer(
        f"✅ Updated {cur.rowcount} stock item(s).\nNew Rate: {rate:.2f}",
        reply_markup=kb_admin(m.from_user.id)
    )
    await state.clear()

@dp.callback_query(F.data == "a_list")
async def a_list(c: CallbackQuery):
    if not await admin_guard(c):
        return
    await c.answer()
    with cn() as db:
        rows = db.execute("SELECT user_id,username FROM users WHERE admin=1 ORDER BY user_id").fetchall()
    text = "👑 Oᴡɴᴇʀs:\n" + "\n".join(f"• {x}" for x in MAIN_OWNER_IDS)
    text += "\n\n👥 Aᴅᴍɪɴs:\n"
    text += "\n".join(
        f"• {r['user_id']} (@{r['username']})" if r["username"] else f"• {r['user_id']}"
        for r in rows
    ) or "—"
    await c.message.edit_text(text, reply_markup=kb_admin(c.from_user.id))

@dp.callback_query(F.data == "a_addadm")
async def a_addadm(c: CallbackQuery, state: FSMContext):
    if not await owner_guard(c):
        return
    await c.answer()
    await c.message.edit_text("New Admin User ID দিন:", reply_markup=kb_back())
    await state.set_state(S.addadm)

@dp.message(S.addadm)
async def save_adm(m: Message, state: FSMContext):
    if not is_own(m.from_user.id):
        return
    try:
        uid = int((m.text or "").strip())
        if uid <= 0:
            raise ValueError
    except ValueError:
        return await m.answer("সঠিক User ID দিন।")
    with transaction() as db:
        db.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (uid,))
        db.execute("UPDATE users SET admin=1 WHERE user_id=?", (uid,))
    await m.answer(f"✅ {uid} এখন Admin।", reply_markup=kb_admin(m.from_user.id))
    await state.clear()

@dp.callback_query(F.data == "a_ban")
async def a_ban(c: CallbackQuery, state: FSMContext):
    if not await admin_guard(c):
        return
    await c.answer()
    await c.message.edit_text("Ban / Unban করার User ID দিন:", reply_markup=kb_back())
    await state.set_state(S.ban)

@dp.message(S.ban)
async def do_ban(m: Message, state: FSMContext):
    if not is_adm(m.from_user.id):
        return
    try:
        uid = int((m.text or "").strip())
    except ValueError:
        return await m.answer("সঠিক User ID দিন।")
    if is_own(uid):
        return await m.answer("Owner-কে Ban করা যাবে না।")
    u = user(uid)
    new_status = 0 if u["banned"] else 1
    with cn() as db:
        db.execute("UPDATE users SET banned=? WHERE user_id=?", (new_status, uid))
    await m.answer(
        f"✅ {uid} → {'🚫 Banned' if new_status else '✅ Unbanned'}",
        reply_markup=kb_admin(m.from_user.id)
    )
    await state.clear()

@dp.callback_query(F.data == "a_bal")
async def a_bal(c: CallbackQuery, state: FSMContext):
    if not await admin_guard(c):
        return
    await c.answer()
    await c.message.edit_text("যে User-এর Balance পরিবর্তন করবেন তার ID দিন:", reply_markup=kb_back())
    await state.set_state(S.bal_uid)

@dp.message(S.bal_uid)
async def bal_uid(m: Message, state: FSMContext):
    if not is_adm(m.from_user.id):
        return
    try:
        uid = int((m.text or "").strip())
    except ValueError:
        return await m.answer("সঠিক User ID দিন।")
    user(uid)
    await state.update_data(uid=uid)
    await m.answer("পরিমাণ লিখুন (+ যোগ, - কাট):")
    await state.set_state(S.bal_amt)

@dp.message(S.bal_amt)
async def bal_amt(m: Message, state: FSMContext):
    if not is_adm(m.from_user.id):
        return
    try:
        amount = float((m.text or "").strip())
        if amount == 0:
            raise ValueError
    except ValueError:
        return await m.answer("শূন্য ছাড়া সঠিক সংখ্যা দিন।")
    uid = (await state.get_data())["uid"]
    with transaction() as db:
        row = db.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
        if amount < 0 and float(row["balance"]) < abs(amount):
            return await m.answer("❌ User-এর Balance এত নেই।")
        db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, uid))
        new_balance = db.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()["balance"]
    await m.answer(
        f"✅ User: {uid}\nChange: {amount:+.2f} TK\nNew Balance: {new_balance:.2f} TK",
        reply_markup=kb_admin(m.from_user.id)
    )
    try:
        await bot.send_message(uid, f"💰 আপনার Balance {amount:+.2f} TK পরিবর্তন হয়েছে।\nবর্তমান Balance: {new_balance:.2f} TK")
    except Exception:
        pass
    await state.clear()

@dp.callback_query(F.data == "a_bc")
async def a_bc(c: CallbackQuery, state: FSMContext):
    if not await admin_guard(c):
        return
    await c.answer()
    await c.message.edit_text("📢 Broadcast Message লিখুন:", reply_markup=kb_back())
    await state.set_state(S.bc)

@dp.message(S.bc)
async def do_bc(m: Message, state: FSMContext):
    if not is_adm(m.from_user.id):
        return
    with cn() as db:
        ids = [r["user_id"] for r in db.execute("SELECT user_id FROM users WHERE banned=0")]
    ok = fail = 0
    for uid in ids:
        try:
            await bot.send_message(uid, m.text or "")
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)
    await m.answer(
        f"✅ BʀᴏᴀᴅCᴀsᴛ সম্পন্ন\nসফল: {ok} | ব্যর্থ: {fail}",
        reply_markup=kb_admin(m.from_user.id)
    )
    await state.clear()

# ================= OWNER: DYNAMIC BUTTON EDITOR =================
EDIT_OPTIONS = [
    ("u_buy", "User: Buy Product"),
    ("u_stock", "User: Stock"),
    ("u_addbal", "User: Add Balance"),
    ("u_myinfo", "User: My Info"),
    ("u_support", "User: Support Team"),
    ("a_stock", "Admin: Stock Add"),
    ("a_rate", "Admin: Rate Update"),
    ("a_list", "Admin: Admin List"),
    ("a_ban", "Admin: Ban / Unban"),
    ("a_bal", "Admin: Balance +/-"),
    ("a_bc", "Admin: Broadcast"),
    ("a_addadm", "Owner: Add Admin"),
    ("a_edit", "Owner: Edit Buttons"),
]

@dp.callback_query(F.data == "a_edit")
async def a_edit(c: CallbackQuery, state: FSMContext):
    if not await owner_guard(c):
        return
    await c.answer()
    rows = [
        [IKB(text=title, callback_data=f"editkey:{key}")]
        for key, title in EDIT_OPTIONS
    ]
    rows.append([IKB(text="⬅️ Back", callback_data="adpanel")])
    await c.message.edit_text(
        "✏️ যে Button-এর Text / Emoji পরিবর্তন করতে চান সেটি নির্বাচন করুন:",
        reply_markup=IKM(inline_keyboard=rows)
    )

@dp.callback_query(F.data.startswith("editkey:"))
async def edit_key(c: CallbackQuery, state: FSMContext):
    if not await owner_guard(c):
        return
    key = c.data.split(":", 1)[1]
    if key not in dict(EDIT_OPTIONS):
        return await c.answer("Invalid button", show_alert=True)
    await c.answer()
    await state.update_data(edit_key=key)
    await c.message.edit_text(
        f"বর্তমান Text:\n{label(key)}\n\nনতুন Button Text + Emoji পাঠান:",
        reply_markup=kb_back()
    )
    await state.set_state(S.edit_text)

@dp.message(S.edit_text)
async def save_button_text(m: Message, state: FSMContext):
    if not is_own(m.from_user.id):
        return
    new_text = (m.text or "").strip()
    if not new_text or len(new_text) > 60:
        return await m.answer("Button Text ১-৬০ অক্ষরের মধ্যে দিন।")
    data = await state.get_data()
    key = data.get("edit_key")
    if key not in dict(EDIT_OPTIONS):
        await state.clear()
        return await m.answer("Edit session expired. আবার চেষ্টা করুন।")
    set_label(key, new_text)
    await m.answer(
        f"✅ Button Updated!\nনতুন Text: {new_text}\n\n"
        "পরিবর্তন Database-এ Save হয়েছে।",
        reply_markup=kb_admin(m.from_user.id)
    )
    await state.clear()

# ================= RUNNER =================
async def main():
    logging.basicConfig(level=logging.INFO)
    if BOT_TOKEN == "PASTE_NEW_BOT_TOKEN_HERE":
        raise RuntimeError("CONFIG-এ নতুন BOT_TOKEN বসান।")
    init()
    print("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")
    except Exception:
        logging.exception("Bot stopped because of an error.")
