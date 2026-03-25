from functools import wraps
import logging

import asyncpg
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from db.database import execute_query, fetch_all, fetch_one, get_connection
from services.admin import ADMINS, notify_admins
from services.parser import parse_load as parse_load_from_parser

router = Router()

YES_CALLBACK = "update_rate_yes"
NO_CALLBACK = "update_rate_no"
MESSAGE_PREFIX = "\u203c\ufe0f"
CHECK_MARK = chr(0x2705)
CROSS_MARK = chr(0x274C)

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
                await message_or_call.reply(f"{CROSS_MARK} Only admin can use this command")
            elif isinstance(message_or_call, CallbackQuery):
                await message_or_call.answer(f"{CROSS_MARK} Only admin can use this command", show_alert=True)
            return

        return await func(message_or_call, *args, **kwargs)

    return wrapper


async def merge_driver_records(source_id: int, target_id: int) -> tuple[bool, str]:
    if source_id == target_id:
        return False, "Source and target driver IDs must be different"

    conn = await get_connection()
    async with conn.acquire() as connection:
        async with connection.transaction():
            source = await connection.fetchrow(
                "SELECT id, name, chat_id FROM drivers WHERE id = $1",
                source_id,
            )
            target = await connection.fetchrow(
                "SELECT id, name, chat_id FROM drivers WHERE id = $1",
                target_id,
            )

            if source is None:
                return False, f"Driver {source_id} not found"
            if target is None:
                return False, f"Driver {target_id} not found"
            if source["chat_id"] is not None and target["chat_id"] is not None and source["chat_id"] != target["chat_id"]:
                return False, "Drivers have different chat_id values. Merge aborted to avoid mixing two groups"

            keep_chat_id = target["chat_id"] if target["chat_id"] is not None else source["chat_id"]
            keep_name = target["name"] or source["name"]

            await connection.execute(
                "UPDATE drivers SET name = $1, chat_id = $2 WHERE id = $3",
                keep_name,
                keep_chat_id,
                target_id,
            )

            await connection.execute(
                "UPDATE loads SET driver_id = $1 WHERE driver_id = $2",
                target_id,
                source_id,
            )

            await connection.execute(
                """
                INSERT INTO driver_dispatcher (driver_id, dispatcher_id)
                SELECT $1, dispatcher_id
                FROM driver_dispatcher
                WHERE driver_id = $2
                ON CONFLICT (driver_id, dispatcher_id) DO NOTHING
                """,
                target_id,
                source_id,
            )

            await connection.execute("DELETE FROM driver_dispatcher WHERE driver_id = $1", source_id)
            await connection.execute("DELETE FROM drivers WHERE id = $1", source_id)

    return True, f"Driver {source_id} merged into driver {target_id}"


async def merge_dispatcher_records(source_id: int, target_id: int) -> tuple[bool, str]:
    if source_id == target_id:
        return False, "Source and target dispatcher IDs must be different"

    conn = await get_connection()
    async with conn.acquire() as connection:
        async with connection.transaction():
            source = await connection.fetchrow(
                "SELECT id, name, telegram_user_id FROM dispatchers WHERE id = $1",
                source_id,
            )
            target = await connection.fetchrow(
                "SELECT id, name, telegram_user_id FROM dispatchers WHERE id = $1",
                target_id,
            )

            if source is None:
                return False, f"Dispatcher {source_id} not found"
            if target is None:
                return False, f"Dispatcher {target_id} not found"
            if (
                source["telegram_user_id"] is not None
                and target["telegram_user_id"] is not None
                and source["telegram_user_id"] != target["telegram_user_id"]
            ):
                return False, "Dispatchers have different telegram_user_id values. Merge aborted to avoid mixing two users"

            keep_user_id = (
                target["telegram_user_id"]
                if target["telegram_user_id"] is not None
                else source["telegram_user_id"]
            )
            keep_name = target["name"] or source["name"]

            await connection.execute(
                "UPDATE dispatchers SET name = $1, telegram_user_id = $2 WHERE id = $3",
                keep_name,
                keep_user_id,
                target_id,
            )

            await connection.execute(
                "UPDATE loads SET dispatcher_id = $1 WHERE dispatcher_id = $2",
                target_id,
                source_id,
            )

            await connection.execute(
                """
                INSERT INTO driver_dispatcher (driver_id, dispatcher_id)
                SELECT driver_id, $1
                FROM driver_dispatcher
                WHERE dispatcher_id = $2
                ON CONFLICT (driver_id, dispatcher_id) DO NOTHING
                """,
                target_id,
                source_id,
            )

            await connection.execute("DELETE FROM driver_dispatcher WHERE dispatcher_id = $1", source_id)
            await connection.execute("DELETE FROM dispatchers WHERE id = $1", source_id)

    return True, f"Dispatcher {source_id} merged into dispatcher {target_id}"


@router.message(Command("drivers_db"))
@admin_only
async def command_drivers_db(message: Message):
    rows = await fetch_all(
        """
        SELECT
            d.id,
            d.name,
            d.chat_id,
            COUNT(l.id) AS loads_count
        FROM drivers d
        LEFT JOIN loads l ON l.driver_id = d.id
        GROUP BY d.id, d.name, d.chat_id
        ORDER BY d.name NULLS LAST, d.id
        """
    )
    if not rows:
        await message.reply("No drivers found")
        return

    lines = ["Drivers in DB:"]
    for row in rows:
        lines.append(
            f"ID {row['id']} | {row['name'] or 'Unknown'} | chat_id: {row['chat_id'] or 'NULL'} | loads: {row['loads_count']}"
        )
    await message.reply("\n".join(lines))


