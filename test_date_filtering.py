#!/usr/bin/env python3
"""
Test script for date filtering functionality.
Run this to verify that the new date filtering feature is working correctly.
"""

import sys


def test_imports():
    print("Testing imports...")
    try:
        from services.parser import parse_load, parse_date_from_time_string
        print("  OK services.parser imports successful")
    except Exception as e:
        print(f"  FAIL services.parser import failed: {e}")
        return False

    try:
        from handlers.gross import parse_date_range, dates_in_range, gross_by_driver, gross_by_dispatcher, normalize_date
        print("  OK handlers.gross imports successful")
    except Exception as e:
        print(f"  FAIL handlers.gross import failed: {e}")
        return False

    try:
        from handlers.loads import add_load
        print("  OK handlers.loads imports successful")
    except Exception as e:
        print(f"  FAIL handlers.loads import failed: {e}")
        return False

    try:
        from db.database import init_db, get_connection
        print("  OK db.database imports successful")
    except Exception as e:
        print(f"  FAIL db.database import failed: {e}")
        return False

    return True


def test_date_parsing():
    print("\nTesting date parsing functions...")
    from services.parser import parse_date_from_time_string
    from handlers.gross import normalize_date

    test_cases = [
        ("02/25/2026 0330", "2/25/2026"),
        ("2/25/2026 1230", "2/25/2026"),
        ("03/22/26", "3/22/2026"),
        ("22 Mar", "3/22/2026"),
        ("DEL time: 22 Mar 1400", "3/22/2026"),
        ("1/5/2026 0900", "1/5/2026"),
        ("invalid", None),
        ("", None),
    ]

    for input_str, expected in test_cases:
        result = parse_date_from_time_string(input_str)
        if result == expected:
            print(f"  OK parse_date_from_time_string('{input_str}') = {result}")
        else:
            print(f"  FAIL parse_date_from_time_string('{input_str}') expected {expected}, got {result}")
            return False

    normalize_cases = [
        ("2/24/26", "2/24/2026"),
        ("2/24/2026", "2/24/2026"),
        ("02/24/2026", "2/24/2026"),
        ("1/5/26", "1/5/2026"),
        ("invalid", None),
    ]

    for input_str, expected in normalize_cases:
        result = normalize_date(input_str)
        if result == expected:
            print(f"  OK normalize_date('{input_str}') = {result}")
        else:
            print(f"  FAIL normalize_date('{input_str}') expected {expected}, got {result}")
            return False

    return True


def test_date_range_parsing():
    print("\nTesting date range parsing...")
    from handlers.gross import parse_date_range

    test_cases = [
        ("2/24/26-3/2/26", ("2/24/2026", "3/2/2026")),
        ("2/24/2026-3/2/2026", ("2/24/2026", "3/2/2026")),
        ("1/1/26-12/31/26", ("1/1/2026", "12/31/2026")),
        ("invalid", None),
        ("2/24/26", None),
        ("", None),
    ]

    for input_str, expected in test_cases:
        result = parse_date_range(input_str)
        if result == expected:
            print(f"  OK parse_date_range('{input_str}') = {result}")
        else:
            print(f"  FAIL parse_date_range('{input_str}') expected {expected}, got {result}")
            return False

    return True


def test_date_range_checking():
    print("\nTesting date range checking...")
    from handlers.gross import dates_in_range

    test_cases = [
        ("2/25/2026", "2/24/2026", "3/2/2026", True),
        ("2/24/2026", "2/24/2026", "3/2/2026", True),
        ("3/2/2026", "2/24/2026", "3/2/2026", True),
        ("3/5/2026", "2/24/2026", "3/2/2026", False),
        ("2/20/2026", "2/24/2026", "3/2/2026", False),
        (None, "2/24/2026", "3/2/2026", False),
        ("invalid", "2/24/2026", "3/2/2026", False),
    ]

    for date_str, start_date, end_date, expected in test_cases:
        result = dates_in_range(date_str, start_date, end_date)
        if result == expected:
            print(f"  OK dates_in_range('{date_str}', '{start_date}', '{end_date}') = {result}")
        else:
            print(f"  FAIL dates_in_range('{date_str}', '{start_date}', '{end_date}') expected {expected}, got {result}")
            return False

    return True


def test_parse_load():
    print("\nTesting parse_load with date extraction...")
    from services.parser import parse_load

    message = """\u203c\ufe0fLOAD NUMBER: 567765\u203c\ufe0f
\u203c\ufe0fDispatch: Sam Walter \u203c\ufe0f
PU time: 03/22/26
DEL time: 22 Mar
\u203c\ufe0fRATE: $100 \u203c\ufe0f"""

    result = parse_load(message)

    required_fields = ["load_number", "dispatch", "rate", "miles", "pu_date", "del_date"]
    for field in required_fields:
        if field in result:
            print(f"  OK parse_load includes '{field}': {result[field]}")
        else:
            print(f"  FAIL parse_load missing field '{field}'")
            return False

    if result.get("pu_date") != "3/22/2026":
        print(f"  FAIL pu_date not correctly parsed: {result.get('pu_date')}")
        return False

    if result.get("del_date") != "3/22/2026":
        print(f"  FAIL del_date not correctly parsed: {result.get('del_date')}")
        return False

    if result.get("rate") != 100.0:
        print(f"  FAIL rate not correctly parsed: {result.get('rate')}")
        return False

    if result.get("miles") is not None:
        print(f"  FAIL miles should be optional and missing here: {result.get('miles')}")
        return False

    message_with_miles = message + "\nMiles: 1,250.5 mi"
    result_with_miles = parse_load(message_with_miles)
    if result_with_miles.get("miles") != 1250.5:
        print(f"  FAIL miles not correctly parsed: {result_with_miles.get('miles')}")
        return False

    print("  OK parse_load correctly normalizes supported date formats")
    return True


def test_database():
    print("\nTesting database schema...")
    import asyncio
    from db.database import init_db, fetch_all

    async def async_test():
        try:
            await init_db()
            print("  OK Database initialized successfully")

            columns = await fetch_all("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'loads' AND column_name = 'miles'
            """)

            if columns:
                print("  OK 'miles' column exists in 'loads' table")
            else:
                print("  FAIL 'miles' column missing from 'loads' table")
                return False

            return True
        except Exception as e:
            print(f"  FAIL Database test failed: {e}")
            return False

    return asyncio.run(async_test())


def run_all_tests():
    print("=" * 60)
    print("Running Date Filtering Feature Tests")
    print("=" * 60)

    tests = [
        ("Import Test", test_imports),
        ("Date Parsing Test", test_date_parsing),
        ("Date Range Parsing Test", test_date_range_parsing),
        ("Date Range Check Test", test_date_range_checking),
        ("Parse Load Test", test_parse_load),
        ("Database Schema Test", test_database),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\nFAIL {test_name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"{status}: {test_name}")

    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    return all(result for _, result in results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
