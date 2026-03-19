from aiogram import Bot
from config.settings import BOT_TOKEN

def create_bot() -> Bot:
    return Bot(token=BOT_TOKEN)
