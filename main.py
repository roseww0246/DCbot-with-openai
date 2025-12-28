import os
import asyncio
import logging
from datetime import datetime

import discord
from discord import app_commands

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

import uvicorn

# ======================
# 基本設定
# ======================
logging.basicConfig(level=logging.INFO)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
PORT = int(os.getenv("PORT", 8080))

# ======================
# Discord Bot
# ======================
intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

@bot.event
async def on_ready():
    await tree.sync()
    logging.info(f"✅ Discord 已登入：{bot.user}")

# ---------- Slash 指令 ----------
@tree.command(name="debug", description="系統狀態")
async def debug(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"🫀 Bot 活著\n⏰ {datetime.now()}"
    )

# ======================
# FastAPI（Railway 主程序）
# ======================
app = FastAPI()

@app.get("/ping")
async def ping():
    return PlainTextResponse("pong")

# ======================
# FastAPI 生命周期（關鍵）
# ======================
@app.on_event("startup")
async def startup():
    logging.info("🚀 FastAPI 啟動，啟動 Discord Bot")
    asyncio.create_task(bot.start(DISCORD_TOKEN))

@app.on_event("shutdown")
async def shutdown():
    logging.info("🛑 關閉 Discord Bot")
    await bot.close()

# ======================
# 主入口（只能啟動 uvicorn）
# ======================
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        log_level="info"
    )
