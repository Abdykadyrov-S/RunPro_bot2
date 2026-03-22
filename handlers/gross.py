from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types.input_file import BufferedInputFile
from db.database import fetch_all, fetch_one, execute_query
from keyboards.main import get_dispatchers_keyboard, get_drivers_keyboard, get_export_keyboard, main_menu
from services.admin import suppress_group
import io
from openpyxl import Workbook
from datetime import datetime, timedelta
import re
import logging

router = Router()
logger = logging.getLogger(__name__)


class SelectionState(StatesGroup):
    waiting_for_driver = State()
    waiting_for_dispatcher = State()
    waiting_for_period_type = State()
    waiting_for_custom_date_range = State()


def safe_sheet_title(title: str) -> str:
    """Очистить название листа от запрещенных символов"""
    forbidden = ['/', '\\', '?', '*', '[', ']']
    for ch in forbidden:
        title = title.replace(ch, '_')
    return title[:31]


def normalize_date(date_str: str) -> str | None:
    """
    Преобразует дату из формата M/D/YY или M/D/YYYY в формат M/D/YYYY
    Например: 2/24/26 -> 2/24/2026
    """
    if not date_str:
        return None
    
    parts = date_str.strip().split('/')
    if len(parts) != 3:
        return None
    
    try:
        month, day, year = parts
        # Если год двузначный, добавляем 20
        if len(year) == 2:
            year = '20' + year
        return f"{month.lstrip('0')}/{day.lstrip('0')}/{year}"
    except:
        return None


def parse_date_range(date_range_str: str) -> tuple[str, str] | None:
    """
    Парсит диапазон дат в формате М/D/YY-M/D/YY или М/D/YYYY-M/D/YYYY
    Возвращает кортеж (start_date, end_date) в формате M/D/YYYY
    Например: "2/24/26-3/2/26" -> ("2/24/2026", "3/2/2026")
    """
    if not date_range_str:
        return None
    
    # Извлекаем две даты из строки
    match = re.match(r'(\d{1,2}/\d{1,2}/\d{2,4})\s*-\s*(\d{1,2}/\d{1,2}/\d{2,4})', date_range_str.strip())
    if not match:
        return None
    
    start_date = normalize_date(match.group(1))
    end_date = normalize_date(match.group(2))
    
    if start_date and end_date:
        return (start_date, end_date)
    return None


def dates_in_range(date_str: str, start_date: str, end_date: str) -> bool:
    """
    Проверяет, находится ли дата в диапазоне между start_date и end_date
    Все даты в формате M/D/YYYY
    """
    if not date_str:
        return False
    
    try:
        # Парсим даты
        date = datetime.strptime(date_str, "%m/%d/%Y")
        start = datetime.strptime(start_date, "%m/%d/%Y")
        end = datetime.strptime(end_date, "%m/%d/%Y")
        
        result = start <= date <= end
        logger.debug(f"dates_in_range: {date_str} in [{start_date}, {end_date}] = {result}")
        return result
    except Exception as e:
        logger.error(f"dates_in_range error: {date_str}, {start_date}, {end_date} - {e}")
        return False


def get_week_start_end() -> tuple[str, str]:
    """
    Получить дни текущей недели (с Вторника по Понедельник)
    Возвращает (tuesday, monday) в формате M/D/YYYY
    """
    today = datetime.now()
    current_weekday = today.weekday()  # 0=понедельник,6=воскресенье
    if current_weekday == 0:
        # понедельник: неделя заканчивается сегодня
        tuesday = today - timedelta(days=6)
        monday = today
    else:
        tuesday = today - timedelta(days=(current_weekday - 1))
        monday = tuesday + timedelta(days=6)
    return (format_date(tuesday), format_date(monday))


