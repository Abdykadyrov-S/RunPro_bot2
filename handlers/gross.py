from datetime import datetime, timedelta
import io
import logging
import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.types.input_file import BufferedInputFile
from openpyxl import Workbook

from db.database import fetch_all, fetch_one
from keyboards.main import main_menu
from services.admin import ADMINS, suppress_group

router = Router()
logger = logging.getLogger(__name__)

EMOJI_DRIVER = chr(0x1F468) + chr(0x200D) + chr(0x2708) + chr(0xFE0F)
EMOJI_DISPATCHER = chr(0x1F4CB)
EMOJI_CALENDAR = chr(0x1F4C5)
EMOJI_MEMO = chr(0x1F4DD)
EMOJI_MONEY = chr(0x1F4B0)
EMOJI_TRUCK = chr(0x1F69A)
EMOJI_CHART = chr(0x1F4CA)
EMOJI_CARD = chr(0x1F4C7)
BACK_LABEL = chr(0x25C0) + chr(0xFE0F) + " Back"
ARROW = chr(0x2192)
CROSS_MARK = chr(0x274C)


class SelectionState(StatesGroup):
    waiting_for_driver = State()
    waiting_for_dispatcher = State()
    waiting_for_period_type = State()
    waiting_for_custom_date_range = State()


def safe_sheet_title(title: str) -> str:
    forbidden = ["/", "\\", "?", "*", "[", "]"]
    for ch in forbidden:
        title = title.replace(ch, "_")
    return title[:31]


def normalize_date(date_str: str) -> str | None:
    if not date_str:
        return None

    parts = date_str.strip().split("/")
    if len(parts) != 3:
        return None

    try:
        month, day, year = parts
        if len(year) == 2:
            year = "20" + year
        return f"{month.lstrip('0')}/{day.lstrip('0')}/{year}"
    except Exception:
        return None


def parse_date_range(date_range_str: str) -> tuple[str, str] | None:
    if not date_range_str:
        return None

    match = re.match(r"(\d{1,2}/\d{1,2}/\d{2,4})\s*-\s*(\d{1,2}/\d{1,2}/\d{2,4})", date_range_str.strip())
    if not match:
        return None

    start_date = normalize_date(match.group(1))
    end_date = normalize_date(match.group(2))
    if start_date and end_date:
        return start_date, end_date
    return None


def dates_in_range(date_str: str, start_date: str, end_date: str) -> bool:
    if not date_str:
        return False

    try:
        date = datetime.strptime(date_str, "%m/%d/%Y")
        start = datetime.strptime(start_date, "%m/%d/%Y")
        end = datetime.strptime(end_date, "%m/%d/%Y")
        return start <= date <= end
    except Exception as exc:
        logger.error("dates_in_range error: %s, %s, %s - %s", date_str, start_date, end_date, exc)
        return False


def format_date(date_obj: datetime) -> str:
    formatted = date_obj.strftime("%m/%d/%Y")
    month, day, year = formatted.split("/")
    return f"{int(month)}/{int(day)}/{year}"


def get_week_start_end() -> tuple[str, str]:
    today = datetime.now()
    current_weekday = today.weekday()
    if current_weekday == 0:
        tuesday = today - timedelta(days=6)
        monday = today
    else:
        tuesday = today - timedelta(days=(current_weekday - 1))
        monday = tuesday + timedelta(days=6)
    return format_date(tuesday), format_date(monday)


def get_last_week_start_end() -> tuple[str, str]:
    tuesday, monday = get_week_start_end()
    tuesday_dt = datetime.strptime(tuesday, "%m/%d/%Y") - timedelta(days=7)
    monday_dt = datetime.strptime(monday, "%m/%d/%Y") - timedelta(days=7)
    return format_date(tuesday_dt), format_date(monday_dt)


def get_period_dates(period: str) -> tuple[str, str] | None:
    today = datetime.now()

    if period == "this_week":
        return get_week_start_end()
    if period == "last_week":
        return get_last_week_start_end()
    if period == "this_month":
        first_day = today.replace(day=1)
        if today.month == 12:
            last_day = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last_day = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        return format_date(first_day), format_date(last_day)
    if period == "this_quarter":
        quarter = (today.month - 1) // 3 + 1
        first_month = (quarter - 1) * 3 + 1
        first_day = today.replace(month=first_month, day=1)
        if quarter == 4:
            last_day = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last_day = today.replace(month=first_month + 3, day=1) - timedelta(days=1)
        return format_date(first_day), format_date(last_day)
    if period == "this_year":
        return format_date(today.replace(month=1, day=1)), format_date(today.replace(month=12, day=31))

    return None


