from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from db.database import fetch_all


async def get_drivers_keyboard():
    """Получить клавиатуру со списком водителей"""
    drivers = await fetch_all("SELECT name FROM drivers")
    
    keyboard = ReplyKeyboardMarkup(keyboard=[], resize_keyboard=True)
    for driver in drivers:
        keyboard.keyboard.append([KeyboardButton(text=driver['name'])])
    
    keyboard.keyboard.append([KeyboardButton(text="◀️ Назад")])
    return keyboard


async def get_dispatchers_keyboard():
    """Получить клавиатуру со списком диспетчеров"""
    dispatchers = await fetch_all("SELECT name FROM dispatchers")
    
    keyboard = ReplyKeyboardMarkup(keyboard=[], resize_keyboard=True)
    for dispatcher in dispatchers:
        keyboard.keyboard.append([KeyboardButton(text=dispatcher['name'])])
    
    keyboard.keyboard.append([KeyboardButton(text="◀️ Назад")])
    return keyboard


def get_export_keyboard(dispatcher_name: str):
    """Получить инлайн-клавиатуру с кнопкой экспорта"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Export", callback_data=f"export_dispatcher:{dispatcher_name}")]
    ])
    return keyboard


# Главное меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/gross_driver 👨‍✈️")],
        [KeyboardButton(text="/gross_dispatcher 📋")]
    ],
    resize_keyboard=True
)