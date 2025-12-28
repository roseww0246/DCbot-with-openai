import os
import asyncio
import logging
import random
import datetime
from discord.ext import commands, tasks
import discord
import openai
import tweepy  # X API

# Logging 設定
logging.basicConfig(level=logging.INFO)

# ----------------- 環境變數 -----------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
X_API_CONSUMER_KEY = os.getenv("X_API_CONSUMER_KEY")
X_API_CONSUMER_SECRET = os.getenv("X_API_CONSUMER_SECRET")
X_API_ACCESS_TOKEN = os.getenv("X_API_ACCESS_TOKEN")
X_API_ACCESS_TOKEN_SECRET = os.getenv("X_API_ACCESS_TOKEN_SECRET")

# 驗證環境變數
required_envs = [
    ("DISCORD_TOKEN", DISCORD_TOKEN),
    ("OPENAI_API_KEY", OPENAI_API_KEY),
    ("X_API_CONSUMER_KEY", X_API_CONSUMER_KEY),
    ("X_API_CONSUMER_SECRET", X_API_CONSUMER_SECRET),
    ("X_API_ACCESS_TOKEN", X_API_ACCESS_TOKEN),
    ("X_API_ACCESS_TOKEN_SECRET", X_API_ACCESS_TOKEN_SECRET)
]

for name, val in required_envs:
    if not val:
        logging.error(f"❌ 環境變數 {name} 未設定！")
        exit(1)

# OpenAI
openai.api_key = OPENAI_API_KEY

# X API (Tweepy)
try:
    auth = tweepy.OAuth1UserHandler(
        X_API_CONSUMER_KEY,
        X_API_CONSUMER_SECRET,
        X_API_ACCESS_TOKEN,
        X_API_ACCESS_TOKEN_SECRET
    )
    x_api = tweepy.API(auth)
    x_api.verify_credentials()
    logging.info("✅ X API 登入成功")
except Exception as e:
    logging.error(f"❌ X API 登入失敗: {e}")
    x_api = None

# ----------------- Discord Bot -----------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 時間排程與主題
time_schedule = ["08:00", "12:00", "18:00", "22:00"]
themes = ["cute animals", "meme", "trending"]
paused = False

# ----------------- Discord 指令 -----------------
@bot.command(description="增加發文時段")
async def addtime(ctx, time: str):
    if time not in time_schedule:
        time_schedule.append(time)
        await ctx.send(f"✅ 已新增時段: {time}")
    else:
        await ctx.send("⚠️ 時段已存在")

@bot.command(description="移除發文時段")
async def removetime(ctx, time: str):
    if time in time_schedule:
        time_schedule.remove(time)
        await ctx.send(f"✅ 已移除時段: {time}")
    else:
        await ctx.send("⚠️ 時段不存在")

@bot.command(description="查看現有發文時段")
async def time_schedule_cmd(ctx):
    await ctx.send(f"⏰ 現有時段: {', '.join(time_schedule)}")

@bot.command(description="增加主題")
async def addtheme(ctx, *, theme: str):
    if theme not in themes:
        themes.append(theme)
        await ctx.send(f"✅ 已新增主題: {theme}")
    else:
        await ctx.send("⚠️ 主題已存在")

@bot.command(description="移除主題")
async def removetheme(ctx, *, theme: str):
    if theme in themes:
        themes.remove(theme)
        await ctx.send(f"✅ 已移除主題: {theme}")
    else:
        await ctx.send("⚠️ 主題不存在")

@bot.command(description="查看現有主題")
async def theme_schedule(ctx):
    await ctx.send(f"📚 現有主題: {', '.join(themes)}")

@bot.command(description="暫停發文")
async def stop(ctx):
    global paused
    paused = True
    await ctx.send("⏸️ 已暫停發文")

@bot.command(description="恢復發文")
async def resume(ctx):
    global paused
    paused = False
    await ctx.send("▶️ 已恢復發文")

@bot.command(description="系統偵錯 / Debug")
async def debug(ctx):
    embed = discord.Embed(title="🧪 系統偵錯")
    embed.add_field(name="時區", value="Asia/Taipei")
    embed.add_field(name="排程時間", value=", ".join(time_schedule))
    embed.add_field(name="主題數", value=str(len(themes)))
    embed.add_field(name="暫停", value=str(paused))
    embed.add_field(name="X API 登入", value="✅" if x_api else "❌")
    embed.add_field(name="X API 發文", value="✅" if x_api else "❌")
    await ctx.send(embed=embed)

# ----------------- OpenAI 圖片生成 -----------------
async def generate_image(prompt: str) -> str:
    try:
        result = openai.Image.create(
            prompt=prompt,
            n=1,
            size="1024x1024"
        )
        url = result['data'][0]['url']
        return url
    except Exception as e:
        logging.error(f"❌ OpenAI 生成圖片失敗: {e}")
        return None

# ----------------- 發文任務 -----------------
@tasks.loop(minutes=1)
async def scheduler():
    now = datetime.datetime.now().strftime("%H:%M")
    if paused or not x_api:
        return
    if now in time_schedule:
        theme = random.choice(themes)
        logging.info(f"📢 發文時段觸發: {now} 主題: {theme}")
        img_url = await generate_image(theme)
        status = f"自動發文 - 主題: {theme}"
        try:
            if img_url:
                x_api.update_status(status=status)  # Free Tier 不支援上傳圖片
            else:
                x_api.update_status(status=status)
            logging.info("✅ 發文成功")
        except Exception as e:
            logging.error(f"❌ 發文失敗: {e}")

# ----------------- Bot 事件 -----------------
@bot.event
async def on_ready():
    logging.info(f"已登入 Discord: {bot.user}")
    scheduler.start()

# ----------------- Railway 友善主程式 -----------------
async def main():
    await bot.start(DISCORD_TOKEN)
    await asyncio.Event().wait()  # 永遠等待，不會停止

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("🛑 手動停止 Bot")

