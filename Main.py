import telebot
import sqlite3
import time
import os
from io import BytesIO
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# ================= CONFIG =================
BOT_TOKEN = "9062068619:AAE0T3sL7zz66MSZsbRZSOgGj9ylYP2niFQ"
MAIN_OWNER_IDS = [8614383351]
DB = "vpn.db"

# ================= Aᴍᴏɴ FONT =================
_M = {
    **{chr(65+i): chr(0x1D400+i) for i in range(26)},
    **{chr(97+i): chr(0x1D41A+i) for i in range(26)},
    **{chr(48+i): chr(0x1D7CE+i) for i in range(10)}
}

def amon(t):
    return "".join(_M.get(c, c) for c in t)

bot = telebot.TeleBot(BOT_TOKEN)
states = {}

# ================= DATABASE =================
def cn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout=30000")
    return c

def init():
    with cn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0,
            banned INTEGER DEFAULT 0,
            admin INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS stock(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            dtime TEXT,
            gmail TEXT,
            pw TEXT,
            exp TEXT,
            key TEXT,
            rate REAL,
            sold INTEGER DEFAULT 0,
            buyer INTEGER
        );

        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid INTEGER,
            qty INTEGER,
            total REAL
        );
        """)

        # পুরোনো database ঠিক রেখেই নতুন profile columns যোগ হবে
        user_columns = {
            row["name"] for row in c.execute("PRAGMA table_info(users)").fetchall()
        }
        for column, definition in (
            ("username", "TEXT"),
            ("first_name", "TEXT"),
            ("last_name", "TEXT")
        ):
            if column not in user_columns:
                c.execute(f"ALTER TABLE users ADD COLUMN {column} {definition}")

def user(uid, tg_user=None):
    with cn() as c:
        c.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (uid,))
        if tg_user:
            c.execute("""
                UPDATE users
                SET username=?, first_name=?, last_name=?
                WHERE user_id=?
            """, (
                tg_user.username,
                tg_user.first_name,
                tg_user.last_name,
                uid
            ))
        return c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()

def is_adm(uid):
    return uid in MAIN_OWNER_IDS or bool(user(uid)["admin"])

def is_own(uid):
    return uid in MAIN_OWNER_IDS

def stock_left():
    with cn() as c:
        return c.execute("SELECT COUNT(*) FROM stock WHERE sold=0").fetchone()[0]

def sold_count():
    with cn() as c:
        return c.execute("SELECT COUNT(*) FROM stock WHERE sold=1").fetchone()[0]

def add_bal(uid, amt):
    with cn() as c:
        c.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (uid,))
        c.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amt, uid))

def admin_contacts():
    """Owner এবং Admin-দের বর্তমান username দেখায়."""
    ids = list(dict.fromkeys(MAIN_OWNER_IDS))
    with cn() as c:
        rows = c.execute(
            "SELECT user_id, username, first_name FROM users WHERE admin=1"
        ).fetchall()

    contacts = []
    seen = set()

    for uid in ids + [r["user_id"] for r in rows]:
        if uid in seen:
            continue
        seen.add(uid)

        row = next((r for r in rows if r["user_id"] == uid), None)
        username = row["username"] if row else None
        first_name = row["first_name"] if row else None

        if not username:
            try:
                chat = bot.get_chat(uid)
                username = chat.username
                first_name = first_name or chat.first_name
                with cn() as c:
                    c.execute("""
                        INSERT OR IGNORE INTO users(user_id) VALUES(?)
                    """, (uid,))
                    c.execute("""
                        UPDATE users SET username=?, first_name=?
                        WHERE user_id=?
                    """, (username, first_name, uid))
            except Exception:
                pass

        if username:
            contacts.append(f"• @{username}")
        else:
            contacts.append(f"• {first_name or 'Admin'} (ID: {uid})")

    return "\n".join(contacts) if contacts else "এখনো কোনো Admin username পাওয়া যায়নি।"

# ================= KEYBOARDS (REPLY MENU) =================
def menu_user(uid):
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.row(
        KeyboardButton(f"🛒 {amon('Bᴜʏ')}"),
        KeyboardButton(f"📦 {amon('Sᴛᴏᴄᴋ')}")
    )
    m.row(
        KeyboardButton(f"💰 {amon('Bᴀʟᴀɴᴄᴇ')}"),
        KeyboardButton(f"👤 {amon('Aᴅᴍɪɴ Iɴғᴏ')}")
    )
    m.row(KeyboardButton(f"🤝 {amon('Pᴀʀᴛɴᴇʀ')}"))
    if is_adm(uid):
        m.row(KeyboardButton(f"⚙️ {amon('Aᴅᴍɪɴ')}"))
    return m

def menu_admin(uid):
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.row(KeyboardButton("✅ Aᴅᴅ Sᴛᴏᴄᴋ"), KeyboardButton("💰 Rᴀᴛᴇ"))
    m.row(KeyboardButton("👥 Aᴅᴍɪɴ Lɪsᴛ"), KeyboardButton("🚫 Bᴀɴ/Uɴʙᴀɴ"))
    m.row(KeyboardButton("💵 Bᴀʟ +/-"), KeyboardButton("📢 Bᴄᴀsᴛ"))
    if is_own(uid):
        m.row(KeyboardButton("⚙️ Aᴅᴅ Aᴅᴍɪɴ"), KeyboardButton("✏️ Eᴅɪᴛ Bᴛɴ"))
    m.row(KeyboardButton("🔙 Bᴀᴄᴋ Mᴇɴᴜ"))
    return m

# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):
    u = user(m.from_user.id, m.from_user)
    if u["banned"]:
        return bot.send_message(m.chat.id, "🚫 আপনি ব্যান হয়েছেন।")

    msg = bot.send_message(m.chat.id, "✨")
    for i in range(3):
        try:
            bot.edit_message_text(
                f"⏳ Lᴏᴀᴅɪɴɢ... {['◐','◓','◑','◒'][i%4]}",
                m.chat.id, msg.message_id
            )
            time.sleep(0.3)
        except Exception:
            pass

    bot.edit_message_text(
        f"👋 {amon('Wᴇʟᴄᴏᴍᴇ')} {m.from_user.first_name}!\n\n"
        f"🎯 {amon('Pʀᴇᴍɪᴜᴍ Vᴘɴ')} — নিচে থেকে বেছে নিন 👇",
        m.chat.id, msg.message_id
    )
    bot.send_message(
        m.chat.id, "🏠 মেইন মেনু 👇",
        reply_markup=menu_user(m.from_user.id)
    )

# ================= MAIN MENU =================
@bot.message_handler(func=lambda m: m.text == f"🛒 {amon('Bᴜʏ')}")
def btn_buy(m):
    user(m.from_user.id, m.from_user)

    # প্রতিবার Buy চাপলে database থেকে live rate ও stock count নেয়
    with cn() as c:
        products = c.execute("""
            SELECT name, rate, COUNT(*) AS qty
            FROM stock
            WHERE sold=0
            GROUP BY name, rate
            ORDER BY name, rate
        """).fetchall()

    if not products:
        return bot.send_message(
            m.chat.id,
            f"❌ {amon('Sᴛᴏᴄᴋ Nᴏ Aᴠᴀɪʟᴀʙʟᴇ')}\n\n"
            "📦 Available Stock : 0\n"
            "🛒 Sold Out : " + str(sold_count()) +
            "\n\nঅ্যাডমিনকে স্টক যোগ করতে বলুন।"
        )

    lines = [
        f"🛍️ {amon('Pʀᴏᴅᴜᴄᴛ Rᴀᴛᴇ & Sᴛᴏᴄᴋ')}",
        ""
    ]
    for p in products:
        lines.append(
            f"📌 {p['name']}\n"
            f"💵 Rate : {p['rate']:g}\n"
            f"📦 Available : {p['qty']}"
        )

    lines += [
        "",
        f"✅ Total Available : {stock_left()}",
        f"🛒 Total Sold Out : {sold_count()}",
        "",
        "কয়টি Product নিতে চান? সংখ্যা লিখুন (যেমন: 1, 2, 3)"
    ]

    states[m.from_user.id] = "qty"
    bot.send_message(m.chat.id, "\n".join(lines))

@bot.message_handler(func=lambda m: m.text == f"📦 {amon('Sᴛᴏᴄᴋ')}")
def btn_stock(m):
    user(m.from_user.id, m.from_user)
    bot.send_message(
        m.chat.id,
        f"📦 {amon('Sᴛᴏᴄᴋ Dᴇᴛᴀɪʟs')}\n\n"
        f"✅ Aᴠᴀɪʟᴀʙʟᴇ : {stock_left()}\n"
        f"🛒 Sᴏʟᴅ Oᴜᴛ : {sold_count()}"
    )

@bot.message_handler(func=lambda m: m.text == f"💰 {amon('Bᴀʟ')}")
def btn_bal(m):
    u = user(m.from_user.id, m.from_user)
    with cn() as c:
        order_data = c.execute("""
            SELECT COUNT(*) AS total_orders, COALESCE(SUM(total), 0) AS spent
            FROM orders WHERE uid=?
        """, (m.from_user.id,)).fetchone()

    username = f"@{m.from_user.username}" if m.from_user.username else "নেই"
    full_name = " ".join(
        x for x in [m.from_user.first_name, m.from_user.last_name] if x
    ) or "Unknown"

    text = (
        f"💰 {amon('Yᴏᴜʀ Bᴀʟᴀɴᴄᴇ & Dᴇᴛᴀɪʟs')}\n\n"
        f"👤 Name : {full_name}\n"
        f"🆔 User ID : {m.from_user.id}\n"
        f"🔗 Username : {username}\n"
        f"💵 Balance : {u['balance']:g}\n"
        f"🛒 Total Orders : {order_data['total_orders']}\n"
        f"💸 Total Spent : {order_data['spent']:g}\n\n"
        f"➕ {amon('Bᴀʟᴀɴᴄᴇ Aᴅᴅ')}\n"
        "Balance কিনতে নিচের Admin-দের যেকোনো একজনকে নক দিন:\n\n"
        f"{admin_contacts()}"
    )
    bot.send_message(m.chat.id, text)

@bot.message_handler(func=lambda m: m.text == f"👤 {amon('Iɴғᴏ')}")
def btn_info(m):
    user(m.from_user.id, m.from_user)
    bot.send_message(
        m.chat.id,
        f"👤 {amon('Aᴅᴍɪɴ Iɴғᴏ')}\n\n"
        f"Nᴀᴍᴇ : {amon('𝗗𝗔𝗥𝗞 𝗟𝗘𝗢')} 🅕︎🧛‍♂️\n"
        f"UsᴇʀNᴀᴍᴇ : @BangIadeshi"
    )

@bot.message_handler(func=lambda m: m.text == f"🤝 {amon('Pᴀʀᴛɴᴇʀ')}")
def btn_partner(m):
    user(m.from_user.id, m.from_user)
    bot.send_message(
        m.chat.id,
        f"🤝 {amon('Bᴜsɪɴᴇss Pᴀʀᴛɴᴇʀ')}\n\nযোগাযোগ : @BangIadeshi"
    )

# ================= ADMIN MENU =================
@bot.message_handler(func=lambda m: m.text == f"⚙️ {amon('Aᴅᴍɪɴ')}")
def btn_admin_panel(m):
    user(m.from_user.id, m.from_user)
    if not is_adm(m.from_user.id):
        return bot.send_message(m.chat.id, "⛔️ Nᴏ ʏᴏᴜ Aᴅᴍɪɴ")
    bot.send_message(
        m.chat.id, f"⚙️ {amon('Aᴅᴍɪɴ Pᴀɴᴇʟ')} 👇",
        reply_markup=menu_admin(m.from_user.id)
    )

@bot.message_handler(func=lambda m: m.text == "✅ Aᴅᴅ Sᴛᴏᴄᴋ")
def btn_a_stock(m):
    user(m.from_user.id, m.from_user)
    if not is_adm(m.from_user.id):
        return
    states[m.from_user.id] = "stock"
    bot.send_message(
        m.chat.id,
        "✅ Sᴛᴏᴄᴋ Aᴅᴅ\n\nফরম্যাট (প্রতি লাইনে একটি):\n"
        "Name | Delivery | Gmail | Pass | Expired | Key | Rate"
    )

@bot.message_handler(func=lambda m: m.text == "💰 Rᴀᴛᴇ")
def btn_a_rate(m):
    user(m.from_user.id, m.from_user)
    if not is_adm(m.from_user.id):
        return
    states[m.from_user.id] = "rate"
    bot.send_message(
        m.chat.id,
        "💰 সব Aᴠᴀɪʟᴀʙʟᴇ Vᴘɴ-এর নতুন Rᴀᴛᴇ লিখুন (শুধু সংখ্যা) :"
    )

@bot.message_handler(func=lambda m: m.text == "👥 Aᴅᴍɪɴ Lɪsᴛ")
def btn_a_list(m):
    user(m.from_user.id, m.from_user)
    if not is_adm(m.from_user.id):
        return

    with cn() as c:
        rows = c.execute("""
            SELECT user_id, username, first_name
            FROM users WHERE admin=1
        """).fetchall()

    lines = ["👑 Oᴡɴᴇʀs :"]
    for oid in MAIN_OWNER_IDS:
        try:
            chat = bot.get_chat(oid)
            lines.append(
                f"• @{chat.username}" if chat.username else f"• ID: {oid}"
            )
        except Exception:
            lines.append(f"• ID: {oid}")

    lines.append("\n👥 Aᴅᴍɪɴs :")
    if rows:
        for r in rows:
            label = f"@{r['username']}" if r["username"] else f"ID: {r['user_id']}"
            lines.append(f"• {label}")
    else:
        lines.append("—")

    bot.send_message(m.chat.id, "\n".join(lines))

@bot.message_handler(func=lambda m: m.text == "🚫 Bᴀɴ/Uɴʙᴀɴ")
def btn_a_ban(m):
    user(m.from_user.id, m.from_user)
    if not is_adm(m.from_user.id):
        return
    states[m.from_user.id] = "ban"
    bot.send_message(m.chat.id, "Bᴀɴ » Uɴʙᴀɴ Usᴇʀ Iᴅ :")

@bot.message_handler(func=lambda m: m.text == "💵 Bᴀʟ +/-")
def btn_a_bal(m):
    user(m.from_user.id, m.from_user)
    if not is_adm(m.from_user.id):
        return
    states[m.from_user.id] = "bal_uid"
    bot.send_message(m.chat.id, "Eɴᴛᴇʀ Usᴇʀ Iᴅ :")

@bot.message_handler(func=lambda m: m.text == "📢 Bᴄᴀsᴛ")
def btn_a_bc(m):
    user(m.from_user.id, m.from_user)
    if not is_adm(m.from_user.id):
        return
    states[m.from_user.id] = "bc"
    bot.send_message(m.chat.id, "📢 ব্রডকাস্ট মেসেজ লিখুন:")

@bot.message_handler(func=lambda m: m.text == "⚙️ Aᴅᴅ Aᴅᴍɪɴ")
def btn_a_addadm(m):
    user(m.from_user.id, m.from_user)
    if not is_own(m.from_user.id):
        return
    states[m.from_user.id] = "addadm"
    bot.send_message(m.chat.id, "Nᴇᴡ Aᴅᴍɪɴs Usᴇʀ Iᴅ :")

@bot.message_handler(func=lambda m: m.text == "✏️ Eᴅɪᴛ Bᴛɴ")
def btn_a_edit(m):
    user(m.from_user.id, m.from_user)
    if not is_own(m.from_user.id):
        return
    bot.send_message(m.chat.id, "বাটন এডিট ফিচারটি কোডে পরিবর্তন করতে হবে।")

@bot.message_handler(func=lambda m: m.text == "🔙 Bᴀᴄᴋ Mᴇɴᴜ")
def btn_back(m):
    user(m.from_user.id, m.from_user)
    states.pop(m.from_user.id, None)
    bot.send_message(
        m.chat.id, "🏠 মেইন মেনু 👇",
        reply_markup=menu_user(m.from_user.id)
    )

# ================= TEXT MESSAGES / STATES =================
@bot.message_handler(func=lambda m: True)
def handle_text(m):
    uid = m.from_user.id
    user(uid, m.from_user)
    state = states.get(uid)

    if not state:
        return

    if state == "qty":
        try:
            q = int(m.text.strip())
            if q <= 0:
                raise ValueError
        except (ValueError, AttributeError):
            return bot.send_message(
                m.chat.id, "⚠️ সঠিক সংখ্যা লিখুন (যেমন: 1, 2, 3)"
            )

        msg = bot.send_message(m.chat.id, "⏳ আপনার Oʀᴅᴇʀ রেডি করা হচ্ছে...")
        for i in range(3):
            try:
                bot.edit_message_text(
                    f"⏳ আপনার Oʀᴅᴇʀ রেডি করা হচ্ছে... {['◐','◓','◑','◒'][i%4]}",
                    m.chat.id, msg.message_id
                )
                time.sleep(0.3)
            except Exception:
                pass

        # একই সময়ে একাধিক purchase হলেও একই stock বিক্রি হবে না
        with cn() as c:
            c.execute("BEGIN IMMEDIATE")
            items = c.execute(
                "SELECT * FROM stock WHERE sold=0 ORDER BY id LIMIT ?", (q,)
            ).fetchall()

            if len(items) < q:
                c.rollback()
                states.pop(uid, None)
                return bot.send_message(
                    m.chat.id,
                    f"❌ স্টক অপর্যাপ্ত। বর্তমানে আছে: {stock_left()}"
                )

            total = sum(float(i["rate"] or 0) for i in items)
            u = c.execute(
                "SELECT balance FROM users WHERE user_id=?", (uid,)
            ).fetchone()

            if not u or float(u["balance"]) < total:
                balance = float(u["balance"]) if u else 0
                c.rollback()
                states.pop(uid, None)
                return bot.send_message(
                    m.chat.id,
                    f"❌ Bᴀʟᴀɴᴄᴇ Sʜᴏʀᴛ।\n"
                    f"প্রয়োজন : {total:g} | আছে : {balance:g}\n\n"
                    f"Balance কিনতে 💰 Bᴀʟ বাটনে যোগাযোগ করুন।"
                )

            c.executemany(
                "UPDATE stock SET sold=1, buyer=? WHERE id=? AND sold=0",
                [(uid, i["id"]) for i in items]
            )
            c.execute(
                "INSERT INTO orders(uid,qty,total) VALUES(?,?,?)",
                (uid, q, total)
            )
            c.execute(
                "UPDATE users SET balance=balance-? WHERE user_id=?",
                (total, uid)
            )

        def block(it):
            return (
                f"===========================\n"
                f"{it['name']}  ( Dᴇʟɪᴠᴇʀʏ Tɪᴍᴇ : {it['dtime']} ) ✅\n"
                f"===========================\n"
                f"Gᴍᴀɪʟ : {it['gmail']}\n"
                f"Pᴀss : {it['pw']}\n"
                f"Exᴘɪʀᴇᴅ Tɪᴍᴇ : {it['exp']}\n\n"
                f"Gᴍᴀɪʟ এবং Pᴀss কাজ না করলে\n"
                f"Kᴇʏ ব্যবহার করুন...✅\n\n"
                f"Aᴄᴛɪᴠᴇ Kᴇʏ : {it['key']}\n"
                f"==============\n"
                f"Uᴘᴅᴀᴛᴇ Rᴀᴛᴇ : {it['rate']}\n"
                f"==============\n"
                f"Tʜᴀɴᴋs Fᴏʀ Sᴜᴘᴘᴏʀᴛ ❤️‍🔥"
            )

        txt = "\n\n".join(block(i) for i in items)
        file_data = BytesIO(txt.encode("utf-8"))
        file_data.name = f"VPN_{q}pcs.txt"

        try:
            bot.send_document(
                m.chat.id,
                file_data,
                caption=(
                    f"✅ আপনার {q} টি Oʀᴅᴇʀ রেডি!\n"
                    f"💵 Tᴏᴛᴀʟ Aᴍᴏᴜɴᴛ : {total:g}\n\n"
                    f"Tʜᴀɴᴋ Yᴏᴜ Cᴜsᴛᴏᴍᴇʀ ❤️‍🔥"
                )
            )
        except Exception as e:
            bot.send_message(
                m.chat.id,
                "⚠️ Order সম্পন্ন হয়েছে, কিন্তু delivery file পাঠানো যায়নি। "
                "দয়া করে Admin-এর সাথে যোগাযোগ করুন।"
            )
            print("Delivery error:", e)

        if stock_left() == 0:
            for owner_id in MAIN_OWNER_IDS:
                try:
                    bot.send_message(
                        owner_id,
                        f"⚠️ Sᴛᴏᴄᴋ Oᴜᴛ!\n"
                        f"Lᴀsᴛ Cᴜsᴛᴏᴍᴇʀ: {uid} ({q} Pᴄs Oʀᴅᴇʀ)"
                    )
                except Exception:
                    pass

        states.pop(uid, None)

    elif state == "stock":
        n = 0
        errors = 0
        with cn() as c:
            for line in m.text.splitlines():
                if not line.strip():
                    continue
                p = [x.strip() for x in line.split("|")]
                if len(p) != 7:
                    errors += 1
                    continue
                try:
                    rate = float(p[6])
                    c.execute("""
                        INSERT INTO stock(name,dtime,gmail,pw,exp,key,rate)
                        VALUES(?,?,?,?,?,?,?)
                    """, (p[0], p[1], p[2], p[3], p[4], p[5], rate))
                    n += 1
                except (ValueError, sqlite3.Error):
                    errors += 1

        bot.send_message(
            m.chat.id,
            f"✅ {n} টি VPN স্টকে যোগ হয়েছে।"
            + (f"\n⚠️ ভুল ফরম্যাট/Rate: {errors} টি" if errors else "")
        )
        states.pop(uid, None)

    elif state == "rate":
        try:
            r = float(m.text)
            if r < 0:
                raise ValueError
        except ValueError:
            return bot.send_message(m.chat.id, "সঠিক সংখ্যা দিন")
        with cn() as c:
            c.execute("UPDATE stock SET rate=? WHERE sold=0", (r,))
        bot.send_message(m.chat.id, f"✅ Nᴇᴡ Rᴀᴛᴇ : {r:g}")
        states.pop(uid, None)

    elif state == "addadm":
        try:
            target = int(m.text)
        except ValueError:
            return bot.send_message(m.chat.id, "সঠিক ID দিন")
        with cn() as c:
            c.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (target,))
            c.execute("UPDATE users SET admin=1 WHERE user_id=?", (target,))
        bot.send_message(m.chat.id, f"✅ {target} Jᴜsᴛ Nᴏᴡ Aᴅᴍɪɴ।")
        states.pop(uid, None)

    elif state == "ban":
        try:
            target = int(m.text)
        except ValueError:
            return bot.send_message(m.chat.id, "সঠিক Usᴇʀ ɪᴅ দিন")
        target_user = user(target)
        new = 0 if target_user["banned"] else 1
        with cn() as c:
            c.execute("UPDATE users SET banned=? WHERE user_id=?", (new, target))
        bot.send_message(
            m.chat.id,
            f"✅ {target} → {'🚫 Bᴀɴ Usᴇʀ' if new else '✅ Uɴʙᴀɴ Usᴇʀ'}"
        )
        states.pop(uid, None)

    elif state == "bal_uid":
        try:
            target = int(m.text)
            user(target)
            states[uid] = ("bal_amt", target)
            bot.send_message(m.chat.id, "পরিমাণ লিখুন (+ যোগ, - কাট) :")
        except ValueError:
            bot.send_message(m.chat.id, "সঠিক Usᴇʀ ɪᴅ দিন")

    elif isinstance(state, tuple) and state[0] == "bal_amt":
        try:
            amt = float(m.text)
        except ValueError:
            return bot.send_message(m.chat.id, "সঠিক সংখ্যা দিন")

        target = state[1]
        add_bal(target, amt)
        bot.send_message(m.chat.id, f"✅ {target} Yᴏᴜʀ Bᴀʟᴀɴᴄᴇ {amt:+g}")
        try:
            bot.send_message(
                target,
                f"💰 আপনার Balance-এ {amt:+g} যোগ/বিয়োগ করা হয়েছে।"
            )
        except Exception:
            pass
        states.pop(uid, None)

    elif state == "bc":
        ok = fail = 0
        with cn() as x:
            ids = [
                r["user_id"]
                for r in x.execute("SELECT user_id FROM users").fetchall()
            ]
        for target in ids:
            try:
                bot.send_message(target, m.text)
                ok += 1
            except Exception:
                fail += 1
            time.sleep(0.05)

        bot.send_message(
            m.chat.id,
            f"✅ BʀᴏᴀᴅCᴀsᴛ\nসফল : {ok} | ব্যর্থ: {fail}"
        )
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
