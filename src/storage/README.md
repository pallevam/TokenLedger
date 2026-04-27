# Storage Module

This module is responsible for persisting token usage and limits to the database.

## Architecture
- **Supabase (PostgreSQL)**: We are using a PostgreSQL database, managed via self-hosted Supabase.
- **ORM (SQLAlchemy)**: `SQLAlchemy` is used as the Object-Relational Mapper to ensure type safety, robust query building, and easy migrations.

## Schema Highlights
- **`usage_logs`**: Stores individual records of LLM interactions, including token counts and computed costs.
- **`user_limits`**: Tracks user quotas and monthly budgets to prevent runaway costs.
