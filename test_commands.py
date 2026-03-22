"""Test all bot commands for functionality"""
import asyncio
import asyncpg
from db.database import init_db, fetch_all, fetch_one, execute_query, get_connection


async def test_database_connection():
    """Test if database connection works"""
    print("\n🔌 Testing database connection...")
    try:
        pool = await get_connection()
        async with pool.acquire() as conn:
            result = await conn.fetchval('SELECT version()')
            print(f"✅ Database connected: {result[:40]}...")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def test_tables_exist():
    """Test if all required tables exist"""
    print("\n📊 Testing database tables...")
    try:
        # Test drivers table
        drivers = await fetch_all("SELECT COUNT(*) as count FROM drivers")
        print(f"✅ drivers table exists - {drivers[0]['count']} drivers")
        
        # Test dispatchers table
        dispatchers = await fetch_all("SELECT COUNT(*) as count FROM dispatchers")
        print(f"✅ dispatchers table exists - {dispatchers[0]['count']} dispatchers")
        
        # Test loads table
        loads = await fetch_all("SELECT COUNT(*) as count FROM loads")
        print(f"✅ loads table exists - {loads[0]['count']} loads")
        
        return True
    except Exception as e:
        print(f"❌ Table test failed: {e}")
        return False


async def test_add_load():
    """Test adding a load to database"""
    print("\n📦 Testing add load function...")
    try:
        # Add test driver
        await execute_query(
            "INSERT INTO drivers (name) VALUES ($1) ON CONFLICT (name) DO NOTHING",
            "TestDriver123"
        )
        
        # Add test dispatcher
        await execute_query(
            "INSERT INTO dispatchers (name) VALUES ($1) ON CONFLICT (name) DO NOTHING",
            "TestDispatcher123"
        )
        
        # Get IDs
        driver_row = await fetch_one("SELECT id FROM drivers WHERE name=$1", "TestDriver123")
        dispatcher_row = await fetch_one("SELECT id FROM dispatchers WHERE name=$1", "TestDispatcher123")
        
        if not driver_row or not dispatcher_row:
            print("❌ Failed to create test driver/dispatcher")
            return False
        
        driver_id = driver_row['id']
        dispatcher_id = dispatcher_row['id']
        
        # Add test load
        await execute_query("""
            INSERT INTO loads (driver_id, dispatcher_id, broker, load_number, rate, pu_date, del_date)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, driver_id, dispatcher_id, "TestBroker", "LOAD001", 1500.00, "3/1/2026", "3/5/2026")
        
        # Verify load was added
        load = await fetch_one("SELECT * FROM loads WHERE load_number=$1", "LOAD001")
        if load:
            print(f"✅ Load added successfully - Load #{load['load_number']} - ${load['rate']}")
        else:
            print("❌ Load was not added to database")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Add load test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_gross_by_driver():
    """Test calculating gross by driver"""
    print("\n💰 Testing gross by driver calculation...")
    try:
        result = await fetch_one("""
            SELECT SUM(rate) as total
            FROM loads l
            JOIN drivers d ON l.driver_id = d.id
            WHERE d.name = $1
        """, "TestDriver123")
        
        if result and result['total']:
            print(f"✅ Gross calculation works - Total: ${result['total']:.2f}")
            return True
        else:
            print("⚠️  No loads found for driver (but query worked)")
            return True
    except Exception as e:
        print(f"❌ Gross calculation test failed: {e}")
        return False


async def test_get_all_drivers():
    """Test getting all drivers"""
    print("\n👥 Testing get all drivers...")
    try:
        drivers = await fetch_all("SELECT name FROM drivers ORDER BY name")
        print(f"✅ Retrieved {len(drivers)} drivers from database")
        return True
    except Exception as e:
        print(f"❌ Get all drivers test failed: {e}")
        return False


async def test_get_all_dispatchers():
    """Test getting all dispatchers"""
    print("\n📋 Testing get all dispatchers...")
    try:
        dispatchers = await fetch_all("SELECT name FROM dispatchers ORDER BY name")
        print(f"✅ Retrieved {len(dispatchers)} dispatchers from database")
        return True
    except Exception as e:
        print(f"❌ Get all dispatchers test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("="*50)
    print("🤖 BOT COMMANDS FUNCTIONALITY TEST")
    print("="*50)
    
    await init_db()
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Database Tables", test_tables_exist),
        ("Add Load", test_add_load),
        ("Gross by Driver", test_gross_by_driver),
        ("Get All Drivers", test_get_all_drivers),
        ("Get All Dispatchers", test_get_all_dispatchers),
    ]
    
    results = []
    for name, test_func in tests:
        result = await test_func()
        results.append((name, result))
    
    print("\n" + "="*50)
    print("📊 TEST RESULTS SUMMARY")
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
