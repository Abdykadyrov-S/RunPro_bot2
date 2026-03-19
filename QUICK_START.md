# Quick Start Guide - Date Filtering Feature

## What's New? ✨

Your application now supports **filtering gross revenue by date range**. This allows you to:
- Get revenue reports for specific time periods
- Export Excel files with filtered loads
- Automatically extract delivery dates from load messages

## Setup

No additional setup needed! The changes are automatic:
1. Database will automatically add the `del_date` column on first run
2. Date extraction starts working immediately with existing message format
3. All commands work with or without date ranges

## Usage Examples

### 1. Get Driver Gross Report
```
# All time
/gross_driver John Doe
Output: 🚚 Gross driver John Doe (all time) 💰 Total: $12,500.00

# Specific date range
/gross_driver John Doe 2/24/26-3/2/26
Output: 🚚 Gross driver John Doe (2/24/2026 to 3/2/2026) 💰 Total: $5,250.00
```

### 2. Get Dispatcher Gross Report
```
# All time
/gross_dispatcher Sam Walter

# Specific date range  
/gross_dispatcher Sam Walter 2/1/26-2/28/26
```

### 3. Export to Excel
```
# All loads
/export_driver John Doe

# Only loads delivered in Feb 2026
/export_driver John Doe 2/1/26-2/28/26
```

## Date Format

Use one of these formats:
- `2/24/26-3/2/26` ← Recommended (shorter)
- `2/24/2026-3/2/2026` ← Also works (full year)

**Format**: `Month/Day/Year-Month/Day/Year`

## How It Works Behind the Scenes

### Message Example
When you send a load message like:
```
‼️TRUCK: 12 ‼️
‼️LOAD NUMBER: 567765 ‼️
‼️Dispatch: Sam Walter ‼️
DEL time: 2/25/2026 1230
‼️RATE: $100 ‼️
```

The system automatically:
1. ✅ Extracts the date `2/25/2026` from `DEL time:`
2. ✅ Stores it in the database
3. ✅ Uses it for filtering reports

### Report Generation
When you request a date range report:
1. ✅ System fetches all loads for that driver/dispatcher
2. ✅ Filters by delivery date within your range
3. ✅ Sums only the matching loads
4. ✅ Creates Excel file with filtered data + date column

## Excel File Examples

### All-Time Export
**File name:** `driver_John_Doe.xlsx`
```
Driver | Dispatcher | Truck | Load # | Rate | DEL Date
-------|-----------|-------|--------|------|----------
John   | Sam       | 12    | 567765 | 100  | 2/25/2026
John   | Sam       | 15    | 567766 | 150  | 2/26/2026
...
TOTAL:                                       | $5,250.00
```

### Date-Range Export  
**File name:** `driver_John_Doe_2/24/2026_to_3/2/2026.xlsx`
```
Driver | Dispatcher | Truck | Load # | Rate | DEL Date
-------|-----------|-------|--------|------|----------
John   | Sam       | 12    | 567765 | 100  | 2/25/2026
John   | Sam       | 15    | 567766 | 150  | 2/26/2026
...
TOTAL:                                       | $5,250.00
```

## Common Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `/gross_driver` | Total for one driver | `/gross_driver John Doe 2/1/26-2/28/26` |
| `/gross_dispatcher` | Total for one dispatcher | `/gross_dispatcher Sam 1/1/26-3/31/26` |
| `/export_driver` | Get Excel file for driver | `/export_driver John Doe 2/1/26-2/28/26` |
| `/export_dispatcher` | Get Excel file for dispatcher | `/export_dispatcher Sam 2/1/26-2/28/26` |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Invalid date format" | Make sure you use: `2/24/26-3/2/26` (with hyphen) |
| Total shows $0.00 | No loads found in that date range - check the dates |
| Driver not found | Make sure spelling matches exactly (case-sensitive) |
| Excel file is empty | Check if loadshave `DEL time` field with valid dates |

## Pro Tips 💡

1. **Month ranges**: Use `1/1/26-1/31/26` for monthly reports
2. **Quarter ranges**: Use `1/1/26-3/31/26` for Q1 reports  
3. **Year ranges**: Use `1/1/26-12/31/26` for full year
4. **Exact day**: Use `2/24/26-2/24/26` for a single day's loads
5. **Multi-word names**: Spaces are included: `/gross_driver John Doe 2/1/26-2/28/26`

## Files Modified

- ✅ `services/parser.py` - Date extraction
- ✅ `db/database.py` - Added `del_date` column
- ✅ `handlers/loads.py` - Store dates when processing messages
- ✅ `handlers/gross.py` - Filter and report by dates

For technical details, see [IMPLEMENTATION_REFERENCE.md](IMPLEMENTATION_REFERENCE.md)

---

**Need help?** Check [DATE_FILTERING_GUIDE.md](DATE_FILTERING_GUIDE.md) for detailed documentation.
