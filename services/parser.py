import re
from datetime import datetime


def extract_between(text: str, start: str) -> str | None:
    pattern = rf"{re.escape(start)}\s*(.*?)\s*‼️"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else None


def parse_rate_to_float(rate_text: str) -> float | None:
    """
    Преобразует текст вида:
      '$1 819,86' -> 1819.86
      '$5000'     -> 5000.0
    """
    if not rate_text:
        return None

    cleaned = re.sub(r"[^\d.,]", "", rate_text)
    normalized = cleaned.replace(",", ".")

    try:
        return round(float(normalized), 2)
    except ValueError:
        return None


def parse_date_from_time_string(time_string: str) -> str | None:
    """
    Извлекает дату из строки вида "02/25/2026 0330" или "2/25/2026 1230"
    Возвращает дату в формате "2/25/2026"
    """
    if not time_string:
        return None
    
    # Извлекаем только дату (первую часть до пробела)
    match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", time_string)
    if match:
        date_str = match.group(1).strip()
        # Убираем ведущие нули
        parts = date_str.split('/')
        return f"{int(parts[0])}/{int(parts[1])}/{parts[2]}"
    return None


def parse_load(text: str) -> dict:
    rate_raw = extract_between(text, "‼️RATE:")
    
    # Извлекаем PU time для получения даты подачи
    pu_time = extract_between(text, "PU time:")
    pu_date = parse_date_from_time_string(pu_time) if pu_time else None
    
    # Извлекаем DEL time для получения даты доставки
    del_time = extract_between(text, "DEL time:")
    del_date = parse_date_from_time_string(del_time) if del_time else None

    return {
        "truck_unit": extract_between(text, "‼️TRUCK:"),
        "load_number": extract_between(text, "‼️LOAD NUMBER:"),
        "dispatch": extract_between(text, "‼️Dispatch:"),
        "broker": extract_between(text, "‼️BROKER:"),
        "rate": parse_rate_to_float(rate_raw),
        "pu_date": pu_date,
        "del_date": del_date
    }