def get_last_week_start_end() -> tuple[str, str]:
    """
    Получить даты прошлой недели (с Вторника по Понедельник)
    """
    tuesday, monday = get_week_start_end()
    # преобразуем обратно в datetime
    t_dt = datetime.strptime(tuesday, "%m/%d/%Y") - timedelta(days=7)
    m_dt = datetime.strptime(monday, "%m/%d/%Y") - timedelta(days=7)
    return (format_date(t_dt), format_date(m_dt))


def format_date(date_obj: datetime) -> str:
    """Форматировать дату в M/D/YYYY (кроссплатформенный способ)"""
    formatted = date_obj.strftime("%m/%d/%Y")
    # Убираем ведущие нули: 02/25/2026 -> 2/25/2026
    parts = formatted.split('/')
    return f"{int(parts[0])}/{int(parts[1])}/{parts[2]}"


def get_period_dates(period: str) -> tuple[str, str] | None:
    """
    Получить диапазон дат для периода
    period: 'all_time', 'this_week', 'last_week', 'this_month', 'this_quarter', 'this_year'
    Возвращает (start_date, end_date) в формате M/D/YYYY или None
    """
    today = datetime.now()
    
    if period == "this_week":
        return get_week_start_end()
    
    elif period == "last_week":
        return get_last_week_start_end()
    
    elif period == "this_month":
        first_day = today.replace(day=1)
        if today.month == 12:
            last_day = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last_day = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        return (format_date(first_day), format_date(last_day))
    
    elif period == "this_quarter":
        quarter = (today.month - 1) // 3 + 1
        first_month = (quarter - 1) * 3 + 1
        first_day = today.replace(month=first_month, day=1)
        
        if quarter == 4:
            last_day = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last_day = today.replace(month=first_month + 3, day=1) - timedelta(days=1)
        
        return (format_date(first_day), format_date(last_day))
    
    elif period == "this_year":
        first_day = today.replace(month=1, day=1)
        last_day = today.replace(month=12, day=31)
        return (format_date(first_day), format_date(last_day))
    
    return None


async def gross_by_driver(driver_name, start_date=None, end_date=None):
    """
    Если start_date и end_date не указаны, возвращает общую сумму
    Если указаны, фильтрует по диапазону дат del_date
    """
    if start_date and end_date:
        # Получаем все грузы водителя с датами
        rows = await fetch_all("""
            SELECT rate, del_date
            FROM loads l
            JOIN drivers d ON l.driver_id = d.id
            WHERE d.name = $1
        """, driver_name)
        
        total = 0
        for row in rows:
            if dates_in_range(row['del_date'], start_date, end_date):
                total += row['rate'] or 0
        return round(total, 2)
    else:
        result = await fetch_one("""
            SELECT SUM(rate)
            FROM loads l
            JOIN drivers d ON l.driver_id = d.id
            WHERE d.name = $1
        """, driver_name)
        return round(result['sum'] or 0, 2)


async def gross_by_dispatcher(dispatcher_name, start_date=None, end_date=None):
    """
    Если start_date и end_date не указаны, возвращает общую сумму
    Если указаны, фильтрует по диапазону дат del_date
    """
    if start_date and end_date:
        # Получаем все грузы диспетчера с датами
        rows = await fetch_all("""
            SELECT rate, del_date
            FROM loads l
            JOIN dispatchers ds ON l.dispatcher_id = ds.id
            WHERE ds.name = $1
        """, dispatcher_name)
        
        total = 0
        for row in rows:
            if dates_in_range(row['del_date'], start_date, end_date):
                total += row['rate'] or 0
        return round(total, 2)
    else:
        result = await fetch_one("""
            SELECT SUM(rate)
            FROM loads l
            JOIN dispatchers ds ON l.dispatcher_id = ds.id
            WHERE ds.name = $1
        """, dispatcher_name)
        return round(result['sum'] or 0, 2)


