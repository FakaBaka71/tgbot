import telebot, sqlite3, time, os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

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

# ================= KEYBOARDS =================
def main_menu_btn():
    # পার্মানেন্ট মেনু বাটন
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🏠 Main Menu"))
    return markup

def kb_main(uid):
    r = [[InlineKeyboardButton(text=f"🛒 {amon('Bᴜʏ Pʀᴏᴅᴜᴄᴛ')}", callback_data="buy")],
         [InlineKeyboardButton(text=f"📦 {amon('Sᴛᴏᴄᴋ')}", callback_data="stock")],
         [InlineKeyboardButton(text=f"💰 {amon('Aᴅᴅ Bᴀʟᴀɴᴄᴇ')}", callback_data="addbal")],
         [InlineKeyboardButton(text=f"👤 {amon('Aᴅᴍɪɴ Iɴғᴏ')}", callback_data="adinfo")],
         [InlineKeyboardButton(text=f"🤝 {amon('Bᴜsɪɴᴇss Pᴀʀᴛɴᴇʀ')}", callback_data="partner")]]
    if is_adm(uid): r.append([InlineKeyboardButton(text=f"⚙️ {amon('Aᴅᴍɪɴ Pᴀɴᴇʟ')}", callback_data="adpanel")])
    return InlineKeyboardMarkup(r)

def kb_back(): return InlineKeyboardMarkup([[InlineKeyboardButton(text="⬅️ Back", callback_data="menu")]])

def kb_admin(uid):
    r = [[InlineKeyboardButton(text="✅ Sᴛᴏᴄᴋ Aᴅᴅ", callback_data="a_stock")],
         [InlineKeyboardButton(text="💰 Rᴀᴛᴇ Uᴘᴅᴀᴛᴇ", callback_data="a_rate")],
         [InlineKeyboardButton(text="👥 Aᴅᴍɪɴ Lɪsᴛ", callback_data="a_list")],
         [InlineKeyboardButton(text="🚫 Bᴀɴ » Uɴʙᴀɴ", callback_data="a_ban")],
         [InlineKeyboardButton(text="💵 Bᴀʟᴀɴᴄᴇ +/-", callback_data="a_bal")],
         [InlineKeyboardButton(text="📢 Bʀᴏᴀᴅᴄᴀsᴛ", callback_data="a_bc")]]
    if is_own(uid):
        r.append([InlineKeyboardButton(text="⚙️ Aᴅᴅ Aᴅᴍɪɴ", callback_data="a_addadm")])
        r.append([InlineKeyboardButton(text="✏️ Eᴅɪᴛ Bᴜᴛᴛᴏɴs", callback_data="a_edit")])
    r.append([InlineKeyboardButton(text="♻️ Bᴀᴄᴋ Mᴇɴᴜ", callback_data="menu")])
    return InlineKeyboardMarkup(r)

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
    
    # এখানে reply_markup এ main_menu_btn() যোগ করা হয়েছে
    bot.edit_message_text(f"👋 {amon('Wᴇʟᴄᴏᴍᴇ')} {m.from_user.first_name}!\n\n🎯 {amon('Pʀᴇᴍɪᴜᴍ Vᴘɴ')} — নিচে থেকে বেছে নিন 👇", 
                          m.chat.id, msg.message_id, reply_markup=kb_main(m.from_user.id))
    
    # পার্মানেন্ট মেনু বাটনটি চালু করা হলো
    bot.send_message(m.chat.id, "মেনু বাটনটি চালু করা হলো 👇", reply_markup=main_menu_btn())

