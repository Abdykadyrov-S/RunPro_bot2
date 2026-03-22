from functools import wraps
import logging

import asyncpg
from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from db.database import execute_query, fetch_one
from services.admin import ADMINS, notify_admins
from services.parser import parse_load as parse_load_from_parser

router = Router()

YES_CALLBACK = "update_rate_yes"
NO_CALLBACK = "update_rate_no"
MESSAGE_PREFIX = "\u203c\ufe0f"

pending_updates = {}


def admin_only(func):
    @wraps(func)
    async def wrapper(message_or_call, *args, **kwargs):
        user_id = None
        if isinstance(message_or_call, Message):
            user_id = message_or_call.from_user.id
        elif isinstance(message_or_call, CallbackQuery):
            user_id = message_or_call.from_user.id
        else:
            return

        if user_id not in ADMINS:
            if isinstance(message_or_call, Message):
                await message_or_call.reply("❌ Only admin can use this command")
            elif isinstance(message_or_call, CallbackQuery):
                await message_or_call.answer("❌ Only admin can use this command", show_alert=True)
            return

        return await func(message_or_call, *args, **kwargs)

    return wrapper


async def add_load(driver_chat_id, driver_name, dispatcher_name, broker, load_number, rate, pu_date=None, del_date=None):
    try:
        driver_row = await fetch_one("SELECT id FROM drivers WHERE chat_id=$1", driver_chat_id)
        if driver_row is None:
            legacy_driver = await fetch_one(
                """
                SELECT id
                FROM drivers
                WHERE chat_id IS NULL AND name = $1
                ORDER BY id
                LIMIT 1
                """,
                driver_name,
            )
            if legacy_driver is not None:
                await execute_query(
                    "UPDATE drivers SET chat_id = $1, name = $2 WHERE id = $3",
                    driver_chat_id,
                    driver_name,
                    legacy_driver["id"],
                )
            else:
                await execute_query(
                    "INSERT INTO drivers (chat_id, name) VALUES ($1, $2)",
                    driver_chat_id,
                    driver_name,
                )

            driver_row = await fetch_one("SELECT id FROM drivers WHERE chat_id=$1", driver_chat_id)
        else:
            await execute_query(
                "UPDATE drivers SET name = $1 WHERE id = $2",
                driver_name,
                driver_row["id"],
            )

        driver_id = driver_row["id"]

        await execute_query(
            "INSERT INTO dispatchers (name) VALUES ($1) ON CONFLICT (name) DO NOTHING",
            dispatcher_name,
        )
        dispatcher_row = await fetch_one("SELECT id FROM dispatchers WHERE name=$1", dispatcher_name)
        dispatcher_id = dispatcher_row["id"]

        await execute_query(
            """
            INSERT INTO driver_dispatcher (driver_id, dispatcher_id)
            VALUES ($1, $2) ON CONFLICT (driver_id, dispatcher_id) DO NOTHING
            """,
            driver_id,
            dispatcher_id,
        )

        await execute_query(
            """
            INSERT INTO loads (driver_id, dispatcher_id, broker, load_number, rate, pu_date, del_date)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            driver_id,
            dispatcher_id,
            broker,
            load_number,
            rate,
            pu_date,
            del_date,
        )
        return True, None
    except asyncpg.UniqueViolationError:
        return False, "duplicate"
    except Exception as e:
        return False, str(e)


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def handle_load_message(message: Message):
    text = message.text or ""
    if not text.startswith(MESSAGE_PREFIX):
        return

    driver_name = message.chat.title or "Unknown"
    parsed = parse_load_from_parser(text)

    if not all([parsed["load_number"], parsed["dispatch"], parsed["rate"] is not None]):
        logging.warning("message could not be parsed completely: %s", text)
        return

    success, error = await add_load(
        message.chat.id,
        driver_name,
        parsed["dispatch"],
        parsed.get("broker"),
        parsed["load_number"],
        parsed["rate"],
        parsed.get("pu_date"),
        parsed.get("del_date"),
    )

    if success:
        admin_text = (
            f"✅ Saved load in group '{message.chat.title or 'Unknown'}'\n"
            f"Load: {parsed['load_number']}\n"
            f"Dispatcher: {parsed['dispatch']}\n"
            f"Rate: ${parsed['rate']:.2f}"
        )
        await notify_admins(message.bot, admin_text)
    elif error == "duplicate":
        pending_updates[parsed["load_number"]] = {
            "rate": parsed["rate"],
            "pu_date": parsed.get("pu_date"),
            "del_date": parsed.get("del_date"),
            "broker": parsed.get("broker"),
        }

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Yes ✅", callback_data=f"{YES_CALLBACK}:{parsed['load_number']}"),
                    InlineKeyboardButton(text="No ❌", callback_data=f"{NO_CALLBACK}:{parsed['load_number']}"),
                ]
            ]
        )
        await notify_admins(
            message.bot,
            f"Was the rate changed for load number {parsed['load_number']}?",
            reply_markup=keyboard,
        )
    else:
        await notify_admins(
            message.bot,
            f"❌ Error while saving load in group '{message.chat.title or 'Unknown'}':\n{error}",
        )


@router.callback_query(F.data.startswith(YES_CALLBACK))
@admin_only
async def handle_yes_update(call: CallbackQuery):
    load_number = call.data.split(":")[1]
    update_data = pending_updates.get(load_number)

    if update_data is None:
        await call.answer("Nothing found to update\n@walter_sam", show_alert=True)
        return

    await execute_query(
        """
        UPDATE loads SET rate = $1, pu_date = $2, del_date = $3, broker = $4 WHERE load_number = $5
        """,
        update_data["rate"],
        update_data.get("pu_date"),
        update_data.get("del_date"),
        update_data.get("broker"),
        load_number,
    )

    await call.message.edit_text(f"Load {load_number} updated ✅")
    pending_updates.pop(load_number, None)
    await call.answer()


@router.callback_query(F.data.startswith(NO_CALLBACK))
@admin_only
async def handle_no_update(call: CallbackQuery):
    load_number = call.data.split(":")[1]
    await call.message.edit_text("A load with this load_number already exists ❌")
    pending_updates.pop(load_number, None)
    await call.answer()