async def export_driver_to_excel(driver_name, start_date=None, end_date=None):
    """Экспортировать данные водителя в Excel с опциональной фильтрацией по датам"""
    rows = await fetch_all("""
        SELECT
            d.name AS driver,
            ds.name AS dispatcher,
            l.broker,
            l.load_number,
            l.rate,
            l.pu_date,
            l.del_date
        FROM loads l
        JOIN drivers d ON l.driver_id = d.id
        JOIN dispatchers ds ON l.dispatcher_id = ds.id
        WHERE d.name = $1
    """, driver_name)

    wb = Workbook()
    ws = wb.active
    sheet_name = safe_sheet_title(driver_name)
    ws.title = sheet_name

    ws.append(["Driver", "Dispatcher", "Broker", "Load Number", "Rate", "PU Date", "DEL Date"])

    total = 0
    for row in rows:
        pu_date = row['pu_date']
        del_date = row['del_date']
        # Фильтруем по датам если они указаны
        if start_date and end_date:
            if not dates_in_range(del_date, start_date, end_date):
                continue
        
        ws.append([row['driver'], row['dispatcher'], row['broker'], row['load_number'], row['rate'], row['pu_date'], row['del_date']])
        total += row['rate'] or 0

    ws.append([])
    ws.append(["", "", "", "TOTAL", round(total, 2), "", ""])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    # Формируем имя файла с датами если они есть
    if start_date and end_date:
        filename = f"driver_{driver_name}_{start_date}_to_{end_date}.xlsx"
    else:
        filename = f"driver_{driver_name}.xlsx"

    return buffer, filename


async def export_dispatcher_to_excel(dispatcher_name, start_date=None, end_date=None):
    """Экспортировать данные диспетчера в Excel с опциональной фильтрацией по датам"""
    rows = await fetch_all("""
        SELECT 
            d.name AS driver,
            ds.name AS dispatcher,
            l.broker,
            l.load_number,
            l.rate,
            l.pu_date,
            l.del_date
        FROM loads l
        JOIN drivers d ON l.driver_id = d.id
        JOIN dispatchers ds ON l.dispatcher_id = ds.id
        WHERE ds.name = $1
    """, dispatcher_name)

    wb = Workbook()
    ws = wb.active
    sheet_name = safe_sheet_title(dispatcher_name)
    ws.title = sheet_name

    ws.append(["Driver", "Dispatcher", "Broker", "Load Number", "Rate", "PU Date", "DEL Date"])

    total = 0
    for row in rows:
        pu_date = row['pu_date']
        del_date = row['del_date']
        # Фильтруем по датам если они указаны
        if start_date and end_date:
            if not dates_in_range(del_date, start_date, end_date):
                continue
        
        ws.append([row['driver'], row['dispatcher'], row['broker'], row['load_number'], row['rate'], row['pu_date'], row['del_date']])
        total += row['rate'] or 0

    ws.append([])
    ws.append(["", "", "", "TOTAL", round(total, 2), "", ""])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    # Формируем имя файла с датами если они есть
    if start_date and end_date:
        filename = f"dispatcher_{dispatcher_name}_{start_date}_to_{end_date}.xlsx"
    else:
        filename = f"dispatcher_{dispatcher_name}.xlsx"

    return buffer, filename


async def get_all_drivers() -> list[str]:
    """Получить список всех водителей из БД"""
    rows = await fetch_all("SELECT name FROM drivers ORDER BY name")
    return [row['name'] for row in rows]


async def get_all_dispatchers() -> list[str]:
    """Получить список всех диспетчеров из БД"""
    rows = await fetch_all("SELECT name FROM dispatchers ORDER BY name")
    return [row['name'] for row in rows]