@bot.message_handler(func=lambda m: m.text == "🏠 Main Menu")
def menu_btn_pressed(m):
    states.pop(m.from_user.id, None)
    bot.send_message(m.chat.id, f"🏠 {amon('Mᴀɪɴ Mᴇᴍᴜ')}\n\nনিচে থেকে বেছে নিন 👇", reply_markup=kb_main(m.from_user.id))

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    uid = call.from_user.id
    data = call.data

    if data == "menu":
        states.pop(uid, None)
        bot.edit_message_text(f"🏠 {amon('Mᴀɪɴ Mᴇᴍᴜ')}\n\nনিচে থেকে বেছে নিন 👇", call.message.chat.id, call.message.message_id, reply_markup=kb_main(uid))

    elif data == "buy":
        if stock_left() == 0:
            bot.edit_message_text("❌ Sᴛᴏᴄᴋ Nᴏ Aᴠᴀɪʟᴀʙʟᴇ\n\nঅ্যাডমিনকে স্টক যোগ করতে বলুন।", call.message.chat.id, call.message.message_id, reply_markup=kb_back())
            for o in MAIN_OWNER_IDS:
                try: bot.send_message(o, f"⛔ Sᴛᴏᴄᴋ Sᴏʟᴅ Oᴜᴛ!\nশেষ চেষ্টা: {uid}")
                except: pass
            return
        states[uid] = "qty"
        bot.edit_message_text("🛒 আপনি কয়টি Vᴘɴ নিতে চান? সংখ্যা লিখুন (যেমন: 1,2,3,)", call.message.chat.id, call.message.message_id, reply_markup=kb_back())

    elif data == "stock":
        with cn() as x: sold = x.execute("SELECT COUNT(*) FROM stock WHERE sold=1").fetchone()[0]
        bot.edit_message_text(f"📦 {amon('Sᴛᴏᴄᴋ Dᴇᴛᴀɪʟs')}\n\n✅ Aᴠᴀɪʟᴀʙʟᴇ : {stock_left()}\n🛒 Sᴏʟᴅ Oᴜᴛ : {sold}", call.message.chat.id, call.message.message_id, reply_markup=kb_back())

    elif data == "addbal":
        bot.edit_message_text(f"💰 {amon('Aᴅᴅ Bᴀʟᴀɴᴄᴇ')}\n\nযোগাযোগ করুন:\n\nNᴀᴍᴇ : {amon('𝗗𝗔𝗥𝗞 𝗟𝗘𝗢')} 🅕︎🧛‍♂️\nUsᴇʀNᴀᴍᴇ : @BangIadeshi", call.message.chat.id, call.message.message_id, reply_markup=kb_back())

    elif data == "adinfo":
        bot.edit_message_text(f"👤 {amon('Aᴅᴍɪɴ Iɴғᴏ')}\n\nNᴀᴍᴇ : {amon('𝗗𝗔𝗥𝗞 𝗟𝗘𝗢')} 🅕︎🧛‍♂️\nUsᴇʀNᴀᴍᴇ : @BangIadeshi", call.message.chat.id, call.message.message_id, reply_markup=kb_back())

    elif data == "partner":
        bot.edit_message_text(f"🤝 {amon('Bᴜsɪɴᴇss Pᴀʀᴛɴᴇʀ')}\n\nযোগাযোগ : @BangIadeshi", call.message.chat.id, call.message.message_id, reply_markup=kb_back())

    elif data == "adpanel":
        if not is_adm(uid): return bot.answer_callback_query(call.id, "⛔️ Nᴏ ʏᴏᴜ Aᴅᴍɪɴ", show_alert=True)
        bot.edit_message_text(f"⚙️ {amon('Aᴅᴍɪɴ Pᴀɴᴇʟ')}", call.message.chat.id, call.message.message_id, reply_markup=kb_admin(uid))

    # Admin Actions
    elif data == "a_stock":
        if not is_adm(uid): return bot.answer_callback_query(call.id, "⛔️", show_alert=True)
        states[uid] = "stock"
        bot.edit_message_text("✅ Sᴛᴏᴄᴋ Aᴅᴅ\n\nফরম্যাট (প্রতি লাইনে একটি):\nName | Delivery | Gmail | Pass | Expired | Key | Rate", call.message.chat.id, call.message.message_id, reply_markup=kb_back())
    
    elif data == "a_rate":
        if not is_adm(uid): return bot.answer_callback_query(call.id, "⛔️", show_alert=True)
        states[uid] = "rate"
        bot.edit_message_text("💰 সব Aᴠᴀɪʟᴀʙʟᴇ Vᴘɴ-এর নতুন Rᴀᴛᴇ লিখুন (শুধু সংখ্যা) :", call.message.chat.id, call.message.message_id, reply_markup=kb_back())

    elif data == "a_list":
        if not is_adm(uid): return bot.answer_callback_query(call.id, "⛔️", show_alert=True)
        with cn() as x: rows = x.execute("SELECT user_id FROM users WHERE admin=1").fetchall()
        t = "👑 Oᴡɴᴇʀs :\n" + "\n".join(f"• {o}" for o in MAIN_OWNER_IDS)
        t += "\n\n👥 Aᴅᴍɪɴs :\n" + ("\n".join(f"• {r['user_id']}" for r in rows) or "—")
        bot.edit_message_text(t, call.message.chat.id, call.message.message_id, reply_markup=kb_admin(uid))

    elif data == "a_addadm":
        if not is_own(uid): return bot.answer_callback_query(call.id, "⛔️ Oᴡɴᴇʀ Oɴʟʏ", show_alert=True)
        states[uid] = "addadm"
        bot.edit_message_text("Nᴇᴡ Aᴅᴍɪɴs Usᴇʀ Iᴅ :", call.message.chat.id, call.message.message_id, reply_markup=kb_back())

    elif data == "a_ban":
        if not is_adm(uid): return bot.answer_callback_query(call.id, "⛔️", show_alert=True)
        states[uid] = "ban"
        bot.edit_message_text("Bᴀɴ » Uɴʙᴀɴ Usᴇʀ Iᴅ :", call.message.chat.id, call.message.message_id, reply_markup=kb_back())

    elif data == "a_bal":
        if not is_adm(uid): return bot.answer_callback_query(call.id, "⛔️", show_alert=True)
        states[uid] = "bal_uid"
        bot.edit_message_text("Eɴᴛᴇʀ Usᴇʀ Iᴅ :", call.message.chat.id, call.message.message_id, reply_markup=kb_back())
    
    elif data == "a_bc":
        if not is_adm(uid): return bot.answer_callback_query(call.id, "⛔️", show_alert=True)
        states[uid] = "bc"
        bot.edit_message_text("📢 ব্রডকাস্ট মেসেজ লিখুন:", call.message.chat.id, call.message.message_id, reply_markup=kb_back())

    elif data == "a_edit":
        bot.answer_callback_query(call.id, "বাটন এডিট ফিচারটি কোডে পরিবর্তন করতে হবে।", show_alert=True)

