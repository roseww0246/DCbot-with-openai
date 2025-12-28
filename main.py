import os
import asyncio
import discord
from discord.ext import commands, tasks
import openai
import tweepy
import logging
from datetime import datetime
import pytz

# ----------------------------
# 設定日誌
# ----------------------------
logging.basicConfig(level=logging.INFO)

# ----------------------------
# 環境變數
# ----------------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

if not all([DISCORD_TOKEN, OPENAI_API_KEY, TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
    logging.error("❌ 請確認所有環境變數已設定")
    exit(1)

# ----------------------------
# 初始化 OpenAI
# ----------------------------
openai.api_key = OPENAI_API_KEY

# ----------------------------
# 初始化 Twitter
# ----------------------------
auth = tweepy.OAuth1UserHandler(
    TWITTER_API_KEY, TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
)
twitter_api = tweepy.API(auth)

# ----------------------------
# 初始化 Discord
# ----------------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# ----------------------------
# 全域資料
# ----------------------------
timezone = pytz.timezone("Asia/Taipei")
scheduled_times = ["08:00", "12:00", "18:00", "22:00"]
themes = ["科技", "藝術", "生活"]

paused = False

# ----------------------------
# Discord 指令
# ----------------------------
@bot.command()
async def addtime(ctx, time_str: str):
    if time_str not in scheduled_times:
        scheduled_times.append(time_str)
        await ctx.send(f"✅ 已新增時段: {time_str}")
    else:
        await ctx.send(f"⚠️ 時段 {time_str} 已存在")

@bot.command()
async def removetime(ctx, time_str: str):
    if time_str in scheduled_times:
        scheduled_times.remove(time_str)
        await ctx.send(f"✅ 已刪除時段: {time_str}")
    else:
        await ctx.send(f"⚠️ 時段 {time_str} 不存在")

@bot.command()
async def time_schedule(ctx):
    await ctx.send(f"🕒 現有時段: {', '.join(sorted(scheduled_times))}")

@bot.command()
async def addtheme(ctx, theme: str):
    if theme not in themes:
        themes.append(theme)
        await ctx.send(f"✅ 已新增主題: {theme}")
    else:
        await ctx.send(f"⚠️ 主題 {theme} 已存在")

@bot.command()
async def removetheme(ctx, theme: str):
    if theme in themes:
        themes.remove(theme)
        await ctx.send(f"✅ 已刪除主題: {theme}")
    else:
        await ctx.send(f"⚠️ 主題 {theme} 不存在")

@bot.command()
async def theme_schedule(ctx):
    await ctx.send(f"📚 現有主題: {', '.join(themes)}")

@bot.command()
async def debug(ctx):
    msg = (
        f"🧪 系統偵錯\n"
        f"━━━━━━━━━━━━━━\n"
        f"🕒 時區：{timezone}\n"
        f"⏰ 排程時間：{', '.join(sorted(scheduled_times))}\n"
        f"📚 主題數：{len(themes)}\n"
        f"⏸️ 暫停：{paused}\n"
    )
    await ctx.send(msg)

@bot.command()
async def pause(ctx):
    global paused
    paused = True
    await ctx.send("⏸️ 已暫停自動發文")

@bot.command()
async def resume(ctx):
    global paused
    paused = False
    await ctx.send("▶️ 已恢復自動發文")

# ----------------------------
# 自動推文任務
# ----------------------------
async def generate_image(prompt: str) -> bytes:
    """使用 OpenAI 生成圖片"""
    try:
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            size="1024x1024"
        )
        img_url = response['data'][0]['url']
        import requests
        r = requests.get(img_url)
        return r.content
    except Exception as e:
        logging.error(f"❌ 生成圖片失敗: {e}")
        return None

async def post_to_twitter(text: str, image_bytes: bytes = None):
    try:
        if image_bytes:
            from io import BytesIO
            file = BytesIO(image_bytes)
            file.name = "image.png"
            media = twitter_api.media_upload(filename="image.png", file=file)
            twitter_api.update_status(status=text, media_ids=[media.media_id])
        else:
            twitter_api.update_status(status=text)
        logging.info("🐦 已發文到 Twitter")
    except Exception as e:
        logging.error(f"❌ 發文到 Twitter 失敗: {e}")

@tasks.loop(seconds=60)
async def scheduled_loop():
    global paused
    if paused:
        return
    now = datetime.now(timezone)
    time_str = now.strftime("%H:%M")
    if time_str in scheduled_times:
        theme = themes[now.minute % len(themes)]
        prompt = f"以 '{theme}' 為主題生成圖片"
        img_bytes = await generate_image(prompt)
        tweet_text = f"{theme} 主題自動推文 - {now.strftime('%Y-%m-%d %H:%M')}"
        await post_to_twitter(tweet_text, img_bytes)
        logging.info(f"🟢 發布完成: {tweet_text}")

# ----------------------------
# Bot 啟動事件
# ----------------------------
@bot.event
async def on_ready():
    logging.info(f"✅ 已登入 Discord: {bot.user}")
    scheduled_loop.start()

# ----------------------------
# 永遠運行保持 Railway 友善
# ----------------------------
async def main():
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("🛑 手動停止 Bot")
