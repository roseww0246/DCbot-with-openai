import os
import asyncio
import logging
from datetime import datetime
import pytz
import random

import discord
from discord.ext import commands, tasks
from openai import OpenAI
import tweepy

# -----------------------
# 環境變數
# -----------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET_KEY = os.getenv("X_API_SECRET_KEY")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

# -----------------------
# 日誌
# -----------------------
logging.basicConfig(level=logging.INFO)

# -----------------------
# 時區
# -----------------------
tz = pytz.timezone("Asia/Taipei")

# -----------------------
# OpenAI
# -----------------------
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# -----------------------
# Twitter (X) API
# -----------------------
auth = tweepy.OAuth1UserHandler(
    X_API_KEY, X_API_SECRET_KEY, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET
)
x_api = tweepy.API(auth)

# -----------------------
# Discord Bot
# -----------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# -----------------------
# 全域變數
# -----------------------
time_slots = ["08:00", "12:00", "18:00", "22:00"]
themes = ["可愛動物", "迷因"]
paused = False

# -----------------------
# Helper Functions
# -----------------------
async def generate_image(prompt: str) -> str:
    """使用 OpenAI 生成圖片，回傳本地檔案路徑"""
    try:
        response = openai_client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )
        image_url = response.data[0].url
        filename = f"temp_{int(datetime.now().timestamp())}.png"
        # 下載圖片
        import requests
        r = requests.get(image_url)
        with open(filename, "wb") as f:
            f.write(r.content)
        return filename
    except Exception as e:
        logging.error(f"❌ 生成圖片失敗: {e}")
        return None

async def post_to_x(image_path: str, status: str):
    """發文到 X"""
    try:
        media = x_api.media_upload(image_path)
        x_api.update_status(status=status, media_ids=[media.media_id])
        logging.info("✅ 發文成功")
    except Exception as e:
        logging.error(f"❌ 發文失敗: {e}")

async def post_report_to_dc(content: str):
    """發報告到 Discord"""
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(content)
                return

# -----------------------
# 排程任務
# -----------------------
@tasks.loop(minutes=1)
async def scheduler():
    if paused:
        return

    now = datetime.now(tz).strftime("%H:%M")
    if now in time_slots:
        theme = random.choice(themes)
        logging.info(f"🕒 發送主題: {theme}")
        image_path = await generate_image(theme)
        if image_path:
            await post_to_x(image_path, f"今天的主題：{theme}")
            report = f"📊 發送成功: {theme} ({now})"
            await post_report_to_dc(report)

# -----------------------
# Discord Slash Command
# -----------------------
@bot.tree.command(name="addtime", description="增加發文時段")
async def addtime(interaction: discord.Interaction, hour: str):
    if hour not in time_slots:
        time_slots.append(hour)
        await interaction.response.send_message(f"✅ 時段 {hour} 已新增", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ 時段 {hour} 已存在", ephemeral=True)

@bot.tree.command(name="removetime", description="刪除發文時段")
async def removetime(interaction: discord.Interaction, hour: str):
    if hour in time_slots:
        time_slots.remove(hour)
        await interaction.response.send_message(f"✅ 時段 {hour} 已移除", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ 時段 {hour} 不存在", ephemeral=True)

@bot.tree.command(name="time_schedule", description="查看現有時段")
async def time_schedule(interaction: discord.Interaction):
    await interaction.response.send_message(f"🕒 時段: {', '.join(time_slots)}", ephemeral=True)

@bot.tree.command(name="addtheme", description="增加主題")
async def addtheme(interaction: discord.Interaction, theme: str):
    if theme not in themes:
        themes.append(theme)
        await interaction.response.send_message(f"✅ 主題 {theme} 已新增", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ 主題 {theme} 已存在", ephemeral=True)

@bot.tree.command(name="removetheme", description="刪除主題")
async def removetheme(interaction: discord.Interaction, theme: str):
    if theme in themes:
        themes.remove(theme)
        await interaction.response.send_message(f"✅ 主題 {theme} 已移除", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ 主題 {theme} 不存在", ephemeral=True)

@bot.tree.command(name="theme_schedule", description="查看現有主題")
async def theme_schedule(interaction: discord.Interaction):
    await interaction.response.send_message(f"📚 主題: {', '.join(themes)}", ephemeral=True)

@bot.tree.command(name="stop", description="暫停排程")
async def stop(interaction: discord.Interaction):
    global paused
    paused = True
    await interaction.response.send_message("⏸️ 排程已暫停", ephemeral=True)

@bot.tree.command(name="resume", description="恢復排程")
async def resume(interaction: discord.Interaction):
    global paused
    paused = False
    await interaction.response.send_message("▶️ 排程已恢復", ephemeral=True)

@bot.tree.command(name="report", description="查看最新發文報告")
async def report(interaction: discord.Interaction):
    await interaction.response.send_message(f"📝 時段: {time_slots}\n📚 主題: {themes}\n暫停: {paused}", ephemeral=True)

@bot.tree.command(name="debug", description="系統偵錯")
async def debug(interaction: discord.Interaction):
    x_status = "✅" if X_API_KEY and X_API_SECRET_KEY else "❌"
    await interaction.response.send_message(
        f"🧪 系統偵錯\n━━━━━━━━━━━━━━\n"
        f"🕒 時區：Asia/Taipei\n"
        f"⏰ 排程時間：{', '.join(time_slots)}\n"
        f"📚 主題數：{len(themes)}\n"
        f"⏸️ 暫停：{paused}\n\n"
        f"🐦 X API Key 設定：{x_status}\n",
        ephemeral=True
    )

# -----------------------
# Bot 啟動
# -----------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    scheduler.start()
    logging.info(f"已登入 Discord: {bot.user}")

# -----------------------
# 主程式
# -----------------------
if __name__ == "__main__":
    try:
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        logging.info("🛑 手動停止 Bot")
