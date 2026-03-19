# RunPro - Freight Management Bot 🚚

## Latest Update: Date Range Filtering ✨

The application now supports **filtering gross revenue by date range**. Generate reports for specific time periods with automatic date extraction from load messages.

## Quick Links

- **New to date filtering?** Start with [QUICK_START.md](QUICK_START.md)
- **Want detailed info?** See [DATE_FILTERING_GUIDE.md](DATE_FILTERING_GUIDE.md)
- **Technical details?** Read [IMPLEMENTATION_REFERENCE.md](IMPLEMENTATION_REFERENCE.md)
- **Database changes?** Check [DATABASE_MIGRATION.md](DATABASE_MIGRATION.md)
- **What changed?** Review [CHANGES_SUMMARY.md](CHANGES_SUMMARY.md)

## Features

### Core Features
- ✅ Track freight loads from group chats
- ✅ Store driver and dispatcher information
- ✅ Calculate gross revenue
- ✅ Export data to Excel
- ✅ **NEW:** Filter reports by date range
- ✅ **NEW:** Automatic date extraction from messages

### Commands
```
/gross_driver NAME [DATE_RANGE]            Get driver revenue
/gross_dispatcher NAME [DATE_RANGE]        Get dispatcher revenue
/export_driver NAME [DATE_RANGE]           Export to Excel
/export_dispatcher NAME [DATE_RANGE]       Export to Excel
```

### Date Range Format
- `2/24/26-3/2/26` ← Recommended
- `2/24/2026-3/2/2026` ← Also works
- Omit date range for all-time reports

## Project Structure

```
RunPro/
├── main.py                          # Bot entry point
├── config/
│   └── settings.py                  # Configuration
├── core/
│   ├── bot.py                       # Bot initialization
│   ├── dispatcher.py                # Event dispatcher setup
│   └── logging.py                   # Logging configuration
├── db/
│   ├── database.py                  # Database schema & migrations
│   ├── models.py                    # Data models
│   └── export.py                    # Export utilities
├── handlers/
│   ├── start.py                     # /start command
│   ├── loads.py                     # Load message handling
│   └── gross.py                     # Gross calculation & reporting
├── keyboards/
│   └── main.py                      # Inline keyboards
├── services/
│   ├── admin.py                     # Admin notifications
│   └── parser.py                    # Message parsing & date extraction
├── requirements.txt                 # Python dependencies
├── Procfile                         # Deployment configuration
├── test_date_filtering.py           # Test script
└── README.md                        # This file
```

## Installation

### Prerequisites
- Python 3.8+
- Telegram Bot API token
- Virtual environment (recommended)

### Setup

```bash
# Clone the repository
git clone <repo_url>
cd RunPro

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure bot token
# Edit config/settings.py and set your BOT_TOKEN

# Run the bot
python main.py
```

## Usage Example

### Message Format
```
‼️BOOKED BY CMA ‼️
‼️BROKER: ITS‼️
‼️TRUCK: 12 ‼️
‼️LOAD NUMBER: 567765‼️
‼️Dispatch: Sam Walter ‼️
===================
PU address: 123 Main St
PU time: 02/25/2026 0330
===================
DEL address: 456 Oak Ave
DEL time: 2/25/2026 1230
===================
‼️RATE: $100 ‼️
RPM: $1.0/mi
Miles: 100 mi
```

### Commands
```
# Get all-time gross for a driver
/gross_driver John Doe

# Get gross for February 2026
/gross_driver John Doe 2/1/26-2/28/26

# Get dispatcher's Q1 revenue
/gross_dispatcher Sam Walter 1/1/26-3/31/26

# Export to Excel with dates
/export_driver Mary Johnson 2/24/26-3/2/26
```

## Database Schema

### Tables
- **drivers**: Driver information
- **dispatchers**: Dispatcher information
- **driver_dispatcher**: Many-to-many relationship
- **loads**: Load records with new `del_date` field

### New Schema Change
The `loads` table now includes:
```sql
del_date TEXT          -- Delivery date (M/D/YYYY format)
```

## Testing

Run the test suite to verify the date filtering implementation:

```bash
python test_date_filtering.py
```

