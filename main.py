import os
import asyncio
import logging
from datetime import datetime, time
import discord
from discord.ext import commands, tasks
import tweepy
import openai
from fastapi import FastAPI
import uvicorn
import nest_asyncio

# ------------------- Logger -------------------
logging.basicConfig(level=logging.INFO)

# ------------------- 環境變數 -------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")
PORT = int(os.getenv("PORT", 8000))

# ------------------- Discord Bot -------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# ------------------- X API (Twitter) -------------------
twitter_api = None
if all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET]):
    auth = tweepy.OAuth1UserHandler(
        X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET
    )
    twitter_api = tweepy.API(auth)

# ------------------- OpenAI -------------------
openai.api_key = OPENAI_API_KEY

# ------------------- FastAPI 保活 -------------------
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "alive", "time": str(datetime.now())}

# ------------------- 排程管理 -------------------
times = [time(8,0), time(12,0), time(18,0), time(22,0)]
themes = ["科技", "動物", "幽默"]
paused = False

# ------------------- Heartbeat -------------------
@tasks.loop(seconds=10)
async def heartbeat():
    logging.info(f"🫀 Bot 活動中... {datetime.now()}")

# ------------------- 自動發文 -------------------
@tasks.loop(minutes=1)
async def auto_post():
    if paused:
        return
    now = datetime.now().time()
    if any(t.hour == now.hour and t.minute == now.minute for t in times):
        theme = themes[0] if themes else "隨機主題"
        try:
            # OpenAI 生成圖片
            response = openai.Image.create(prompt=theme, n=1, size="1024x1024")
            image_url = response['data'][0]['url']

            # 發文到 X
            if twitter_api:
                twitter_api.update_status(status=f"{theme} - {datetime.now()}")
                logging.info("✅ 已發推文")
        except Exception as e:
            logging.error(f"❌ 發文失敗: {e}")

# ------------------- Discord 指令 -------------------
@bot.command()
async def debug(ctx):
    status = {
        "time": [t.strftime("%H:%M") for t in times],
        "themes": themes,
        "paused": paused,
        "X API": {
            "login": twitter_api is not None,
            "post": twitter_api is not None,
        }
    }
    await ctx.send(f"🧪 系統偵錯\n```\n{status}\n```")

@bot.command()
async def addtime(ctx, hour: int, minute: int):
    times.append(time(hour, minute))
    await ctx.send(f"✅ 新增時間 {hour:02d}:{minute:02d}")

@bot.command()
async def removetime(ctx, hour: int, minute: int):
    t = time(hour, minute)
    if t in times:
        times.remove(t)
        await ctx.send(f"✅ 移除時間 {hour:02d}:{minute:02d}")
    else:
        await ctx.send("⚠️ 時間不存在")

@bot.command()
async def time_schedule(ctx):
    await ctx.send("⏰ 現有時段：" + ", ".join(t.strftime("%H:%M") for t in times))

@bot.command()
async def addtheme(ctx, theme: str):
    themes.append(theme)
    await ctx.send(f"✅ 新增主題 {theme}")

@bot.command()
async def removetheme(ctx, theme: str):
    if theme in themes:
        themes.remove(theme)
        await ctx.send(f"✅ 移除主題 {theme}")
    else:
        await ctx.send("⚠️ 主題不存在")

@bot.command()
async def theme_schedule(ctx):
    await ctx.send("📚 現有主題：" + ", ".join(themes))

@bot.command()
async def stop(ctx):
    global paused
    paused = True
    await ctx.send("⏸️ 暫停自動發文")

@bot.command()
async def resume(ctx):
    global paused
    paused = False
    await ctx.send("▶️ 恢復自動發文")

@bot.command()
async def report(ctx):
    await ctx.send(f"📝 排程時間: {', '.join(t.strftime('%H:%M') for t in times)}\n主題數: {len(themes)}\n暫停: {paused}")

# ------------------- Bot 事件 -------------------
@bot.event
async def on_ready():
    logging.info(f"✅ 已登入 Discord: {bot.user}")
    heartbeat.start()
    auto_post.start()

# ------------------- Railway 友善啟動 -------------------
if __name__ == "__main__":
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    import signal
    # 安全退出
    for s in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(s, lambda: asyncio.create_task(bot.close()))

    # 啟動 FastAPI server + Discord Bot
    import uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="info")
    server = uvicorn.Server(config)
    loop.create_task(server.serve())
    loop.create_task(bot.start(DISCORD_TOKEN))
    loop.run_forever()
