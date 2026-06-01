import re
from datetime import datetime


FIELD_END = "\u203c\ufe0f"
MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def extract_between(text: str, start: str) -> str | None:
    pattern = rf"{re.escape(start)}\s*(.*?)\s*{re.escape(FIELD_END)}"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else None


def extract_line_value(text: str, field_name: str) -> str | None:
    pattern = rf"(?i)\b{re.escape(field_name)}\s*:?\s*([^\r\n{re.escape(FIELD_END)}]+)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def parse_rate_to_float(rate_text: str) -> float | None:
    if not rate_text:
        return None

    cleaned = re.sub(r"[^\d.,]", "", rate_text)
    normalized = cleaned.replace(",", ".")

    try:
        return round(float(normalized), 2)
    except ValueError:
        return None


def parse_miles_to_float(miles_text: str) -> float | None:
    if not miles_text:
        return None

    match = re.search(r"\d[\d,]*(?:\.\d+)?", miles_text)
    if not match:
        return None

    try:
        return round(float(match.group(0).replace(",", "")), 2)
    except ValueError:
        return None


def _format_date(month: int, day: int, year: int) -> str:
    return f"{month}/{day}/{year}"


def parse_date_from_time_string(time_string: str) -> str | None:
    if not time_string:
        return None

    text = time_string.strip()

    full_year_match = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", text)
    if full_year_match:
        month, day, year = map(int, full_year_match.groups())
        return _format_date(month, day, year)

    short_year_match = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{2})\b", text)
    if short_year_match:
        month, day, short_year = map(int, short_year_match.groups())
        year = 2000 + short_year
        return _format_date(month, day, year)

    text_month_match = re.search(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\b", text)
    if text_month_match:
        day = int(text_month_match.group(1))
        month_name = text_month_match.group(2).lower()[:4].rstrip(".")
        month = MONTHS.get(month_name) or MONTHS.get(month_name[:3])
        if month is not None:
            year = datetime.now().year
            return _format_date(month, day, year)

    return None


def parse_load(text: str) -> dict:
    rate_raw = extract_between(text, f"{FIELD_END}RATE:") or extract_line_value(text, "Rate")
    miles_raw = extract_line_value(text, "Miles")
    pu_time = extract_between(text, "PU time:")
    pu_date = parse_date_from_time_string(pu_time) if pu_time else None

    del_time = extract_between(text, "DEL time:")
    del_date = parse_date_from_time_string(del_time) if del_time else None

    return {
        "load_number": extract_between(text, f"{FIELD_END}LOAD NUMBER:"),
        "dispatch": extract_between(text, f"{FIELD_END}Dispatch:"),
        "broker": extract_between(text, f"{FIELD_END}BROKER:"),
        "rate": parse_rate_to_float(rate_raw),
        "miles": parse_miles_to_float(miles_raw),
        "pu_date": pu_date,
        "del_date": del_date,
    }


def parse_load_update(text: str) -> dict | None:
    load_number = extract_between(text, f"{FIELD_END}LOAD NUMBER:")
    if not load_number:
        return None

    if re.search(r"\bcancell?ed\b", text, re.IGNORECASE):
        return {
            "action": "canceled",
            "load_number": load_number,
            "rate": 0.0,
        }

    revised_rate_raw = extract_line_value(text, "REVISED RATE")
    revised_rate = parse_rate_to_float(revised_rate_raw)
    if revised_rate is not None:
        return {
            "action": "revised_rate",
            "load_number": load_number,
            "rate": revised_rate,
        }

    return None
