# Database Migration Guide

## Migration from SQLite to PostgreSQL

The project has been migrated from SQLite to PostgreSQL for better performance and scalability.

### Changes Made

#### Database Driver
- **Old**: sqlite3 (synchronous)
- **New**: asyncpg (asynchronous PostgreSQL driver)

#### Schema Changes
- `AUTOINCREMENT` → `SERIAL PRIMARY KEY`
- `INSERT OR IGNORE` → `INSERT ... ON CONFLICT DO NOTHING`
- Parameter placeholders: `?` → `$1, $2, etc.`
- Result access: `fetchone()[0]` → `result['column_name']`
- Result access: `fetchall()` → list of dicts

#### New Tables
- `chats` table for storing registered chat information

#### Configuration
- Added database connection settings in `config/settings.py`
- Environment variables for PostgreSQL connection
- Added `.env` file template

### Updated Schema

```sql
CREATE TABLE IF NOT EXISTS drivers (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS dispatchers (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS driver_dispatcher (
    driver_id INTEGER,
    dispatcher_id INTEGER,
    PRIMARY KEY(driver_id, dispatcher_id),
    FOREIGN KEY(driver_id) REFERENCES drivers(id),
    FOREIGN KEY(dispatcher_id) REFERENCES dispatchers(id)
);

CREATE TABLE IF NOT EXISTS loads (
    id SERIAL PRIMARY KEY,
    driver_id INTEGER,
    dispatcher_id INTEGER,
    truck_unit TEXT,
    broker TEXT,
    load_number TEXT UNIQUE,
    rate REAL,
    pu_date TEXT,
    del_date TEXT,
    FOREIGN KEY(driver_id) REFERENCES drivers(id),
    FOREIGN KEY(dispatcher_id) REFERENCES dispatchers(id)
);

CREATE TABLE IF NOT EXISTS chats (
    chat_id BIGINT PRIMARY KEY,
    title TEXT
);
```

### Environment Variables

Create a `.env` file with the following variables:

```
BOT_TOKEN=your_bot_token_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=runpro_bot
DB_USER=postgres
DB_PASSWORD=your_password_here
```

### Migration Steps

1. Install PostgreSQL server
2. Create database and user
3. Update `.env` file with your database credentials
4. Install dependencies: `pip install -r requirements.txt`
5. Run the bot: `python main.py`

The application will automatically create all tables on first run.

**Note**: Existing SQLite data is not migrated. Start with a fresh PostgreSQL database.

```
id | driver_id | dispatcher_id | load_number | rate   | del_date
1  | 1         | 2             | 567765      | 100.00 | 2/25/2026
2  | 1         | 2             | 567766      | 150.00 | 2/26/2026
3  | 2         | 3             | 567767      | 200.00 | 3/1/2026
4  | 1         | 2             | 567768      | 120.00 | NULL       (old loads without dates)
```

## Impact on Existing Data

- **Existing loads**: Will have `NULL` values for `del_date` (unless you manually update them)
- **Filtering**: Filters with date ranges will automatically skip NULL dates
- **Migration**: Automatic and non-destructive

## Manual Data Update (Optional)

If you want to backfill dates for existing loads from archived messages, you can manually update them:

```sql
-- Example: Update a specific load with a date
UPDATE loads 
SET del_date = '2/25/2026' 
WHERE load_number = '567765';

-- Or use a case statement for multiple loads
UPDATE loads 
SET del_date = CASE 
    WHEN load_number = '567765' THEN '2/25/2026'
    WHEN load_number = '567766' THEN '2/26/2026'
    ELSE del_date
END;
```

## Performance Considerations

- Currently no index on `del_date`, but filtering only returns rows matching the driver/dispatcher first, so performance should be acceptable
- If you need to add an index for very large databases:

```sql
CREATE INDEX idx_loads_del_date ON loads(del_date);
```

## Rollback (if needed)

To remove the new column (not recommended):

```sql
-- Note: SQLite doesn't have DROP COLUMN in older versions
-- You would need to recreate the table
-- This is why we made it optional to include dates
```