Expected output:
```
✅ PASSED: Import Test
✅ PASSED: Date Parsing Test
✅ PASSED: Date Range Parsing Test
✅ PASSED: Date Range Check Test
✅ PASSED: Parse Load Test
✅ PASSED: Database Schema Test
Results: 6/6 tests passed
```

## Configuration

Edit `config/settings.py`:
```python
BOT_TOKEN = "your_bot_token_here"
ADMIN_ID = 123456789  # Your Telegram ID
ADMINS = [123456789, 987654321]  # List of admin IDs
```

## Date Filtering Examples

### Example 1: Monthly Report
```
/gross_driver John Doe 2/1/26-2/28/26

Output:
🚚 Gross driver John Doe (2/1/2026 to 2/28/2026)
💰 Total: $5,250.00
[Excel file attached]
```

### Example 2: Single Day
```
/gross_dispatcher Sam 2/25/26-2/25/26

Output:
📊 Gross dispatcher Sam (2/25/2026 to 2/25/2026)
💰 Total: $1,500.00
[Excel file attached]
```

### Example 3: Year-to-Date
```
/export_driver Mary Johnson 1/1/26-12/31/26

Output:
🚚 Gross driver Mary Johnson (1/1/2026 to 12/31/2026)
💰 Total: $45,000.00
[Excel file: driver_Mary_Johnson_1/1/2026_to_12/31/2026.xlsx]
```

## Troubleshooting

### Issue: "Invalid date format"
**Solution**: Use format like `2/24/26-3/2/26` with a hyphen between dates

### Issue: No loads in report
**Solution**: 
1. Check that loads have DEL time field with valid dates
2. Verify date range is correct
3. Check driver/dispatcher name matches exactly

### Issue: $0.00 total
**Solution**: No loads found in that date range. Try different dates or check database.

### Issue: Database migration error
**Solution**: 
1. Backup your database.db file
2. Delete database.db
3. Run the bot again to create fresh database

## Performance Notes

- Date filtering works efficiently for typical load volumes (< 50,000 per driver)
- Dates with NULL values are automatically excluded from range queries
- Excel exports include filtered date column for reference

## Future Enhancements

Planned improvements:
- [ ] SQL-level date filtering for better performance
- [ ] Monthly/quarterly summary reports
- [ ] Date range validation (DEL > PU)
- [ ] Timezone support
- [ ] Visual date picker UI
- [ ] Email report scheduling

## Admin Features

- Notification of new loads saved
- Confirmation dialog for rate updates
- Admin-only rate update commands

## Dependencies

```
aiogram>=3.0.0           # Telegram bot framework
openpyxl>=3.0.0          # Excel file generation
python-dotenv>=0.19.0    # Environment variable management
```

See `requirements.txt` for complete list.

## Deployment

### Local Development
```bash
python main.py
```

### Production (Heroku)
```bash
git push heroku main
```

Requires:
- Heroku account
- Procfile (included)
- Environment variables set in Heroku config

## Documentation Files

| File | Purpose |
|------|---------|
| QUICK_START.md | User guide for new feature |
| DATE_FILTERING_GUIDE.md | Complete feature documentation |
| DATABASE_MIGRATION.md | Database schema changes |
| IMPLEMENTATION_REFERENCE.md | Technical implementation details |
| CHANGES_SUMMARY.md | Summary of all code changes |
| test_date_filtering.py | Automated test suite |

## Support

For issues or questions:
1. Check the [QUICK_START.md](QUICK_START.md) guide
2. Read [DATE_FILTERING_GUIDE.md](DATE_FILTERING_GUIDE.md) for detailed info
3. Review [IMPLEMENTATION_REFERENCE.md](IMPLEMENTATION_REFERENCE.md) for technical details
4. Run `python test_date_filtering.py` to verify setup

## Recent Changes (This Release) 📝

### New Features
✨ Date range filtering for gross reports  
✨ Automatic date extraction from load messages  
✨ Excel exports with date column  

### Code Changes
📝 Added `del_date` column to loads table  
📝 Enhanced parser with date extraction  
📝 Updated gross calculation functions  
📝 Improved command parsing for date ranges  

For complete list, see [CHANGES_SUMMARY.md](CHANGES_SUMMARY.md)

## License

[Add your license here]

## Contact

[Add contact information here]

---

**Last Updated**: March 4, 2026  
**Version**: 2.0 (Date Filtering Release)
