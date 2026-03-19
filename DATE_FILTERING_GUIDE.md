# Date Filtering Guide 📅

## Overview
The application now supports filtering gross revenue by date range. You can get reports for specific time periods both for drivers and dispatchers.

## How It Works

### 1. Automatic Date Extraction
When a load message is received, the application automatically extracts the **delivery date** from the `DEL time:` field in the message template:

```
DEL time: 2/25/2026 1230    → Extracts: 2/25/2026
```

The date is stored in the database for each load.

### 2. Commands with Date Range Support

#### For Drivers:
```bash
# Get all-time gross for a driver
/gross_driver John Doe

# Get gross for a date range  
/gross_driver John Doe 2/24/26-3/2/26
```

#### For Dispatchers:
```bash
# Get all-time gross for a dispatcher
/gross_dispatcher Sam Walter

# Get gross for a date range
/gross_dispatcher Sam Walter 2/24/26-3/2/26
```

#### Export Commands (same syntax):
```bash
/export_driver Name [date_range]
/export_dispatcher Name [date_range]
```

### 3. Date Format
- **Supported formats**: `M/D/YY` or `M/D/YYYY`
- **Range separator**: Hyphen `-`
- **Examples**:
  - `2/24/26-3/2/26` ✅
  - `2/24/2026-3/2/2026` ✅
  - `02/24/2026-03/02/2026` ✅ (leading zeros supported)

### 4. Excel Export Features
When exporting data:
- **All-time exports**: File named `driver_Name.xlsx` or `dispatcher_Name.xlsx`
- **Date-range exports**: File named `driver_Name_M/D/YYYY_to_M/D/YYYY.xlsx`
- All exports include a `DEL Date` column for reference
- Totals section shows filtered sum at the bottom

## Examples in Practice

### Example 1: Driver Report for Specific Month
```
/gross_driver John Doe 2/1/26-2/28/26
```
Returns: Total revenue for John Doe for February 2026, Excel file with all matching loads

### Example 2: Dispatcher Report for Quarter
```
/gross_dispatcher Sam Walter 1/1/26-3/31/26
```
Returns: Total revenue for Sam Walter for Q1 2026, Excel file with all matching loads

### Example 3: All-Time Report
```
/gross_driver Mary Smith
```
Returns: Total revenue for Mary Smith from all time, Excel file with ALL loads

## Visual Output

### Response Caption Format
```
🚚 Gross driver John Doe (2/24/2026 to 3/2/2026)
💰 Total: $5,250.00
```

or for all-time:

```
🚚 Gross driver John Doe (all time)  
💰 Total: $12,500.00
```

## Important Notes

1. **Date Extraction**: The DEL time field must be present in the load message for the date to be stored
2. **Empty Results**: If no loads exist in the date range, the total will be $0.00 and the Excel file will be empty
3. **Case Sensitivity**: Driver/Dispatcher names should match exactly as stored in database
4. **Date Validation**: If an invalid date range is provided, you'll receive an error message with the correct format

## Database Schema
The `loads` table now includes:
- `del_date TEXT` - Stores delivery date in format `M/D/YYYY`

Example of how dates are stored:
```
load_number | driver_name | del_date   | rate
567765      | John Doe    | 2/25/2026  | 100.00
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Invalid date format" error | Use format like `2/24/26-3/2/26` or `2/24/2026-3/2/2026` |
| No loads in Excel file | Check if date range is correct; some loads might have NULL dates |
| Total shows $0.00 | No matching loads found in the date range |
| Driver/Dispatcher name not found | Make sure exact name matches database (check previously exported files) |
