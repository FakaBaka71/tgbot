import telebot, sqlite3, time, os
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# ================= CONFIG =================
BOT_TOKEN = "9062068619:AAE0T3sL7zz66MSZsbRZSOgGj9ylYP2niFQ" 
MAIN_OWNER_IDS = [8614383351]          
DB = "vpn.db"

# ================= Aᴍᴏɴ FONT =================
_M = {**{chr(65+i): chr(0x1D400+i) for i in range(26)},
      **{chr(97+i): chr(0x1D41A+i) for i in range(26)},
      **{chr(48+i): chr(0x1D7CE+i) for i in range(10)}}
def amon(t): return "".join(_M.get(c, c) for c in t)

bot = telebot.TeleBot(BOT_TOKEN)

# ================= DB =================
def cn():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

def init():
    with cn() as c: c.executescript("""
    CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, banned INTEGER DEFAULT 0, admin INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS stock(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, dtime TEXT, gmail TEXT, pw TEXT, exp TEXT, key TEXT, rate REAL, sold INTEGER DEFAULT 0, buyer INTEGER);
    CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER, qty INTEGER, total REAL);""")

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

# ================= KEYBOARDS (REPLY MENU) =================
def menu_user(uid):
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.row(KeyboardButton(f"🛒 {amon('Bᴜʏ')}"), KeyboardButton(f"📦 {amon('Sᴛᴏᴄᴋ')}"))
    m.row(KeyboardButton(f"💰 {amon('Bᴀʟᴀɴᴄᴇ')}"), KeyboardButton(f"👤 {amon('Iɴғᴏ')}"))
    m.row(KeyboardButton(f"🤝 {amon('Pᴀʀᴛɴᴇʀ')}"))
    if is_adm(uid):
        m.row(KeyboardButton(f"⚙️ {amon('Aᴅᴍɪɴ')}"))
    return m

def menu_admin(uid):
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.row(KeyboardButton("✅ Aᴅᴅ Sᴛᴏᴄᴋ"), KeyboardButton("💰 Rᴀᴛᴇ"))
    m.row(KeyboardButton("👥 Aᴅᴍɪɴ Lɪsᴛ"), KeyboardButton("🚫 Bᴀɴ/Uɴʙᴀɴ"))
    m.row(KeyboardButton("💵 Bᴀʟᴀɴᴄᴇ"), KeyboardButton("📢 Bᴄᴀsᴛ"))
    if is_own(uid):
        m.row(KeyboardButton("⚙️ Aᴅᴅ Aᴅᴍɪɴ"), KeyboardButton("✏️ Eᴅɪᴛ Bᴛɴ"))
    m.row(KeyboardButton("🔙 Bᴀᴄᴋ Mᴇɴᴜ"))
    return m

# ================= HANDLERS =================
states = {}

@bot.message_handler(commands=['start'])
def start(m):
    user(m.from_user.id)
    if user(m.from_user.id)["banned"]: return bot.send_message(m.chat.id, "🚫 আপনি ব্যান হয়েছেন।")
    
    msg = bot.send_message(m.chat.id, "✨")
    for i in range(3):
        bot.edit_message_text(f"⏳ Lᴏᴀᴅɪɴɢ... {['◐','◓','◑','◒'][i%4]}", m.chat.id, msg.message_id)
        time.sleep(0.3)
    
    bot.edit_message_text(f"👋 {amon('Wᴇʟᴄᴏᴍᴇ')} {m.from_user.first_name}!\n\n🎯 {amon('Pʀᴇᴍɪᴜᴍ Vᴘɴ')} — নিচে থেকে বেছে নিন 👇", m.chat.id, msg.message_id)
    bot.send_message(m.chat.id, "🏠 মেইন মেনু 👇", reply_markup=menu_user(m.from_user.id))

# ----- Main Menu Buttons (Reply Keyboard) -----
@bot.message_handler(func=lambda m: m.text == f"🛒 {amon('Bᴜʏ')}")
def btn_buy(m):
    if stock_left() == 0:
        return bot.send_message(m.chat.id, "❌ Sᴛᴏᴄᴋ Nᴏ Aᴠᴀɪʟᴀʙʟᴇ\n\nঅ্যাডমিনকে স্টক যোগ করতে বলুন।")
    states[m.from_user.id] = "qty"
    bot.send_message(m.chat.id, "🛒 আপনি কয়টি Vᴘɴ নিতে চান? সংখ্যা লিখুন (যেমন: 1,2,3,)")

