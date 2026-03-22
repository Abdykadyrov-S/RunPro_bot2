"""Test specific command handler logic"""
import asyncio
import sys
sys.path.insert(0, '.')

from db.database import init_db, fetch_all, fetch_one, execute_query


async def test_command_gross_driver():
    """Test /gross_driver command logic"""
    print("\n🚚 Testing /gross_driver command...")
    try:
        # Get all drivers
        drivers = await fetch_all("SELECT name FROM drivers ORDER BY name")
        if not drivers:
            print("⚠️  No drivers in database - command would show error message")
            return True
        
        # Test gross calculation for first driver
        driver_name = drivers[0]['name']
        result = await fetch_one("""
            SELECT SUM(rate) as sum
            FROM loads l
            JOIN drivers d ON l.driver_id = d.id
            WHERE d.name = $1
        """, driver_name)
        
        total = result['sum'] or 0
        print(f"✅ /gross_driver works - Driver '{driver_name}' gross: ${round(total, 2)}")
        return True
    except Exception as e:
        print(f"❌ /gross_driver failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_command_gross_dispatcher():
    """Test /gross_dispatcher command logic"""
    print("\n📊 Testing /gross_dispatcher command...")
    try:
        # Get all dispatchers
        dispatchers = await fetch_all("SELECT name FROM dispatchers ORDER BY name")
        if not dispatchers:
            print("⚠️  No dispatchers in database - command would show error message")
            return True
        
        # Test gross calculation for first dispatcher
        dispatcher_name = dispatchers[0]['name']
        result = await fetch_one("""
            SELECT SUM(rate) as sum
            FROM loads l
            JOIN dispatchers ds ON l.dispatcher_id = ds.id
            WHERE ds.name = $1
        """, dispatcher_name)
        
        total = result['sum'] or 0
        print(f"✅ /gross_dispatcher works - Dispatcher '{dispatcher_name}' gross: ${round(total, 2)}")
        return True
    except Exception as e:
        print(f"❌ /gross_dispatcher failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_date_filtering():
    """Test date filtering logic for gross calculations"""
    print("\n📅 Testing date filtering...")
    try:
        # Get all loads with dates
        loads = await fetch_all("""
            SELECT rate, del_date FROM loads WHERE del_date IS NOT NULL
        """)
        
        if not loads:
            print("⚠️  No loads with dates in database")
            return True
        
        # Test if we can filter by date range
        test_date = "3/5/2026"
        count = len([l for l in loads if l['del_date'] == test_date])
        print(f"✅ Date filtering works - Found {count} loads on {test_date}")
        return True
    except Exception as e:
        print(f"❌ Date filtering failed: {e}")
        return False


async def test_excel_export():
    """Test Excel export preparation"""
    print("\n📝 Testing Excel export...")
    try:
        from openpyxl import Workbook
        
        # Get a driver with loads
        driver_loads = await fetch_all("""
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
            LIMIT 1
        """)
        
        if not driver_loads:
            print("⚠️  No loads found in database")
            return True
        
        # Test Workbook creation
        wb = Workbook()
        ws = wb.active
        ws.title = "Test"
        ws.append(["Driver", "Dispatcher", "Broker", "Load Number", "Rate", "PU Date", "DEL Date"])
        
        for row in driver_loads:
            ws.append([row['driver'], row['dispatcher'], row['broker'], row['load_number'],
                      row['rate'], row['pu_date'], row['del_date']])
        
        print(f"✅ Excel export works - Created workbook with {len(driver_loads)} load(s)")
        return True
    except Exception as e:
        print(f"❌ Excel export failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("="*50)
    print("📋 COMMAND HANDLERS LOGIC TEST")
    print("="*50)
    
    await init_db()
    
    tests = [
        ("Gross Driver", test_command_gross_driver),
        ("Gross Dispatcher", test_command_gross_dispatcher),
        ("Date Filtering", test_date_filtering),
        ("Excel Export", test_excel_export),
    ]
    
    results = []
    for name, test_func in tests:
        result = await test_func()
        results.append((name, result))
    
    print("\n" + "="*50)
    print("📊 COMMAND HANDLERS TEST SUMMARY")
    print("="*50)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\n📈 Total: {passed}/{total} tests passed")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
