import asyncio
import asyncpg

from config.settings import DATABASE_URL

pool = None


def _pool_closed(current_pool) -> bool:
    if current_pool is None:
        return True

    is_closed = getattr(current_pool, "is_closed", None)
    if callable(is_closed):
        return is_closed()

    return bool(getattr(current_pool, "_closed", False))


async def create_pool(force: bool = False):
    global pool

    if force and not _pool_closed(pool):
        await pool.close()
        pool = None

    if _pool_closed(pool):
        pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=10,
            max_inactive_connection_lifetime=300,
        )
    return pool


async def get_connection():
    if _pool_closed(pool):
        await create_pool()
    return pool


async def _retry_db_call(operation):
    global pool

    try:
        return await operation()
    except (
        asyncpg.InterfaceError,
        asyncpg.ConnectionDoesNotExistError,
        asyncpg.ConnectionFailureError,
        asyncpg.CannotConnectNowError,
        OSError,
    ):
        if not _pool_closed(pool):
            await pool.close()
        pool = None
        await create_pool(force=True)
        return await operation()

# Инициализация всех таблиц
async def init_db():
    conn = await get_connection()
    async with conn.acquire() as connection:
        # Водители
        await connection.execute("""
        CREATE TABLE IF NOT EXISTS drivers (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE
        )
        """)

        # Диспетчеры
        await connection.execute("""
        CREATE TABLE IF NOT EXISTS dispatchers (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE
        )
        """)

        # Связь "много ко многим"
        await connection.execute("""
        CREATE TABLE IF NOT EXISTS driver_dispatcher (
            driver_id INTEGER,
            dispatcher_id INTEGER,
            PRIMARY KEY(driver_id, dispatcher_id),
            FOREIGN KEY(driver_id) REFERENCES drivers(id),
            FOREIGN KEY(dispatcher_id) REFERENCES dispatchers(id)
        )
        """)

        # Грузы
        await connection.execute("""
        CREATE TABLE IF NOT EXISTS loads (
            id SERIAL PRIMARY KEY,
            driver_id INTEGER,
            dispatcher_id INTEGER,
            broker TEXT,
            load_number TEXT UNIQUE,
            rate REAL,
            pu_date TEXT,
            del_date TEXT,
            FOREIGN KEY(driver_id) REFERENCES drivers(id),
            FOREIGN KEY(dispatcher_id) REFERENCES dispatchers(id)
        )
        """)

        # Чаты для регистрации
        await connection.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            chat_id BIGINT PRIMARY KEY,
            title TEXT
        )
        """)

async def execute_query(query, *args):
    async def operation():
        conn = await get_connection()
        async with conn.acquire() as connection:
            return await connection.execute(query, *args)

    return await _retry_db_call(operation)

async def fetch_one(query, *args):
    async def operation():
        conn = await get_connection()
        async with conn.acquire() as connection:
            return await connection.fetchrow(query, *args)

    return await _retry_db_call(operation)

async def fetch_all(query, *args):
    async def operation():
        conn = await get_connection()
        async with conn.acquire() as connection:
            return await connection.fetch(query, *args)

    return await _retry_db_call(operation)

# Если запускаем файл напрямую, создаём базу
if __name__ == "__main__":
    asyncio.run(init_db())
    print("База данных и таблицы успешно созданы ✅")