@bot.message_handler(func=lambda m: m.text == f"📦 {amon('Sᴛᴏᴄᴋ')}")
def btn_stock(m):
    with cn() as x: sold = x.execute("SELECT COUNT(*) FROM stock WHERE sold=1").fetchone()[0]
    bot.send_message(m.chat.id, f"📦 {amon('Sᴛᴏᴄᴋ Dᴇᴛᴀɪʟs')}\n\n✅ Aᴠᴀɪʟᴀʙʟᴇ : {stock_left()}\n🛒 Sᴏʟᴅ Oᴜᴛ : {sold}")

@bot.message_handler(func=lambda m: m.text == f"💰 {amon('Bᴀʟ')}")
def btn_bal(m):
    bot.send_message(m.chat.id, f"💰 {amon('Aᴅᴅ Bᴀʟᴀɴᴄᴇ')}\n\nযোগাযোগ করুন:\n\nNᴀᴍᴇ : {amon('𝗗𝗔𝗥𝗞 𝗟𝗘𝗢')} 🅕︎🧛‍♂️\nUsᴇʀNᴀᴍᴇ : @BangIadeshi")

@bot.message_handler(func=lambda m: m.text == f"👤 {amon('Iɴғᴏ')}")
def btn_info(m):
    bot.send_message(m.chat.id, f"👤 {amon('Aᴅᴍɪɴ Iɴғᴏ')}\n\nNᴀᴍᴇ : {amon('𝗗𝗔𝗥𝗞 𝗟𝗘𝗢')} 🅕︎🧛‍♂️\nUsᴇʀNᴀᴍᴇ : @BangIadeshi")

@bot.message_handler(func=lambda m: m.text == f"🤝 {amon('Pᴀʀᴛɴᴇʀ')}")
def btn_partner(m):
    bot.send_message(m.chat.id, f"🤝 {amon('Bᴜsɪɴᴇss Pᴀʀᴛɴᴇʀ')}\n\nযোগাযোগ : @BangIadeshi")