def create_period_keyboard() -> InlineKeyboardMarkup:
    """Создать клавиатуру с периодами"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 All Time", callback_data="period:all_time")],
            [InlineKeyboardButton(text="📊 This Week (Tue-Mon)", callback_data="period:this_week")],
            [InlineKeyboardButton(text="⏮️ Last Week", callback_data="period:last_week")],
            [InlineKeyboardButton(text="📈 This Month", callback_data="period:this_month")],
            [InlineKeyboardButton(text="📉 This Quarter", callback_data="period:this_quarter")],
            [InlineKeyboardButton(text="📆 This Year", callback_data="period:this_year")],
            [InlineKeyboardButton(text="🔧 Custom Range", callback_data="period:custom")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="back_to_menu")],
        ]
    )


def create_driver_keyboard(drivers: list[str]) -> InlineKeyboardMarkup:
    """Создать клавиатуру со списком водителей"""
    keyboard = []
    for driver in drivers:
        keyboard.append([InlineKeyboardButton(text=f"👨‍✈️ {driver}", callback_data=f"driver:{driver}")])
    keyboard.append([InlineKeyboardButton(text="◀️ Back", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_dispatcher_keyboard(dispatchers: list[str]) -> InlineKeyboardMarkup:
    """Создать клавиатуру со списком диспетчеров"""
    keyboard = []
    for dispatcher in dispatchers:
        keyboard.append([InlineKeyboardButton(text=f"📋 {dispatcher}", callback_data=f"dispatcher:{dispatcher}")])
    keyboard.append([InlineKeyboardButton(text="◀️ Back", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@suppress_group
@router.message(Command("gross_driver"))
async def command_gross_driver(message: Message, state: FSMContext):
    """Начать интерактивный выбор водителя"""
    drivers = await get_all_drivers()
    if not drivers:
        await message.reply("❌ No drivers found in database", reply_markup=main_menu)
        return
    
    await state.set_state(SelectionState.waiting_for_period_type)
    await state.update_data(entity_type="driver")
    await message.reply(
        "👨‍✈️ Select a driver:",
        reply_markup=create_driver_keyboard(drivers)
    )


@suppress_group
@router.message(Command("gross_dispatcher"))
async def command_gross_dispatcher(message: Message, state: FSMContext):
    """Начать интерактивный выбор диспетчера"""
    dispatchers = await get_all_dispatchers()
    if not dispatchers:
        await message.reply("❌ No dispatchers found in database", reply_markup=main_menu)
        return
    
    await state.set_state(SelectionState.waiting_for_period_type)
    await state.update_data(entity_type="dispatcher")
    await message.reply(
        "📋 Select a dispatcher:",
        reply_markup=create_dispatcher_keyboard(dispatchers)
    )


@suppress_group
@router.callback_query(F.data.startswith("driver:"))
async def select_driver_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора водителя"""
    driver_name = callback.data.split(":", 1)[1]
    await state.update_data(driver_or_dispatcher=driver_name)
    await callback.message.delete()
    await callback.message.answer(
        f"👨‍✈️ *{driver_name}*\n\n📅 Select period:",
        parse_mode="Markdown",
        reply_markup=create_period_keyboard()
    )
    await callback.answer()


