import asyncio, sqlite3, itertools, logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup as IKM,
                           InlineKeyboardButton as IKB, BufferedInputFile)

# ================= CONFIG =================
BOT_TOKEN      = "9062068619:AAE0T3sL7zz66MSZsbRZSOgGj9ylYP2niFQ" 
MAIN_OWNER_IDS = [8614383351]          
DB = "vpn.db" 

# ================= Aᴍᴏɴ FONT =================
_M = {**{chr(65+i): chr(0x1D400+i) for i in range(26)},
      **{chr(97+i): chr(0x1D41A+i) for i in range(26)},
      **{chr(48+i): chr(0x1D7CE+i) for i in range(10)}}
def amon(t): return "".join(_M.get(c, c) for c in t)

# ================= DB =================
def cn():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

def init():
    with cn() as c: c.executescript("""
    CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, username TEXT,
      balance REAL DEFAULT 0, banned INTEGER DEFAULT 0, admin INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS stock(id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT, dtime TEXT, gmail TEXT, pw TEXT, exp TEXT, key TEXT, rate REAL,
      sold INTEGER DEFAULT 0, buyer INTEGER);
    CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT,
      uid INTEGER, qty INTEGER, total REAL, ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP);""")

def user(uid):
    with cn() as c:
        u = c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
        if not u:
            c.execute("INSERT INTO users(user_id) VALUES(?)", (uid,))
            u = c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
        return u

def is_adm(uid): return uid in MAIN_OWNER_IDS or bool(user(uid)["admin"])
def is_own(uid): return uid in MAIN_OWNER_IDS
def stock_left():
    with cn() as c: return c.execute("SELECT COUNT(*) FROM stock WHERE sold=0").fetchone()[0]
def add_bal(uid, amt):
    with cn() as c: c.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amt, uid))

def sell(qty, uid):
    with cn() as c:
        rows = c.execute("SELECT * FROM stock WHERE sold=0 LIMIT ?", (qty,)).fetchall()
        if len(rows) < qty: return None
        c.executemany("UPDATE stock SET sold=1,buyer=? WHERE id=?",
                      [(uid, r["id"]) for r in rows])
        return rows

def unsell(ids):
    with cn() as c: c.executemany("UPDATE stock SET sold=0,buyer=NULL WHERE id=?",
                                  [(i,) for i in ids])

# ================= ANIMATION =================
SPIN = itertools.cycle(["◐", "◓", "◑", "◒"])
async def animate(msg, base, steps=3):
    for _ in range(steps):
        try: await msg.edit_text(f"{base}  {next(SPIN)}")
        except: pass
        await asyncio.sleep(0.35)
    try: await msg.edit_text(base)
    except: pass

# ================= KEYBOARDS =================
def kb_main(uid):
    r = [[IKB(text=f"🛒 {amon('Bᴜʏ Pʀᴏᴅᴜᴄᴛ')}", callback_data="buy")],
         [IKB(text=f"📦 {amon('Sᴛᴏᴄᴋ')}", callback_data="stock")],
         [IKB(text=f"💰 {amon('Aᴅᴅ Bᴀʟᴀɴᴄᴇ')}", callback_data="addbal")],
         [IKB(text=f"👤 {amon('Aᴅᴍɪɴ Iɴғᴏ')}", callback_data="adinfo")],
         [IKB(text=f"🤝 {amon('Bᴜsɪɴᴇss Pᴀʀᴛɴᴇʀ')}", callback_data="partner")]]
    if is_adm(uid): r.append([IKB(text=f"⚙️ {amon('Aᴅᴍɪɴ Pᴀɴᴇʟ')}", callback_data="adpanel")])
    return IKM(inline_keyboard=r)

def kb_back(): return IKM(inline_keyboard=[[IKB(text="⬅️ Back", callback_data="menu")]])

