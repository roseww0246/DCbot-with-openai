import os
import discord
from discord import app_commands
from discord.ext import commands
from fastapi import FastAPI
import uvicorn
import asyncio
import openai
import logging

# ----------------- 設定 -----------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 8080))

if not DISCORD_TOKEN or not OPENAI_API_KEY:
    raise ValueError("請確認環境變數 DISCORD_TOKEN 與 OPENAI_API_KEY 已設定")

openai.api_key = OPENAI_API_KEY

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)
app = FastAPI()
logging.basicConfig(level=logging.INFO)

# ----------------- Discord 指令 -----------------
class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

client = MyClient(intents=intents)

@client.event
async def on_ready():
    await client.tree.sync()
    logging.info(f"✅ 已登入 Discord: {client.user}")

@client.tree.command(name="make_picture", description="生成圖片並回傳到頻道")
async def make_picture(interaction: discord.Interaction, prompt: str):
    await interaction.response.send_message("🖌️ 開始生成圖片，請稍候...")
    try:
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            size="512x512"
        )
        image_url = response['data'][0]['url']
        await interaction.followup.send(f"✅ 圖片生成完成：{image_url}")
    except openai.error.OpenAIError as e:
        await interaction.followup.send(f"❌ 生成圖片時出錯：{e}")

# ----------------- FastAPI 保活 -----------------
@app.get("/ping")
async def ping():
    return {"status": "ok"}

# ----------------- 啟動函數 -----------------
async def start_bot():
    await client.start(DISCORD_TOKEN)

async def main():
    # 建立 Discord Bot 任務
    bot_task = asyncio.create_task(start_bot())
    # 啟動 FastAPI
    config = uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="info")
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())

    await asyncio.gather(bot_task, server_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot 停止運行")