@router.message(Command("dispatchers_db"))
@admin_only
async def command_dispatchers_db(message: Message):
    rows = await fetch_all(
        """
        SELECT
            d.id,
            d.name,
            d.telegram_user_id,
            COUNT(l.id) AS loads_count
        FROM dispatchers d
        LEFT JOIN loads l ON l.dispatcher_id = d.id
        GROUP BY d.id, d.name, d.telegram_user_id
        ORDER BY d.name NULLS LAST, d.id
        """
    )
    if not rows:
        await message.reply("No dispatchers found")
        return

    lines = ["Dispatchers in DB:"]
    for row in rows:
        lines.append(
            f"ID {row['id']} | {row['name'] or 'Unknown'} | user_id: {row['telegram_user_id'] or 'NULL'} | loads: {row['loads_count']}"
        )
    await message.reply("\n".join(lines))


@router.message(Command("merge_driver"))
@admin_only
async def command_merge_driver(message: Message):
    parts = (message.text or "").split()
    if len(parts) != 3:
        await message.reply("Usage: /merge_driver <duplicate_id> <keep_id>")
        return

    try:
        source_id = int(parts[1])
        target_id = int(parts[2])
    except ValueError:
        await message.reply("Driver IDs must be numbers")
        return

    success, text = await merge_driver_records(source_id, target_id)
    await message.reply(f"{CHECK_MARK if success else CROSS_MARK} {text}")


@router.message(Command("merge_dispatcher"))
@admin_only
async def command_merge_dispatcher(message: Message):
    parts = (message.text or "").split()
    if len(parts) != 3:
        await message.reply("Usage: /merge_dispatcher <duplicate_id> <keep_id>")
        return

    try:
        source_id = int(parts[1])
        target_id = int(parts[2])
    except ValueError:
        await message.reply("Dispatcher IDs must be numbers")
        return

    success, text = await merge_dispatcher_records(source_id, target_id)
    await message.reply(f"{CHECK_MARK if success else CROSS_MARK} {text}")


async def add_load(
    driver_chat_id,
    driver_name,
    dispatcher_user_id,
    dispatcher_name,
    broker,
    load_number,
    rate,
    pu_date=None,
    del_date=None,
):
    try:
        driver_row = await fetch_one("SELECT id FROM drivers WHERE chat_id = $1", driver_chat_id)
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

            driver_row = await fetch_one("SELECT id FROM drivers WHERE chat_id = $1", driver_chat_id)
        else:
            await execute_query(
                "UPDATE drivers SET name = $1 WHERE id = $2",
                driver_name,
                driver_row["id"],
            )

        driver_id = driver_row["id"]

        dispatcher_row = await fetch_one(
            "SELECT id FROM dispatchers WHERE telegram_user_id = $1",
            dispatcher_user_id,
        )
        if dispatcher_row is None:
            legacy_dispatcher = await fetch_one(
                """
                SELECT id
                FROM dispatchers
                WHERE telegram_user_id IS NULL AND name = $1
                ORDER BY id
                LIMIT 1
                """,
                dispatcher_name,
            )
            if legacy_dispatcher is not None:
                await execute_query(
                    "UPDATE dispatchers SET telegram_user_id = $1, name = $2 WHERE id = $3",
                    dispatcher_user_id,
                    dispatcher_name,
                    legacy_dispatcher["id"],
                )
            else:
                await execute_query(
                    "INSERT INTO dispatchers (telegram_user_id, name) VALUES ($1, $2)",
                    dispatcher_user_id,
                    dispatcher_name,
                )

            dispatcher_row = await fetch_one(
                "SELECT id FROM dispatchers WHERE telegram_user_id = $1",
                dispatcher_user_id,
            )
        else:
            await execute_query(
                "UPDATE dispatchers SET name = $1 WHERE id = $2",
                dispatcher_name,
                dispatcher_row["id"],
            )

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
    except Exception as exc:
        return False, str(exc)


async def notify_dispatcher_saved_load(message: Message, parsed: dict):
    dispatcher_text = (
        f"{CHECK_MARK} Load saved\n"
        f"Driver: {message.chat.title or 'Unknown'}\n"
        f"Load: {parsed['load_number']}\n"
        f"Rate: ${parsed['rate']:.2f}"
    )
    try:
        await message.bot.send_message(message.from_user.id, dispatcher_text)
    except Exception:
        logging.warning("could not send save notification to dispatcher %s", message.from_user.id)


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
        message.from_user.id,
        parsed["dispatch"],
        parsed.get("broker"),
        parsed["load_number"],
        parsed["rate"],
        parsed.get("pu_date"),
        parsed.get("del_date"),
    )

    if success:
        await notify_dispatcher_saved_load(message, parsed)

        admin_text = (
            f"{CHECK_MARK} Saved load in group '{message.chat.title or 'Unknown'}'\n"
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
                    InlineKeyboardButton(text=f"Yes {CHECK_MARK}", callback_data=f"{YES_CALLBACK}:{parsed['load_number']}"),
                    InlineKeyboardButton(text=f"No {CROSS_MARK}", callback_data=f"{NO_CALLBACK}:{parsed['load_number']}"),
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
            f"{CROSS_MARK} Error while saving load in group '{message.chat.title or 'Unknown'}':\n{error}",
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

    await call.message.edit_text(f"Load {load_number} updated {CHECK_MARK}")
    pending_updates.pop(load_number, None)
    await call.answer()


@router.callback_query(F.data.startswith(NO_CALLBACK))
@admin_only
async def handle_no_update(call: CallbackQuery):
    load_number = call.data.split(":")[1]
    await call.message.edit_text(f"A load with this load_number already exists {CROSS_MARK}")
    pending_updates.pop(load_number, None)
    await call.answer()