# ----- Admin Menu Buttons -----
@bot.message_handler(func=lambda m: m.text == f"⚙️ {amon('Aᴅᴍɪɴ')}")
def btn_admin_panel(m):
    if not is_adm(m.from_user.id): return bot.send_message(m.chat.id, "⛔️ Nᴏ ʏᴏᴜ Aᴅᴍɪɴ")
    bot.send_message(m.chat.id, f"⚙️ {amon('Aᴅᴍɪɴ Pᴀɴᴇʟ')} 👇", reply_markup=menu_admin(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "✅ Aᴅᴅ Sᴛᴏᴄᴋ")
def btn_a_stock(m):
    if not is_adm(m.from_user.id): return
    states[m.from_user.id] = "stock"
    bot.send_message(m.chat.id, "✅ Sᴛᴏᴄᴋ Aᴅᴅ\n\nফরম্যাট (প্রতি লাইনে একটি):\nName | Delivery | Gmail | Pass | Expired | Key | Rate")

@bot.message_handler(func=lambda m: m.text == "💰 Rᴀᴛᴇ")
def btn_a_rate(m):
    if not is_adm(m.from_user.id): return
    states[m.from_user.id] = "rate"
    bot.send_message(m.chat.id, "💰 সব Aᴠᴀɪʟᴀʙʟᴇ Vᴘɴ-এর নতুন Rᴀᴛᴇ লিখুন (শুধু সংখ্যা) :")

@bot.message_handler(func=lambda m: m.text == "👥 Aᴅᴍɪɴ Lɪsᴛ")
def btn_a_list(m):
    if not is_adm(m.from_user.id): return
    with cn() as x: rows = x.execute("SELECT user_id FROM users WHERE admin=1").fetchall()
    t = "👑 Oᴡɴᴇʀs :\n" + "\n".join(f"• {o}" for o in MAIN_OWNER_IDS)
    t += "\n\n👥 Aᴅᴍɪɴs :\n" + ("\n".join(f"• {r['user_id']}" for r in rows) or "—")
    bot.send_message(m.chat.id, t)

@bot.message_handler(func=lambda m: m.text == "🚫 Bᴀɴ/Uɴʙᴀɴ")
def btn_a_ban(m):
    if not is_adm(m.from_user.id): return
    states[m.from_user.id] = "ban"
    bot.send_message(m.chat.id, "Bᴀɴ » Uɴʙᴀɴ Usᴇʀ Iᴅ :")

@bot.message_handler(func=lambda m: m.text == "💵 Bᴀʟᴀɴᴄᴇ")
def btn_a_bal(m):
    if not is_adm(m.from_user.id): return
    states[m.from_user.id] = "bal_uid"
    bot.send_message(m.chat.id, "Eɴᴛᴇʀ Usᴇʀ Iᴅ :")

@bot.message_handler(func=lambda m: m.text == "📢 Bᴄᴀsᴛ")
def btn_a_bc(m):
    if not is_adm(m.from_user.id): return
    states[m.from_user.id] = "bc"
    bot.send_message(m.chat.id, "📢 ব্রডকাস্ট মেসেজ লিখুন:")

@bot.message_handler(func=lambda m: m.text == "⚙️ Aᴅᴅ Aᴅᴍɪɴ")
def btn_a_addadm(m):
    if not is_own(m.from_user.id): return
    states[m.from_user.id] = "addadm"
    bot.send_message(m.chat.id, "Nᴇᴡ Aᴅᴍɪɴs Usᴇʀ Iᴅ :")

@bot.message_handler(func=lambda m: m.text == "✏️ Eᴅɪᴛ Bᴛɴ")
def btn_a_edit(m):
    bot.send_message(m.chat.id, "বাটন এডিট ফিচারটি কোডে পরিবর্তন করতে হবে।")

@bot.message_handler(func=lambda m: m.text == "🔙 Bᴀᴄᴋ Mᴇɴᴜ")
def btn_back(m):
    states.pop(m.from_user.id, None)
    bot.send_message(m.chat.id, "🏠 মেইন মেনু 👇", reply_markup=menu_user(m.from_user.id))

# ================= TEXT MESSAGES (STATES) =================
@bot.message_handler(func=lambda m: True)
def handle_text(m):
    uid = m.from_user.id
    state = states.get(uid)
    if not state: return

    if state == "qty":
        try:
            q = int(m.text.strip())
            if q <= 0: raise ValueError
        except:
            return bot.send_message(m.chat.id, "⚠️ সঠিক সংখ্যা লিখুন (যেমন: 1,2,3)")
        
        msg = bot.send_message(m.chat.id, "⏳ আপনার Oʀᴅᴇʀ রেডি করা হচ্ছে...")
        for i in range(3):
            bot.edit_message_text(f"⏳ আপনার Oʀᴅᴇʀ রেডি করা হচ্ছে... {['◐','◓','◑','◒'][i%4]}", m.chat.id, msg.message_id)
            time.sleep(0.3)

        with cn() as c:
            items = c.execute("SELECT * FROM stock WHERE sold=0 LIMIT ?", (q,)).fetchall()
            if len(items) < q:
                return bot.send_message(m.chat.id, f"❌ স্টক অপর্যাপ্ত। আছে: {stock_left()}")
            
            total = sum(i["rate"] for i in items)
            u = user(uid)
            if u["balance"] < total:
                return bot.send_message(m.chat.id, f"❌ Bᴀʟᴀɴᴄᴇ Sᴏʟᴅ।\nপ্রয়োজন : {total} | আছে : {u['balance']}\n\nAᴅᴅ Bᴀʟᴀɴᴄᴇ এ যোগাযোগ করুন।")

            c.executemany("UPDATE stock SET sold=1,buyer=? WHERE id=?", [(uid, i["id"]) for i in items])
            c.execute("INSERT INTO orders(uid,qty,total) VALUES(?,?,?)", (uid, q, total))
            c.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (total, uid))

        def block(it):
            return f"===========================\n{it['name']}  ( Dᴇʟɪᴠᴇʀʏ Tɪᴍᴇ : {it['dtime']} ) ✅\n===========================\nGᴍᴀɪʟ : {it['gmail']}\nPᴀss : {it['pw']}\nExᴘʀɪʀᴇᴅ Tɪᴍᴇ : {it['exp']}\n\nGᴍᴀɪʟ এবং Pᴀss কাজ না করলে\nKᴇʏ ব্যবহার করুন...✅\n\nAᴄᴛɪᴠᴇ Kᴇʏ : {it['key']}\n==============\nUᴘᴅᴀᴛᴇ Rᴀᴛᴇ : {it['rate']}\n==============\nTʜᴀɴᴋs Fᴏʀ Sᴜᴘᴘᴏʀᴛ ❤️‍🔥"
        
        txt = "\n\n".join(block(i) for i in items)
        with open(f"VPN_{q}pcs.txt", "w", encoding="utf-8") as f:
            f.write(txt)
            
        with open(f"VPN_{q}pcs.txt", "rb") as f:
            bot.send_document(m.chat.id, f, caption=f"✅ আপনার {q} টি Oʀᴅᴇʀ রেডি!\n💵 Tᴏᴛᴀʟ Aᴍᴏᴜɴᴛ : {total}\n\nTʜᴀɴᴋ Yᴏᴜ Cᴜsᴛᴏᴍᴇʀ ❤️‍🔥")
        os.remove(f"VPN_{q}pcs.txt")

        if stock_left() == 0:
            for o in MAIN_OWNER_IDS:
                try: bot.send_message(o, f"⚠️ Sᴛᴏᴄᴋ Oᴜᴛ!\nLᴀsᴛ Cᴜsᴛᴏᴍᴇʀ: {uid} ({q} Pᴄs Oʀᴅᴇʀ)")
                except: pass
        states.pop(uid, None)

    elif state == "stock":
        n = 0
        with cn() as c:
            for line in m.text.splitlines():
                p = [x.strip() for x in line.split("|")]
                if len(p) != 7: continue
                c.execute("INSERT INTO stock(name,dtime,gmail,pw,exp,key,rate) VALUES(?,?,?,?,?,?,?)", (p[0], p[1], p[2], p[3], p[4], p[5], float(p[6]))); n += 1
        bot.send_message(m.chat.id, f"✅ {n} টি VPN স্টকে যোগ হয়েছে।")
        states.pop(uid, None)

    elif state == "rate":
        try: r = float(m.text)
        except: return bot.send_message(m.chat.id, "সঠিক সংখ্যা দিন")
        with cn() as c: c.execute("UPDATE stock SET rate=? WHERE sold=0", (r,))
        bot.send_message(m.chat.id, f"✅ Nᴇᴡ Rᴀᴛᴇ : {r}")
        states.pop(uid, None)

    elif state == "addadm":
        try: target = int(m.text)
        except: return bot.send_message(m.chat.id, "সঠিক ID দিন")
        with cn() as c:
            c.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (target,))
            c.execute("UPDATE users SET admin=1 WHERE user_id=?", (target,))
        bot.send_message(m.chat.id, f"✅ {target} Jᴜsᴛ Nᴏᴡ Aᴅᴍɪɴ।")
        states.pop(uid, None)

    elif state == "ban":
        try: target = int(m.text)
        except: return bot.send_message(m.chat.id, "সঠিক Usᴇʀ ɪᴅ দিন")
        u = user(target); new = 0 if u["banned"] else 1
        with cn() as c: c.execute("UPDATE users SET banned=? WHERE user_id=?", (new, target))
        bot.send_message(m.chat.id, f"✅ {target} → {'🚫 Bᴀɴ Usᴇʀ' if new else '✅ Uɴʙᴀɴ Usᴇʀ'}")
        states.pop(uid, None)

    elif state == "bal_uid":
        try: 
            states[uid] = ("bal_amt", int(m.text))
            bot.send_message(m.chat.id, "পরিমাণ লিখুন (+ যোগ, - কাট) :")
        except: bot.send_message(m.chat.id, "সঠিক Usᴇʀ ɪᴅ দিন")

    elif isinstance(state, tuple) and state[0] == "bal_amt":
        try: amt = float(m.text)
        except: return bot.send_message(m.chat.id, "সঠিক সংখ্যা দিন")
        target = state[1]
        add_bal(target, amt)
        bot.send_message(m.chat.id, f"✅ {target} Yᴏᴜʀ Bᴀʟᴀɴᴄᴇ {amt:+}")
        states.pop(uid, None)

    elif state == "bc":
        ok = fail = 0
        with cn() as x: ids = [r["user_id"] for r in x.execute("SELECT user_id FROM users")]
        for target in ids:
            try: bot.send_message(target, m.text); ok += 1
            except: fail += 1
            time.sleep(0.05)
        bot.send_message(m.chat.id, f"✅ BʀᴏᴀᴅCᴀsᴛ\nসফল : {ok} | ব্যর্থ: {fail}")
        states.pop(uid, None)

# ================= START BOT =================
if __name__ == "__main__":
    init()
    print("Bot is running...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)
