# Database Migration: Analysis Weights Support

## Overview

This migration adds support for analysis weighting configuration to the database schema. It adds two new columns to the `stock_analyses` table:

1. `business_type` - Stores the detected or user-selected business type (e.g., 'bank', 'reit', 'technology')
2. `analysis_weights` - Stores the analysis weights configuration as JSON

## Migration Script

Run the migration script to update your existing SQLite database:

```bash
cd backend
python scripts/migrate_add_analysis_weights.py
```

Or specify a custom database path:

```bash
python scripts/migrate_add_analysis_weights.py path/to/your/database.db
```

## What Changed

### SQLite Database

**New Columns:**
- `business_type` (VARCHAR(50), nullable, indexed)
- `analysis_weights` (JSON, nullable)

The migration script:
- Adds the columns if they don't exist
- Creates an index on `business_type` for faster queries
- Is idempotent (safe to run multiple times)

### DynamoDB

DynamoDB is schema-less, so no migration is needed. The `DynamoDBService` has been updated to:
- Store `business_type` as a string attribute
- Store `analysis_weights` as a JSON string attribute

### Database Services

Both `DatabaseService` (SQLite) and `DynamoDBService` have been updated to:
- Save `business_type` and `analysis_weights` when storing analyses
- Retrieve these fields when reading analyses

## Backward Compatibility

- Existing analyses without these fields will have `NULL` values (which is fine)
- The application handles missing fields gracefully
- New analyses will automatically include these fields

## Verification

After running the migration, verify it worked:

```python
from app.database.db_service import DatabaseService

db = DatabaseService()
# Check if columns exist
session = db.get_session()
result = session.execute("PRAGMA table_info(stock_analyses)")
columns = [row[1] for row in result]
print("Columns:", columns)
assert 'business_type' in columns
assert 'analysis_weights' in columns
```

## Rollback

If you need to rollback (remove the columns):

```sql
-- SQLite only - DynamoDB doesn't need rollback
ALTER TABLE stock_analyses DROP COLUMN business_type;
ALTER TABLE stock_analyses DROP COLUMN analysis_weights;
```

**Note:** SQLite doesn't support `DROP COLUMN` directly. You would need to:
1. Create a new table without the columns
2. Copy data from old table
3. Drop old table
4. Rename new table

This is rarely needed since the columns are nullable and don't break existing functionality.

## Related Documentation

- [Analysis Weights Configuration](../backend/app/config/analysis_weights.py)
- [Database Guide](./DATABASE_GUIDE.md)
- [DynamoDB Setup](./DYNAMODB_SETUP.md)

