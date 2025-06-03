-- Initialize database for Personal Finance Dashboard
-- This script sets up the database with proper settings and extensions

-- Create database if it doesn't exist (run as superuser)
-- CREATE DATABASE finance_dashboard;

-- Connect to the database
\c finance_dashboard;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Set default timezone
SET timezone = 'UTC';

-- Create custom types if needed
DO $$ BEGIN
    CREATE TYPE transaction_type AS ENUM ('expense', 'income', 'transfer');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Set up performance optimization settings
ALTER DATABASE finance_dashboard SET shared_buffers = '256MB';
ALTER DATABASE finance_dashboard SET effective_cache_size = '1GB';
ALTER DATABASE finance_dashboard SET maintenance_work_mem = '64MB';
ALTER DATABASE finance_dashboard SET work_mem = '4MB';

-- Create indexes for better performance (these will be created by Django migrations, but listed here for reference)
-- CREATE INDEX IF NOT EXISTS idx_transaction_user_date ON expenses_transaction(user_id, date DESC);
-- CREATE INDEX IF NOT EXISTS idx_transaction_category ON expenses_transaction(category_id);
-- CREATE INDEX IF NOT EXISTS idx_budget_user_period ON budgets_budget(user_id, period_start, period_end);
-- CREATE INDEX IF NOT EXISTS idx_category_user_parent ON expenses_category(user_id, parent_id);

-- Grant necessary permissions (adjust username as needed)
-- GRANT ALL PRIVILEGES ON DATABASE finance_dashboard TO your_app_user;

-- Add comments for documentation
COMMENT ON DATABASE finance_dashboard IS 'Personal Finance Dashboard - Secure expense tracking and budget management';