def kb_admin(uid):
    r = [[IKB(text="✅ Sᴛᴏᴄᴋ Aᴅᴅ", callback_data="a_stock")],
         [IKB(text="💰 Rᴀᴛᴇ Uᴘᴅᴀᴛᴇ", callback_data="a_rate")],
         [IKB(text="👥 Aᴅᴍɪɴ Lɪsᴛ", callback_data="a_list")],
         [IKB(text="🚫 Bᴀɴ » Uɴʙᴀɴ", callback_data="a_ban")],
         [IKB(text="💵 Bᴀʟᴀɴᴄᴇ +/-", callback_data="a_bal")],
         [IKB(text="📢 Bʀᴏᴀᴅᴄᴀsᴛ", callback_data="a_bc")]]
    if is_own(uid):
        r.append([IKB(text="⚙️ Aᴅᴅ Aᴅᴍɪɴ", callback_data="a_addadm")])
        r.append([IKB(text="✏️ Eᴅɪᴛ Bᴜᴛᴛᴏɴs", callback_data="a_edit")])
    r.append([IKB(text="♻️ Bᴀᴄᴋ Mᴇɴᴜ", callback_data="menu")])
    return IKM(inline_keyboard=r)

# ================= BOT =================
bot = Bot(token=BOT_TOKEN); dp = Dispatcher()
class S(StatesGroup):
    qty = State(); stock = State(); bal_uid = State(); bal_amt = State()
    ban = State(); addadm = State(); bc = State(); rate = State()

@dp.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    user(m.from_user.id)
    if user(m.from_user.id)["banned"]:
        return await m.answer("🚫 আপনি ব্যান হয়েছেন।")
    msg = await m.answer("✨")
    await animate(msg, f"👋 {amon('Wᴇʟᴄᴏᴍᴇ')} {m.from_user.first_name}!\n\n"
                       f"🎯 {amon('Pʀᴇᴍɪᴜᴍ Vᴘɴ')} — নিচে থেকে বেছে নিন 👇", steps=4)
    await msg.edit_reply_markup(reply_markup=kb_main(m.from_user.id))