# ================= TEXT MESSAGES =================
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
                return bot.edit_message_text(f"❌ স্টক অপর্যাপ্ত। আছে: {stock_left()}", m.chat.id, msg.message_id, reply_markup=kb_back())
            
            total = sum(i["rate"] for i in items)
            u = user(uid)
            if u["balance"] < total:
                return bot.edit_message_text(f"❌ Bᴀʟᴀɴᴄᴇ Sᴏʟᴅ।\nপ্রয়োজন : {total} | আছে : {u['balance']}\n\nAᴅᴅ Bᴀʟᴀɴᴄᴇ এ যোগাযোগ করুন।", m.chat.id, msg.message_id, reply_markup=kb_back())

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

        bot.send_message(m.chat.id, "আরও কিনতে চান?", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(text="♻️ Nᴇᴡ Oʀᴅᴇʀ", callback_data="buy")],
            [InlineKeyboardButton(text="🏠 Mᴀɪɴ Mᴇɴᴜ", callback_data="menu")]]))

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
        bot.send_message(m.chat.id, f"✅ {n} টি VPN স্টকে যোগ হয়েছে।", reply_markup=kb_admin(uid))
        states.pop(uid, None)

    elif state == "rate":
        try: r = float(m.text)
        except: return bot.send_message(m.chat.id, "সঠিক সংখ্যা দিন")
        with cn() as c: c.execute("UPDATE stock SET rate=? WHERE sold=0", (r,))
        bot.send_message(m.chat.id, f"✅ Nᴇᴡ Rᴀᴛᴇ : {r}", reply_markup=kb_admin(uid))
        states.pop(uid, None)

    elif state == "addadm":
        try: target = int(m.text)
        except: return bot.send_message(m.chat.id, "সঠিক ID দিন")
        with cn() as c:
            c.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (target,))
            c.execute("UPDATE users SET admin=1 WHERE user_id=?", (target,))
        bot.send_message(m.chat.id, f"✅ {target} Jᴜsᴛ Nᴏᴡ Aᴅᴍɪɴ।", reply_markup=kb_admin(uid))
        states.pop(uid, None)

    elif state == "ban":
        try: target = int(m.text)
        except: return bot.send_message(m.chat.id, "সঠিক Usᴇʀ ɪᴅ দিন")
        u = user(target); new = 0 if u["banned"] else 1
        with cn() as c: c.execute("UPDATE users SET banned=? WHERE user_id=?", (new, target))
        bot.send_message(m.chat.id, f"✅ {target} → {'🚫 Bᴀɴ Usᴇʀ' if new else '✅ Uɴʙᴀɴ Usᴇʀ'}", reply_markup=kb_admin(uid))
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
        bot.send_message(m.chat.id, f"✅ {target} Yᴏᴜʀ Bᴀʟᴀɴᴄᴇ {amt:+}", reply_markup=kb_admin(uid))
        states.pop(uid, None)

    elif state == "bc":
        ok = fail = 0
        with cn() as x: ids = [r["user_id"] for r in x.execute("SELECT user_id FROM users")]
        for target in ids:
            try: bot.send_message(target, m.text); ok += 1
            except: fail += 1
            time.sleep(0.05)
        bot.send_message(m.chat.id, f"✅ BʀᴏᴀᴅCᴀsᴛ\nসফল : {ok} | ব্যর্থ: {fail}", reply_markup=kb_admin(uid))
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
