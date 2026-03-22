from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from db.database import fetch_all


async def get_drivers_keyboard():
    drivers = await fetch_all("SELECT name FROM drivers")

    keyboard = ReplyKeyboardMarkup(keyboard=[], resize_keyboard=True)
    for driver in drivers:
        keyboard.keyboard.append([KeyboardButton(text=driver["name"])])

    keyboard.keyboard.append([KeyboardButton(text=f"{chr(0x25C0)}{chr(0xFE0F)} Назад")])
    return keyboard


async def get_dispatchers_keyboard():
    dispatchers = await fetch_all("SELECT name FROM dispatchers")

    keyboard = ReplyKeyboardMarkup(keyboard=[], resize_keyboard=True)
    for dispatcher in dispatchers:
        keyboard.keyboard.append([KeyboardButton(text=dispatcher["name"])])

    keyboard.keyboard.append([KeyboardButton(text=f"{chr(0x25C0)}{chr(0xFE0F)} Назад")])
    return keyboard


def get_export_keyboard(dispatcher_name: str):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{chr(0x1F4E5)} Export", callback_data=f"export_dispatcher:{dispatcher_name}")]
        ]
    )
    return keyboard


main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=f"/gross_driver {chr(0x1F468)}{chr(0x200D)}{chr(0x2708)}{chr(0xFE0F)}")],
        [KeyboardButton(text=f"/gross_dispatcher {chr(0x1F4CB)}")],
    ],
    resize_keyboard=True,
)