@dp.callback_query(F.data == "menu")
async def menu(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.edit_text(f"🏠 {amon('Mᴀɪɴ Mᴇɴᴜ')}\n\nনিচে থেকে বেছে নিন 👇",
                              reply_markup=kb_main(c.from_user.id))

@dp.callback_query(F.data == "buy")
async def buy(c: CallbackQuery, state: FSMContext):
    await state.clear()
    if stock_left() == 0:
        await c.message.edit_text("❌ Sᴛᴏᴄᴋ Nᴏ Aᴠᴀɪʟᴀʙʟᴇ\n\nঅ্যাডমিনকে স্টক যোগ করতে বলুন।",
                                  reply_markup=kb_back())
        for o in MAIN_OWNER_IDS:
            try: await bot.send_message(o, f"⛔ Sᴛᴏᴄᴋ Sᴏʟᴅ Oᴜᴛ!\nশেষ চেষ্টা: {c.from_user.id}")
            except: pass
        return
    await c.message.edit_text("🛒 আপনি কয়টি Vᴘɴ নিতে চান? সংখ্যা লিখুন (যেমন: 1,2,3,)",
                              reply_markup=kb_back())
    await state.set_state(S.qty)

@dp.message(S.qty)
async def do_qty(m: Message, state: FSMContext):
    try:
        q = int(m.text.strip()); assert q > 0
    except: return await m.answer("⚠️ সঠিক সংখ্যা লিখুন (যেমন: 1,2,3)")
    msg = await m.answer("⏳")
    await animate(msg, "⏳ আপনার Oʀᴅᴇʀ রেডি করা হচ্ছে...", steps=3)

    items = sell(q, m.from_user.id)
    if not items:
        await msg.edit_text(f"❌ স্টক অপর্যাপ্ত। আছে: {stock_left()}", reply_markup=kb_back())
        return await state.clear()

    total = sum(i["rate"] for i in items)
    u = user(m.from_user.id)
    if u["balance"] < total:
        unsell([i["id"] for i in items])
        await msg.edit_text(f"❌ Bᴀʟᴀɴᴄᴇ Sᴏʟᴅ।\nপ্রয়োজন : {total} | আছে : {u['balance']}\n\n"
                            f"Aᴅᴅ Bᴀʟᴀɴᴄᴇ এ যোগাযোগ করুন।", reply_markup=kb_back())
        return await state.clear()

    add_bal(m.from_user.id, -total)
    with cn() as c: c.execute("INSERT INTO orders(uid,qty,total) VALUES(?,?,?)",
                              (m.from_user.id, q, total))

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
    txt = "\n\n".join(block(i) for i in items)
    f = BufferedInputFile(txt.encode(), filename=f"VPN_{q}pcs.txt")
    await m.answer_document(document=f,
        caption=f"✅ আপনার {q} টি Oʀᴅᴇʀ রেডি!\n💵 Tᴏᴛᴀʟ Aᴍᴏᴜɴᴛ : {total}\n\nTʜᴀɴᴋ Yᴏᴜ Cᴜsᴛᴏᴍᴇʀ ❤️‍🔥")

    await m.answer("আরও কিনতে চান?",
        reply_markup=IKM(inline_keyboard=[
            [IKB(text="♻️ Nᴇᴡ Oʀᴅᴇʀ", callback_data="buy")],
            [IKB(text="🏠 Mᴀɪɴ Mᴇɴᴜ", callback_data="menu")]]))

    if stock_left() == 0:
        for o in MAIN_OWNER_IDS:
            try: await bot.send_message(o, f"⚠️ Sᴛᴏᴄᴋ Oᴜᴛ!\nLᴀsᴛ Cᴜsᴛᴏᴍᴇʀ: {m.from_user.id} ({q} Pᴄs Oʀᴅᴇʀ)")
            except: pass
    await state.clear()

@dp.callback_query(F.data == "stock")
async def stock(c: CallbackQuery, state: FSMContext):
    await state.clear()
    with cn() as x: sold = x.execute("SELECT COUNT(*) FROM stock WHERE sold=1").fetchone()[0]
    await c.message.edit_text(
        f"📦 {amon('Sᴛᴏᴄᴋ Dᴇᴛᴀɪʟs')}\n\n"
        f"✅ Aᴠᴀɪʟᴀʙʟᴇ : {stock_left()}\n🛒 Sᴏʟᴅ Oᴜᴛ : {sold}",
        reply_markup=kb_back())

@dp.callback_query(F.data == "addbal")
async def addbal(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.edit_text(
        f"💰 {amon('Aᴅᴅ Bᴀʟᴀɴᴄᴇ')}\n\nযোগাযোগ করুন:\n\n"
        f"Nᴀᴍᴇ : {amon('𝗗𝗔𝗥𝗞 𝗟𝗘𝗢')} 🅕︎🧛‍♂️\nUsᴇʀNᴀᴍᴇ : @BangIadeshi",
        reply_markup=kb_back())

@dp.callback_query(F.data == "adinfo")
async def adinfo(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.edit_text(
        f"👤 {amon('Aᴅᴍɪɴ Iɴғᴏ')}\n\nNᴀᴍᴇ : {amon('𝗗𝗔𝗥𝗞 𝗟𝗘𝗢')} 🅕︎🧛‍♂️\n"
        f"UsᴇʀNᴀᴍᴇ : @BangIadeshi", reply_markup=kb_back())

@dp.callback_query(F.data == "partner")
async def partner(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.edit_text(
        f"🤝 {amon('Bᴜsɪɴᴇss Pᴀʀᴛɴᴇʀ')}\n\nযোগাযোগ : @BangIadeshi", reply_markup=kb_back())

@dp.callback_query(F.data == "adpanel")
async def adpanel(c: CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_adm(c.from_user.id):
        return await c.answer("⛔️ Nᴏ ʏᴏᴜ Aᴅᴍɪɴ", show_alert=True)
    await c.message.edit_text(f"⚙️ {amon('Aᴅᴍɪɴ Pᴀɴᴇʟ')}", reply_markup=kb_admin(c.from_user.id))

@dp.callback_query(F.data == "a_stock")
async def a_stock(c: CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_adm(c.from_user.id): return await c.answer("⛔️", True)
    await c.message.edit_text(
        "✅ Sᴛᴏᴄᴋ Aᴅᴅ\n\nফরম্যাট (প্রতি লাইনে একটি):\n"
        "Name | Delivery | Gmail | Pass | Expired | Key | Rate\n\n"
        "উদাহরণ:\nExpressVPN | 5 min | a@gmail.com | 1234 | 30 days | KEY-XX | 50",
        reply_markup=kb_back())
    await state.set_state(S.stock)

@dp.message(S.stock)
async def save_stock(m: Message, state: FSMContext):
    if not is_adm(m.from_user.id): return
    n = 0
    with cn() as c:
        for line in m.text.splitlines():
            p = [x.strip() for x in line.split("|")]
            if len(p) != 7: continue
            try:
                c.execute("INSERT INTO stock(name,dtime,gmail,pw,exp,key,rate) VALUES(?,?,?,?,?,?,?)",
                          (p[0], p[1], p[2], p[3], p[4], p[5], float(p[6]))); n += 1
            except:
                pass
    await m.answer(f"✅ {n} টি VPN স্টকে যোগ হয়েছে।", reply_markup=kb_admin(m.from_user.id))
    await state.clear()

@dp.callback_query(F.data == "a_rate")
async def a_rate(c: CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_adm(c.from_user.id): return await c.answer("⛔️", True)
    await c.message.edit_text("💰 সব Aᴠᴀɪʟᴀʙʟᴇ Vᴘɴ-এর নতুন Rᴀᴛᴇ লিখুন (শুধু সংখ্যা) :",
                              reply_markup=kb_back())
    await state.set_state(S.rate)

@dp.message(S.rate)
async def save_rate(m: Message, state: FSMContext):
    try: r = float(m.text)
    except: return await m.answer("সঠিক সংখ্যা দিন")
    with cn() as c: c.execute("UPDATE stock SET rate=? WHERE sold=0", (r,))
    await m.answer(f"✅ Nᴇᴡ Rᴀᴛᴇ : {r}", reply_markup=kb_admin(m.from_user.id))
    await state.clear()

@dp.callback_query(F.data == "a_list")
async def a_list(c: CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_adm(c.from_user.id): return await c.answer("⛔️", True)
    with cn() as x: rows = x.execute("SELECT user_id FROM users WHERE admin=1").fetchall()
    t = "👑 Oᴡɴᴇʀs :\n" + "\n".join(f"• {o}" for o in MAIN_OWNER_IDS)
    t += "\n\n👥 Aᴅᴍɪɴs :\n" + ("\n".join(f"• {r['user_id']}" for r in rows) or "—")
    await c.message.edit_text(t, reply_markup=kb_admin(c.from_user.id))

@dp.callback_query(F.data == "a_addadm")
async def a_addadm(c: CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_own(c.from_user.id): return await c.answer("⛔️ Oᴡɴᴇʀ Oɴʟʏ @BangIadeshi", True)
    await c.message.edit_text("Nᴇᴡ Aᴅᴍɪɴs Usᴇʀ Iᴅ :", reply_markup=kb_back())
    await state.set_state(S.addadm)

@dp.message(S.addadm)
async def save_adm(m: Message, state: FSMContext):
    if not is_own(m.from_user.id): return
    try: uid = int(m.text)
    except: return await m.answer("সঠিক ID দিন")
    with cn() as c:
        c.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (uid,))
        c.execute("UPDATE users SET admin=1 WHERE user_id=?", (uid,))
    await m.answer(f"✅ {uid} Jᴜsᴛ Nᴏᴡ Aᴅᴍɪɴ।", reply_markup=kb_admin(True))
    await state.clear()

@dp.callback_query(F.data == "a_ban")
async def a_ban(c: CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_adm(c.from_user.id): return await c.answer("⛔️", True)
    await c.message.edit_text("Bᴀɴ » Uɴʙᴀɴ Usᴇʀ Iᴅ :", reply_markup=kb_back())
    await state.set_state(S.ban)

@dp.message(S.ban)
async def do_ban(m: Message, state: FSMContext):
    try: uid = int(m.text)
    except: return await m.answer("সঠিক Usᴇʀ ɪᴅ দিন")
    u = user(uid); new = 0 if u["banned"] else 1
    with cn() as c: c.execute("UPDATE users SET banned=? WHERE user_id=?", (new, uid))
    await m.answer(f"✅ {uid} → {'🚫 Bᴀɴ Usᴇʀ' if new else '✅ Uɴʙᴀɴ Usᴇʀ'}",
                   reply_markup=kb_admin(m.from_user.id))
    await state.clear()

@dp.callback_query(F.data == "a_bal")
async def a_bal(c: CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_adm(c.from_user.id): return await c.answer("⛔️", True)
    await c.message.edit_text("Eɴᴛᴇʀ Usᴇʀ Iᴅ :", reply_markup=kb_back())
    await state.set_state(S.bal_uid)

@dp.message(S.bal_uid)
async def bal_uid(m: Message, state: FSMContext):
    try: await state.update_data(uid=int(m.text))
    except: return await m.answer("সঠিক Usᴇʀ ɪᴅ দিন")
    await m.answer("পরিমাণ লিখুন (+ যোগ, - কাট) :")
    await state.set_state(S.bal_amt)

@dp.message(S.bal_amt)
async def bal_amt(m: Message, state: FSMContext):
    try: amt = float(m.text)
    except: return await m.answer("সঠিক সংখ্যা দিন")
    uid = (await state.get_data())["uid"]
    add_bal(uid, amt)
    await m.answer(f"✅ {uid} Yᴏᴜʀ Bᴀʟᴀɴᴄᴇ {amt:+}", reply_markup=kb_admin(m.from_user.id))
    await state.clear()

@dp.callback_query(F.data == "a_bc")
async def a_bc(c: CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_adm(c.from_user.id): return await c.answer("⛔️", True)
    await c.message.edit_text("📢 ব্রডকাস্ট মেসেজ লিখুন:", reply_markup=kb_back())
    await state.set_state(S.bc)

@dp.message(S.bc)
async def do_bc(m: Message, state: FSMContext):
    ok = fail = 0
    with cn() as x: ids = [r["user_id"] for r in x.execute("SELECT user_id FROM users")]
    for uid in ids:
        try: await bot.send_message(uid, m.text); ok += 1
        except: fail += 1
        await asyncio.sleep(0.05)
    await m.answer(f"✅ BʀᴏᴀᴅCᴀsᴛ\nসফল : {ok} | ব্যর্থ: {fail}",
                   reply_markup=kb_admin(m.from_user.id))
    await state.clear()

@dp.callback_query(F.data == "a_edit")
async def a_edit(c: CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_own(c.from_user.id): return await c.answer("⛔️ Owner onlyOᴡɴᴇʀ Oɴʟʏ @BangIadeshi", True)
    await c.answer("বাটন এডিট ফিচারটি কোডে keyboards.py-তে থাকা টেক্সট পরিবর্তন করে করতে হবে।", show_alert=True)

# ================= RUNNER =================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        print("Starting Bot...")
        init()
        asyncio.run(dp.start_polling(bot))
    except Exception as e:
        print(f"ERROR: {e}")
