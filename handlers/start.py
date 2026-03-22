from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from keyboards.main import main_menu

from services.admin import ADMINS
from services.admin import suppress_group


router = Router()



@suppress_group
@router.message(CommandStart())
async def start_handler(message: Message):
    if message.from_user.id in ADMINS:
        await message.answer(
            f"Hello {message.from_user.full_name} 👋\n"
            f"Your id : {message.from_user.id}\n"
            f"Select an option:",
            reply_markup=main_menu
        )
    else:
        await message.answer(
            f"Hello {message.from_user.full_name} 👋\n"
            f"Your id : {message.from_user.id}\n"
            f"If you don’t see the commands, it means you don’t have administrator rights. Please contact your administrator to request access \n"
            f"if you are a dispatch click to 👇 \n/gross_dispatcher",
        )
    

USER_HELP_TEXT = """
🤖 *budut komandy bota for just users*
"""

ADMIN_HELP_TEXT = f"""
🤖 *budut komandy bota for admins*
"""

@suppress_group
@router.message(Command("help"))
async def help_command(message: Message):
    if message.from_user.id in ADMINS:
        await message.reply(ADMIN_HELP_TEXT, parse_mode="Markdown")
    else:
        await message.reply(USER_HELP_TEXT, parse_mode="Markdown")