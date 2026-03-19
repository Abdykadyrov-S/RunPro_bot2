import asyncpg
import asyncio

async def setup_database():
    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            database='postgres'
        )

        await conn.execute("CREATE USER runpro_user WITH PASSWORD 'runpro_pass'")
        print('User created successfully!')

        await conn.execute('CREATE DATABASE runpro_bot OWNER runpro_user')
        print('Database created successfully!')

        await conn.close()
    except Exception as e:
        print(f'Error: {e}')

asyncio.run(setup_database())