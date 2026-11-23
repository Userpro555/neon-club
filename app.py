import os, sqlite3, hmac, hashlib, json, urllib.parse, asyncio
from datetime import datetime, timezone, date
from pathlib import Path
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

ROOT=Path(__file__).parent
TOKEN="PASTE_BOT_TOKEN_HERE"
BOT_USERNAME="PASTE_BOT_USERNAME_HERE"
WEBAPP_URL="PASTE_HTTPS_URL_HERE"
ADMIN_IDS={123456789}  # замени на свой Telegram ID
PORT=8080
DB=str(ROOT/"neon_club.sqlite3")
START_BONUS, REF_BONUS, DAILY_BONUS, QUIZ_REWARD=100,50,10,5
QUESTIONS=[
 {"q":"Сколько будет 7 × 8?","a":["54","56","64"],"c":1},
 {"q":"Какая планета Красная планета?","a":["Венера","Марс","Юпитер"],"c":1},
 {"q":"Сколько сторон у шестиугольника?","a":["5","6","8"],"c":1},
 {"q":"Какой океан самый большой?","a":["Атлантический","Индийский","Тихий"],"c":2}
]
def db():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def stamp(): return datetime.now(timezone.utc).isoformat()
def init():
 with db() as c:
  c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT, name TEXT, balance INTEGER DEFAULT 0, ref INTEGER, joined TEXT, daily TEXT DEFAULT '')")
  c.execute("CREATE TABLE IF NOT EXISTS ledger(id INTEGER PRIMARY KEY,user_id INTEGER,amount INTEGER,reason TEXT,created TEXT)")
  c.execute("CREATE TABLE IF NOT EXISTS quiz(user_id INTEGER,q INTEGER,PRIMARY KEY(user_id,q))")
def credit(c,uid,n,reason):
 c.execute("UPDATE users SET balance=balance+? WHERE id=?",(n,uid))
 c.execute("INSERT INTO ledger(user_id,amount,reason,created) VALUES(?,?,?,?)",(uid,n,reason,stamp()))
def register(u,ref=None):
 uid=int(u.id)
 with db() as c:
  if c.execute("SELECT id FROM users WHERE id=?",(uid,)).fetchone():
   c.execute("UPDATE users SET username=?,name=? WHERE id=?",(u.username or "",u.first_name or "",uid)); return False
  valid=ref if ref and ref!=uid and c.execute("SELECT id FROM users WHERE id=?",(ref,)).fetchone() else None
  c.execute("INSERT INTO users(id,username,name,balance,ref,joined) VALUES(?,?,?,?,?,?)",(uid,u.username or "",u.first_name or "",0,valid,stamp()))
  credit(c,uid,START_BONUS,"Стартовый бонус")
  if valid: credit(c,valid,REF_BONUS,"Реферал")
  return True
def auth(req):
 raw=req.headers.get("X-Telegram-Init-Data","")
 try:
  d=dict(urllib.parse.parse_qsl(raw,keep_blank_values=True)); h=d.pop("hash")
  check="\n".join(f"{k}={v}" for k,v in sorted(d.items()))
  secret=hmac.new(b"WebAppData",TOKEN.encode(),hashlib.sha256).digest()
  good=hmac.new(secret,check.encode(),hashlib.sha256).hexdigest()
  if not hmac.compare_digest(good,h): return None
  if abs(int(datetime.now(timezone.utc).timestamp())-int(d.get("auth_date","0")))>86400:return None
  u=json.loads(d["user"]); return u if u.get("id") else None
 except Exception:return None
def denied():return web.json_response({"error":"Открой Mini App через Telegram"},status=401)
async def home(r):return web.FileResponse(ROOT/"static/index.html")
async def me(r):
 u=auth(r)
 if not u:return denied()
 uid=int(u["id"])
 with db() as c:
  row=c.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone()
  if not row:
   class U:pass
   x=U();x.id=uid;x.username=u.get("username","");x.first_name=u.get("first_name","");register(x)
   row=c.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone()
  refs=c.execute("SELECT count(*) n FROM users WHERE ref=?",(uid,)).fetchone()["n"]
 return web.json_response({"id":uid,"name":row["name"],"balance":row["balance"],"refs":refs,"admin":uid in ADMIN_IDS})
async def referral(r):
 u=auth(r)
 if not u:return denied()
 return web.json_response({"link":f"https://t.me/{BOT_USERNAME}?start=ref_{u['id']}","bonus":REF_BONUS})
