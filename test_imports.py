"""Quick test - import all handlers and check for errors"""
import asyncio
import sys

async def test_imports():
    print("\n📦 Testing handler imports...")
    try:
        from handlers.start import router as start_router
        print("✅ start.py imported successfully")
    except Exception as e:
        print(f"❌ start.py failed: {e}")
        return False
    
    try:
        from handlers.loads import router as loads_router
        print("✅ loads.py imported successfully")
    except Exception as e:
        print(f"❌ loads.py failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        from handlers.gross import router as gross_router
        print("✅ gross.py imported successfully")
    except Exception as e:
        print(f"❌ gross.py failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def main():
    print("="*50)
    print("🔍 HANDLER IMPORT TEST")
    print("="*50)
    
    result = await test_imports()
    
    if result:
        print("\n✅ All handlers imported successfully!")
        print("🤖 Bot is ready to run!")
    else:
        print("\n❌ Some handlers have errors")
    
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
