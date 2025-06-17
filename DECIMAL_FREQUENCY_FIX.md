# Decimal Frequency Fix Instructions

## Problem Fixed
The frequency_per_year column in the database was stored as INTEGER instead of REAL, causing decimal values like 1.5 to be rounded down to 1.

## Solution Applied
✅ **Database schema migrated** from INTEGER to REAL for frequency_per_year column
✅ **All existing data preserved** during migration
✅ **Decimal frequencies now supported** (1.5, 0.5, 0.33, etc.)

## What Was Done
1. **Database Migration**: Changed `frequency_per_year INTEGER` to `frequency_per_year REAL`
2. **Frontend Updates**: Added proper step and pattern attributes for decimal input
3. **Backend Validation**: Ensured float parsing throughout the application
4. **Migration Script**: Automatic detection and migration of existing databases

## To See the Changes
**You must restart your application** for the database changes to take effect:

### For Web Interface (FastAPI):
```bash
# Stop the current server (Ctrl+C)
# Then restart it
python web_app.py
```

### For Streamlit Interface:
```bash
# Stop the current server (Ctrl+C) 
# Then restart it
streamlit run streamlit_app.py
```

## Testing
You can now enter decimal frequencies like:
- **1.5** = every 1.5 years
- **0.5** = every 2 years  
- **0.33** = every 3 years
- **2.5** = 2.5 times per year

## Debug Scripts
Two scripts are available for troubleshooting:
- `debug_frequency.py` - Full database diagnosis and migration
- `test_frequency_update.py` - Test updating a service to decimal frequency

## Verification
The database now properly stores and retrieves decimal frequency values. The "Hand Surgeon" service has been updated to 1.5 as a test case.