async def daily(r):
 u=auth(r)
 if not u:return denied()
 uid=int(u["id"]); today=date.today().isoformat()
 with db() as c:
  row=c.execute("SELECT daily FROM users WHERE id=?",(uid,)).fetchone()
  if row["daily"]==today:return web.json_response({"error":"Бонус уже получен сегодня"},status=400)
  c.execute("UPDATE users SET daily=? WHERE id=?",(today,uid));credit(c,uid,DAILY_BONUS,"Ежедневный бонус")
 return web.json_response({"reward":DAILY_BONUS})
async def quiz(r):
 u=auth(r)
 if not u:return denied()
 uid=int(u["id"])
 with db() as c:
  used={x["q"] for x in c.execute("SELECT q FROM quiz WHERE user_id=?",(uid,))}
  avail=[i for i in range(len(QUESTIONS)) if i not in used]
  if not avail:return web.json_response({"finished":True})
  i=avail[uid%len(avail)];c.execute("INSERT INTO quiz VALUES(?,?)",(uid,i))
 q=QUESTIONS[i]
 return web.json_response({"finished":False,"index":i,"q":q["q"],"answers":q["a"]})
async def answer(r):
 u=auth(r)
 if not u:return denied()
 try:
  b=await r.json();uid=int(u["id"]);i=int(b["index"]);choice=int(b["choice"]);q=QUESTIONS[i]
  if choice not in range(len(q["a"])):raise ValueError()
 except Exception:return web.json_response({"error":"Некорректный ответ"},status=400)
 with db() as c:
  if not c.execute("SELECT 1 FROM quiz WHERE user_id=? AND q=?",(uid,i)).fetchone():return web.json_response({"error":"Сначала получи вопрос"},status=400)
  if c.execute("SELECT 1 FROM ledger WHERE user_id=? AND reason=?",(uid,f"quiz-{i}")).fetchone():return web.json_response({"error":"Награда уже получена"},status=400)
  ok=choice==q["c"]
  if ok:credit(c,uid,QUIZ_REWARD,f"quiz-{i}")
 return web.json_response({"correct":ok,"reward":QUIZ_REWARD if ok else 0})
async def admin_users(r):
 u=auth(r)
 if not u or int(u["id"]) not in ADMIN_IDS:return web.json_response({"error":"Доступ запрещён"},status=403)
 with db() as c: rows=c.execute("SELECT id,name,balance FROM users ORDER BY joined DESC LIMIT 100").fetchall()
 return web.json_response({"users":[dict(x) for x in rows]})
async def adjust(r):
 u=auth(r)
 if not u or int(u["id"]) not in ADMIN_IDS:return web.json_response({"error":"Доступ запрещён"},status=403)
 try:b=await r.json();target=int(b["id"]);amount=int(b["amount"])
 except Exception:return web.json_response({"error":"Проверь ID и сумму"},status=400)
 with db() as c:
  row=c.execute("SELECT balance FROM users WHERE id=?",(target,)).fetchone()
  if not row:return web.json_response({"error":"Пользователь не найден"},status=404)
  if not amount or row["balance"]+amount<0:return web.json_response({"error":"Недопустимая сумма"},status=400)
  credit(c,target,amount,"Изменение администратором")
 return web.json_response({"ok":True})
async def main():
 if "PASTE_" in TOKEN or "PASTE_" in WEBAPP_URL:raise RuntimeError("Заполни TOKEN, BOT_USERNAME и WEBAPP_URL в app.py")
 init();bot=Bot(TOKEN);dp=Dispatcher()
 @dp.message(CommandStart())
 async def start(m:Message):
  args=(m.text or "").split(maxsplit=1);ref=None
  if len(args)>1 and args[1].startswith("ref_"):
   try:ref=int(args[1][4:])
   except:pass
  new=register(m.from_user,ref)
  kb=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🚀 Открыть NEON CLUB",web_app=WebAppInfo(url=WEBAPP_URL))]],resize_keyboard=True)
  await m.answer(("✨ Добро пожаловать! +100 стартовых Звёзд." if new else "С возвращением!")+"\nЭто внутренняя игровая валюта, не Telegram Stars.",reply_markup=kb)
 app=web.Application()
 app.router.add_get("/",home);app.router.add_get("/api/me",me);app.router.add_get("/api/ref",referral)
 app.router.add_post("/api/daily",daily);app.router.add_get("/api/quiz",quiz);app.router.add_post("/api/answer",answer)
 app.router.add_get("/api/admin/users",admin_users);app.router.add_post("/api/admin/adjust",adjust)
 app.router.add_static("/static/",ROOT/"static")
 runner=web.AppRunner(app);await runner.setup();await web.TCPSite(runner,"0.0.0.0",PORT).start()
 print("NEON CLUB запущен на порту",PORT)
 await dp.start_polling(bot)
if __name__=="__main__":asyncio.run(main())