@suppress_group
@router.callback_query(F.data.startswith("dispatcher:"))
async def select_dispatcher_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора диспетчера"""
    dispatcher_name = callback.data.split(":", 1)[1]
    await state.update_data(driver_or_dispatcher=dispatcher_name)
    await callback.message.delete()
    await callback.message.answer(
        f"📋 *{dispatcher_name}*\n\n📅 Select period:",
        parse_mode="Markdown",
        reply_markup=create_period_keyboard()
    )
    await callback.answer()


@suppress_group
@router.callback_query(F.data.startswith("period:"))
async def select_period_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора периода"""
    period = callback.data.split(":", 1)[1]
    data = await state.get_data()
    
    entity_type = data.get("entity_type")
    name = data.get("driver_or_dispatcher")
    
    if not name or not entity_type:
        await callback.answer("❌ Error: missing selection", show_alert=True)
        return
    
    if period == "custom":
        await callback.message.edit_text(
            "📝 Enter date range in format: *2/24/26-3/2/26*",
            parse_mode="Markdown"
        )
        await state.set_state(SelectionState.waiting_for_custom_date_range)
        return
    
    # Получаем диапазон дат
    date_range = get_period_dates(period)
    if not date_range:
        date_range = (None, None)
    
    start_date, end_date = date_range
    
    # Вычисляем гросс
    if entity_type == "driver":
        total = await gross_by_driver(name, start_date, end_date)
        emoji = "🚚"
        label = "driver"
    else:
        total = await gross_by_dispatcher(name, start_date, end_date)
        emoji = "📊"
        label = "dispatcher"
    
    # Форматируем информацию о периоде
    if period == "all_time":
        period_text = "All Time"
    elif period == "this_week":
        period_text = f"This Week (Tue-Mon)\n{start_date} → {end_date}"
    elif period == "last_week":
        period_text = f"Last Week (Tue-Mon)\n{start_date} → {end_date}"
    elif period == "this_month":
        period_text = f"This Month\n{start_date} → {end_date}"
    elif period == "this_quarter":
        period_text = f"This Quarter\n{start_date} → {end_date}"
    elif period == "this_year":
        period_text = f"This Year\n{start_date} → {end_date}"
    else:
        period_text = "Custom"
    
    try:
        buffer, filename = await export_driver_to_excel(name, start_date, end_date) if entity_type == "driver" else await export_dispatcher_to_excel(name, start_date, end_date)
        file = BufferedInputFile(buffer.getvalue(), filename=filename)
        
        caption = (
            f"{emoji} *Gross {label.upper()}*\n"
            f"📇 {name}\n\n"
            f"📅 {period_text}\n\n"
            f"💰 *TOTAL: ${total:.2f}*\n"
            f"━━━━━━━━━━━━━━━━━"
        )
        
        await callback.message.delete()
        await callback.message.answer_document(
            file,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=main_menu
        )
        await state.clear()
    except Exception as e:
        await state.clear()
        await callback.answer(f"❌ Error: {str(e)}", show_alert=True)
        logger.exception(f"Error exporting {entity_type}: {name}")
@suppress_group
@router.message(SelectionState.waiting_for_custom_date_range)
async def handle_custom_date_range(message: Message, state: FSMContext):
    """Обработчик ввода кастомного диапазона дат"""
    date_range_str = message.text or ""
    
    date_range = parse_date_range(date_range_str)
    if not date_range:
        await message.reply("❌ Invalid date format. Use: 2/24/26-3/2/26 or 2/24/2026-3/2/2026")
        return
    
    data = await state.get_data()
    entity_type = data.get("entity_type")
    name = data.get("driver_or_dispatcher")
    
    start_date, end_date = date_range
    
    # Вычисляем гросс
    if entity_type == "driver":
        total = await gross_by_driver(name, start_date, end_date)
        emoji = "🚚"
        label = "driver"
    else:
        total = await gross_by_dispatcher(name, start_date, end_date)
        emoji = "📊"
        label = "dispatcher"
    
    try:
        buffer, filename = await export_driver_to_excel(name, start_date, end_date) if entity_type == "driver" else await export_dispatcher_to_excel(name, start_date, end_date)
        file = BufferedInputFile(buffer.getvalue(), filename=filename)
        
        caption = (
            f"{emoji} *Gross {label.upper()}*\n"
            f"📇 {name}\n\n"
            f"📅 Custom Range\n{start_date} → {end_date}\n\n"
            f"💰 *TOTAL: ${total:.2f}*\n"
            f"━━━━━━━━━━━━━━━━━"
        )
        
        await message.answer_document(
            file,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=main_menu
        )
        await state.clear()
    except Exception as e:
        await state.clear()
        await message.reply(f"❌ Error: {str(e)}", reply_markup=main_menu)
        logger.exception(f"Error exporting custom range {entity_type}: {name}")

@suppress_group
@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_callback(callback: CallbackQuery, state: FSMContext):
    """Вернуться в главное меню"""
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("Main menu:", reply_markup=main_menu)
    await callback.answer()
