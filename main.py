import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
import logging
from io import BytesIO
import openai
import aiohttp

# ----------------- 設定 -----------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DISCORD_TOKEN or not OPENAI_API_KEY:
    raise ValueError("請確認環境變數 DISCORD_TOKEN 與 OPENAI_API_KEY 已設定")

openai.api_key = OPENAI_API_KEY

intents = discord.Intents.default()
intents.message_content = True

logging.basicConfig(level=logging.INFO)

# ----------------- Discord Bot -----------------
class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

client = MyClient(intents=intents)

@client.event
async def on_ready():
    await client.tree.sync()
    logging.info(f"✅ 已登入 Discord: {client.user}")
    logging.info("🫀 Bot 待命中...")

# ----------------- 指令：生成圖片 -----------------
@client.tree.command(name="make_picture", description="生成圖片並回傳到頻道")
@app_commands.describe(prompt="請輸入想生成的圖片內容")
async def make_picture(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    try:
        logging.info(f"🎨 收到生成請求: {prompt}")
        # 使用 OpenAI Image API (1.0+ 新版)
        response = openai.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )
        image_url = response.data[0].url

        # 將圖片抓下來轉成 Discord 可發送的檔案
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                img_bytes = await resp.read()
        file = discord.File(BytesIO(img_bytes), filename="image.png")
        await interaction.followup.send(file=file)
        logging.info("✅ 圖片已回傳 Discord")
    except Exception as e:
        logging.error(f"❌ 生成圖片失敗: {e}")
        await interaction.followup.send(f"生成圖片失敗: {e}")

# ----------------- 啟動 Bot -----------------
client.run(DISCORD_TOKEN)