def create_period_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{EMOJI_CALENDAR} All Time", callback_data="period:all_time")],
            [InlineKeyboardButton(text=f"{EMOJI_CHART} This Week (Tue-Mon)", callback_data="period:this_week")],
            [InlineKeyboardButton(text=f"{chr(0x23EE)}{chr(0xFE0F)} Last Week", callback_data="period:last_week")],
            [InlineKeyboardButton(text=f"{chr(0x1F4C8)} This Month", callback_data="period:this_month")],
            [InlineKeyboardButton(text=f"{chr(0x1F4C9)} This Quarter", callback_data="period:this_quarter")],
            [InlineKeyboardButton(text=f"{chr(0x1F4C6)} This Year", callback_data="period:this_year")],
            [InlineKeyboardButton(text=f"{chr(0x1F527)} Custom Range", callback_data="period:custom")],
            [InlineKeyboardButton(text=BACK_LABEL, callback_data="back_to_menu")],
        ]
    )


def create_driver_keyboard(drivers: list[dict]) -> InlineKeyboardMarkup:
    keyboard = []
    for driver in drivers:
        driver_name = driver["name"] or f"Driver #{driver['id']}"
        keyboard.append([InlineKeyboardButton(text=f"{EMOJI_DRIVER} {driver_name}", callback_data=f"driver:{driver['id']}")])
    keyboard.append([InlineKeyboardButton(text=BACK_LABEL, callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_dispatcher_keyboard(dispatchers: list[dict]) -> InlineKeyboardMarkup:
    keyboard = []
    for dispatcher in dispatchers:
        dispatcher_name = dispatcher["name"] or f"Dispatcher #{dispatcher['id']}"
        keyboard.append(
            [InlineKeyboardButton(text=f"{EMOJI_DISPATCHER} {dispatcher_name}", callback_data=f"dispatcher:{dispatcher['id']}")]
        )
    keyboard.append([InlineKeyboardButton(text=BACK_LABEL, callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def get_dispatcher_by_user_id(user_id: int):
    return await fetch_one(
        """
        SELECT id, name
        FROM dispatchers
        WHERE telegram_user_id = $1
        LIMIT 1
        """,
        user_id,
    )


async def can_view_driver_gross(user_id: int) -> bool:
    if user_id in ADMINS:
        return True
    dispatcher_row = await get_dispatcher_by_user_id(user_id)
    return dispatcher_row is not None


async def gross_by_driver(driver_id, start_date=None, end_date=None):
    total_rate, _ = await gross_totals_by_driver(driver_id, start_date, end_date)
    return total_rate


async def gross_totals_by_driver(driver_id, start_date=None, end_date=None):
    if start_date and end_date:
        rows = await fetch_all(
            """
            SELECT rate, miles, del_date
            FROM loads
            WHERE driver_id = $1
            """,
            driver_id,
        )
        total_rate = 0
        total_miles = 0
        for row in rows:
            if dates_in_range(row["del_date"], start_date, end_date):
                total_rate += row["rate"] or 0
                total_miles += row["miles"] or 0
        return round(total_rate, 2), round(total_miles, 2)

    result = await fetch_one(
        """
        SELECT SUM(rate) AS total_rate, SUM(miles) AS total_miles
        FROM loads
        WHERE driver_id = $1
        """,
        driver_id,
    )
    return round(result["total_rate"] or 0, 2), round(result["total_miles"] or 0, 2)


async def gross_by_dispatcher(dispatcher_id, start_date=None, end_date=None):
    total_rate, _ = await gross_totals_by_dispatcher(dispatcher_id, start_date, end_date)
    return total_rate


async def gross_totals_by_dispatcher(dispatcher_id, start_date=None, end_date=None):
    if start_date and end_date:
        rows = await fetch_all(
            """
            SELECT rate, miles, del_date
            FROM loads
            WHERE dispatcher_id = $1
            """,
            dispatcher_id,
        )
        total_rate = 0
        total_miles = 0
        for row in rows:
            if dates_in_range(row["del_date"], start_date, end_date):
                total_rate += row["rate"] or 0
                total_miles += row["miles"] or 0
        return round(total_rate, 2), round(total_miles, 2)

    result = await fetch_one(
        """
        SELECT SUM(rate) AS total_rate, SUM(miles) AS total_miles
        FROM loads
        WHERE dispatcher_id = $1
        """,
        dispatcher_id,
    )
    return round(result["total_rate"] or 0, 2), round(result["total_miles"] or 0, 2)


async def export_driver_to_excel(driver_id, driver_name, start_date=None, end_date=None):
    rows = await fetch_all(
        """
        SELECT
            d.name AS driver,
            ds.name AS dispatcher,
            l.broker,
            l.load_number,
            l.rate,
            l.miles,
            l.pu_date,
            l.del_date
        FROM loads l
        JOIN drivers d ON l.driver_id = d.id
        JOIN dispatchers ds ON l.dispatcher_id = ds.id
        WHERE l.driver_id = $1
        """,
        driver_id,
    )

    wb = Workbook()
    ws = wb.active
    ws.title = safe_sheet_title(driver_name)
    ws.append(["Driver", "Dispatcher", "Broker", "Load Number", "Rate", "Miles", "PU Date", "DEL Date"])

    total_rate = 0
    total_miles = 0
    for row in rows:
        if start_date and end_date and not dates_in_range(row["del_date"], start_date, end_date):
            continue
        ws.append(
            [
                row["driver"],
                row["dispatcher"],
                row["broker"],
                row["load_number"],
                row["rate"],
                row["miles"],
                row["pu_date"],
                row["del_date"],
            ]
        )
        total_rate += row["rate"] or 0
        total_miles += row["miles"] or 0

    ws.append([])
    ws.append(["", "", "", "TOTAL", round(total_rate, 2), round(total_miles, 2), "", ""])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"driver_{driver_name}_{start_date}_to_{end_date}.xlsx" if start_date and end_date else f"driver_{driver_name}.xlsx"
    return buffer, filename


async def export_dispatcher_to_excel(dispatcher_id, dispatcher_name, start_date=None, end_date=None):
    rows = await fetch_all(
        """
        SELECT
            d.name AS driver,
            ds.name AS dispatcher,
            l.broker,
            l.load_number,
            l.rate,
            l.miles,
            l.pu_date,
            l.del_date
        FROM loads l
        JOIN drivers d ON l.driver_id = d.id
        JOIN dispatchers ds ON l.dispatcher_id = ds.id
        WHERE l.dispatcher_id = $1
        """,
        dispatcher_id,
    )

    wb = Workbook()
    ws = wb.active
    ws.title = safe_sheet_title(dispatcher_name)
    ws.append(["Driver", "Dispatcher", "Broker", "Load Number", "Rate", "Miles", "PU Date", "DEL Date"])

    total_rate = 0
    total_miles = 0
    for row in rows:
        if start_date and end_date and not dates_in_range(row["del_date"], start_date, end_date):
            continue
        ws.append(
            [
                row["driver"],
                row["dispatcher"],
                row["broker"],
                row["load_number"],
                row["rate"],
                row["miles"],
                row["pu_date"],
                row["del_date"],
            ]
        )
        total_rate += row["rate"] or 0
        total_miles += row["miles"] or 0

    ws.append([])
    ws.append(["", "", "", "TOTAL", round(total_rate, 2), round(total_miles, 2), "", ""])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = (
        f"dispatcher_{dispatcher_name}_{start_date}_to_{end_date}.xlsx"
        if start_date and end_date
        else f"dispatcher_{dispatcher_name}.xlsx"
    )
    return buffer, filename


async def get_all_drivers() -> list[dict]:
    rows = await fetch_all("SELECT id, name, chat_id FROM drivers ORDER BY name, id")
    return [{"id": row["id"], "name": row["name"], "chat_id": row["chat_id"]} for row in rows]


async def get_all_dispatchers() -> list[dict]:
    rows = await fetch_all("SELECT id, name, telegram_user_id FROM dispatchers ORDER BY name, id")
    return [{"id": row["id"], "name": row["name"], "telegram_user_id": row["telegram_user_id"]} for row in rows]


async def send_gross_document(
    target_message: Message,
    requester_user_id: int,
    entity_type: str,
    entity_name: str,
    entity_id: int,
    start_date=None,
    end_date=None,
    period_text="All Time",
):
    if entity_type == "driver" and not await can_view_driver_gross(requester_user_id):
        await target_message.answer(
            f"{CROSS_MARK} Only dispatcher or admin can view driver gross",
            reply_markup=main_menu,
        )
        return

    if entity_type == "driver":
        total, total_miles = await gross_totals_by_driver(entity_id, start_date, end_date)
        buffer, filename = await export_driver_to_excel(entity_id, entity_name, start_date, end_date)
        emoji = EMOJI_TRUCK
        label = "DRIVER"
    else:
        total, total_miles = await gross_totals_by_dispatcher(entity_id, start_date, end_date)
        buffer, filename = await export_dispatcher_to_excel(entity_id, entity_name, start_date, end_date)
        emoji = EMOJI_CHART
        label = "DISPATCHER"

    file = BufferedInputFile(buffer.getvalue(), filename=filename)
    caption = (
        f"{emoji} *Gross {label}*\n"
        f"{EMOJI_CARD} {entity_name}\n\n"
        f"{EMOJI_CALENDAR} {period_text}\n\n"
        f"{EMOJI_MONEY} *TOTAL: ${total:.2f}*\n"
        f"{EMOJI_TRUCK} *TOTAL MILES: {total_miles:.2f}*"
    )
    await target_message.answer_document(file, caption=caption, parse_mode="Markdown", reply_markup=main_menu)


@router.message(Command("gross_driver"))
@suppress_group
async def command_gross_driver(message: Message, state: FSMContext):
    if not await can_view_driver_gross(message.from_user.id):
        await message.reply(
            f"{CROSS_MARK} Only dispatcher or admin can view driver gross",
            reply_markup=main_menu,
        )
        return

    drivers = await get_all_drivers()
    if not drivers:
        await message.reply(f"{CROSS_MARK} No drivers found in database", reply_markup=main_menu)
        return

    await state.set_state(SelectionState.waiting_for_period_type)
    await state.update_data(entity_type="driver")
    await message.reply(f"{EMOJI_DRIVER} Select a driver:", reply_markup=create_driver_keyboard(drivers))


@router.message(Command("gross_dispatcher"))
@suppress_group
async def command_gross_dispatcher(message: Message, state: FSMContext):
    if message.from_user.id in ADMINS:
        dispatchers = await get_all_dispatchers()
        if not dispatchers:
            await message.reply(f"{CROSS_MARK} No dispatchers found in database", reply_markup=main_menu)
            return

        await state.set_state(SelectionState.waiting_for_period_type)
        await state.update_data(entity_type="dispatcher")
        await message.reply(f"{EMOJI_DISPATCHER} Select a dispatcher:", reply_markup=create_dispatcher_keyboard(dispatchers))
        return

    dispatcher_row = await get_dispatcher_by_user_id(message.from_user.id)
    if not dispatcher_row:
        await message.reply(
            f"{CROSS_MARK} Your dispatcher profile was not found. Send at least one load first so the bot can bind your Telegram account.",
            reply_markup=main_menu,
        )
        return

    dispatcher_name = dispatcher_row["name"] or f"Dispatcher #{dispatcher_row['id']}"
    await state.set_state(SelectionState.waiting_for_period_type)
    await state.update_data(
        entity_type="dispatcher",
        driver_or_dispatcher=dispatcher_name,
        dispatcher_id=dispatcher_row["id"],
    )
    await message.reply(
        f"{EMOJI_DISPATCHER} *{dispatcher_name}*\n\n{EMOJI_CALENDAR} Select period:",
        parse_mode="Markdown",
        reply_markup=create_period_keyboard(),
    )


@router.callback_query(F.data.startswith("driver:"))
@suppress_group
async def select_driver_callback(callback: CallbackQuery, state: FSMContext):
    if not await can_view_driver_gross(callback.from_user.id):
        await callback.answer(f"{CROSS_MARK} Only dispatcher or admin can view driver gross", show_alert=True)
        await state.clear()
        return

    driver_id = int(callback.data.split(":", 1)[1])
    driver_row = await fetch_one("SELECT id, name FROM drivers WHERE id = $1", driver_id)
    if not driver_row:
        await callback.answer(f"{CROSS_MARK} Driver not found", show_alert=True)
        return

    driver_name = driver_row["name"] or f"Driver #{driver_row['id']}"
    await state.update_data(driver_or_dispatcher=driver_name, driver_id=driver_id)
    await callback.message.delete()
    await callback.message.answer(
        f"{EMOJI_DRIVER} *{driver_name}*\n\n{EMOJI_CALENDAR} Select period:",
        parse_mode="Markdown",
        reply_markup=create_period_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dispatcher:"))
@suppress_group
async def select_dispatcher_callback(callback: CallbackQuery, state: FSMContext):
    dispatcher_id = int(callback.data.split(":", 1)[1])
    if callback.from_user.id not in ADMINS:
        dispatcher_row = await get_dispatcher_by_user_id(callback.from_user.id)
        if not dispatcher_row:
            await callback.answer(
                f"{CROSS_MARK} Your dispatcher profile was not found",
                show_alert=True,
            )
            await state.clear()
            return
        if dispatcher_row["id"] != dispatcher_id:
            await callback.answer(
                f"{CROSS_MARK} You can only view your own dispatcher gross",
                show_alert=True,
            )
            return

    dispatcher_row = await fetch_one("SELECT id, name FROM dispatchers WHERE id = $1", dispatcher_id)
    if not dispatcher_row:
        await callback.answer(f"{CROSS_MARK} Dispatcher not found", show_alert=True)
        return

    dispatcher_name = dispatcher_row["name"] or f"Dispatcher #{dispatcher_row['id']}"
    await state.update_data(driver_or_dispatcher=dispatcher_name, dispatcher_id=dispatcher_id)
    await callback.message.delete()
    await callback.message.answer(
        f"{EMOJI_DISPATCHER} *{dispatcher_name}*\n\n{EMOJI_CALENDAR} Select period:",
        parse_mode="Markdown",
        reply_markup=create_period_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("period:"))
@suppress_group
async def select_period_callback(callback: CallbackQuery, state: FSMContext):
    period = callback.data.split(":", 1)[1]
    data = await state.get_data()

    entity_type = data.get("entity_type")
    name = data.get("driver_or_dispatcher")
    driver_id = data.get("driver_id")
    dispatcher_id = data.get("dispatcher_id")

    if not name or not entity_type:
        await callback.answer(f"{CROSS_MARK} Error: missing selection", show_alert=True)
        return

    if period == "custom":
        await callback.message.edit_text(f"{EMOJI_MEMO} Enter date range in format: *2/24/26-3/2/26*", parse_mode="Markdown")
        await state.set_state(SelectionState.waiting_for_custom_date_range)
        return

    start_date, end_date = get_period_dates(period) or (None, None)

    if period == "all_time":
        period_text = "All Time"
    elif period == "this_week":
        period_text = f"This Week (Tue-Mon)\n{start_date} {ARROW} {end_date}"
    elif period == "last_week":
        period_text = f"Last Week (Tue-Mon)\n{start_date} {ARROW} {end_date}"
    elif period == "this_month":
        period_text = f"This Month\n{start_date} {ARROW} {end_date}"
    elif period == "this_quarter":
        period_text = f"This Quarter\n{start_date} {ARROW} {end_date}"
    elif period == "this_year":
        period_text = f"This Year\n{start_date} {ARROW} {end_date}"
    else:
        period_text = "Custom"

    try:
        await callback.message.delete()
        entity_id = driver_id if entity_type == "driver" else dispatcher_id
        await send_gross_document(
            callback.message,
            callback.from_user.id,
            entity_type,
            name,
            entity_id,
            start_date,
            end_date,
            period_text,
        )
        await state.clear()
    except Exception as exc:
        await state.clear()
        await callback.answer(f"{CROSS_MARK} Error: {str(exc)}", show_alert=True)
        logger.exception("Error exporting %s: %s", entity_type, name)


@router.message(SelectionState.waiting_for_custom_date_range)
@suppress_group
async def handle_custom_date_range(message: Message, state: FSMContext):
    date_range_str = message.text or ""
    date_range = parse_date_range(date_range_str)
    if not date_range:
        await message.reply(f"{CROSS_MARK} Invalid date format. Use: 2/24/26-3/2/26 or 2/24/2026-3/2/2026")
        return

    data = await state.get_data()
    entity_type = data.get("entity_type")
    name = data.get("driver_or_dispatcher")
    driver_id = data.get("driver_id")
    dispatcher_id = data.get("dispatcher_id")
    start_date, end_date = date_range

    try:
        entity_id = driver_id if entity_type == "driver" else dispatcher_id
        await send_gross_document(
            message,
            message.from_user.id,
            entity_type,
            name,
            entity_id,
            start_date,
            end_date,
            f"Custom Range\n{start_date} {ARROW} {end_date}",
        )
        await state.clear()
    except Exception as exc:
        await state.clear()
        await message.reply(f"{CROSS_MARK} Error: {str(exc)}", reply_markup=main_menu)
        logger.exception("Error exporting custom range %s: %s", entity_type, name)


@router.callback_query(F.data == "back_to_menu")
@suppress_group
async def back_to_menu_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("Main menu:", reply_markup=main_menu)
    await callback.answer()
