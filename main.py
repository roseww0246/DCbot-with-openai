import os
import asyncio
import logging
from datetime import datetime
import tweepy
import discord
from discord.ext import commands, tasks
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
import aiohttp
import openai

logging.basicConfig(level=logging.INFO)

# ================================
# 環境變數
# ================================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ================================
# FastAPI
# ================================
app = FastAPI()

@app.get("/ping")
async def ping():
    return PlainTextResponse("pong")

# ================================
# Discord Bot
# ================================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logging.info(f"✅ 已登入 Discord: {bot.user}")

@bot.tree.command(name="debug", description="系統偵錯資訊")
async def debug(interaction: discord.Interaction):
    info = f"🕒 {datetime.now().astimezone()} | Bot 活動中"
    await interaction.response.send_message(info)

# ================================
# Twitter
# ================================
def twitter_client():
    auth = tweepy.OAuth1UserHandler(
        TWITTER_API_KEY, TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
    )
    return tweepy.API(auth)

def tweet_text_with_image(text: str, image_bytes: bytes = None):
    api = twitter_client()
    if image_bytes:
        api.update_status_with_media(filename="image.png", file=image_bytes, status=text)
    else:
        api.update_status(text)

# ================================
# OpenAI 生成圖片
# ================================
openai.api_key = OPENAI_API_KEY

async def generate_image(prompt: str) -> bytes:
    resp = await openai.Image.acreate(prompt=prompt, n=1, size="1024x1024")
    b64 = resp.data[0].b64_json
    import base64
    return base64.b64decode(b64)

# ================================
# 自動排程發文
# ================================
POST_TIMES = ["08:00", "12:00", "18:00", "22:00"]
POST_TOPICS = ["Topic 1", "Topic 2", "Topic 3"]

async def auto_post_loop():
    while True:
        now = datetime.now().strftime("%H:%M")
        if now in POST_TIMES:
            topic = POST_TOPICS[datetime.now().minute % len(POST_TOPICS)]
            image_bytes = await generate_image(f"{topic} illustration")
            tweet_text_with_image(topic, image_bytes)
            logging.info(f"📝 發文成功: {topic}")
            await asyncio.sleep(60)  # 避免同分鐘重複
        await asyncio.sleep(10)

# ================================
# 保活心跳（防止 Railway 停止）
# ================================
async def keep_alive():
    await asyncio.sleep(5)
    url = f"http://localhost:{os.getenv('PORT', 8080)}/ping"
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(url) as resp:
                    logging.info(f"保活心跳: {resp.status}")
            except Exception as e:
                logging.warning(f"保活心跳失敗: {e}")
            await asyncio.sleep(25)

# ================================
# 主程式啟動
# ================================
async def start_bot_and_server():
    bot_task = asyncio.create_task(bot.start(DISCORD_TOKEN))
    api_task = asyncio.create_task(auto_post_loop())
    keep_alive_task = asyncio.create_task(keep_alive())
    # Uvicorn 以非阻塞方式啟動 FastAPI
    import uvicorn
    uvicorn_config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)), log_level="info")
    uvicorn_server = uvicorn.Server(uvicorn_config)
    uvicorn_task = asyncio.create_task(uvicorn_server.serve())
    await asyncio.gather(bot_task, api_task, keep_alive_task, uvicorn_task)

if __name__ == "__main__":
    asyncio.run(start_bot_and_server())
