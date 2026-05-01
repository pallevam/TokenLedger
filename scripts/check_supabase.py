"""
TokenLedger - Async Database Connection Health Check
-----------------------------------------------------
Verifies:
  1. Async SQLAlchemy + asyncpg can connect to Supabase Postgres
  2. The `usage_logs` and `user_limits` tables exist (created by init_db)
  3. Supabase Python SDK can authenticate

Usage:
    python scripts/check_supabase.py

Prerequisites:
    - .env file exists with DATABASE_URL pointing at Supabase (postgresql+asyncpg://)
    - pip install -r requirements.txt
"""

import sys
import os
import asyncio

# Load .env before anything else
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed. Run: pip install python-dotenv")
    sys.exit(1)


# ─────────────────────────────────────────────
# 1. Async SQLAlchemy → Supabase Postgres check
# ─────────────────────────────────────────────
async def check_sqlalchemy() -> bool:
    print("\n🔌  [1/3] Testing async SQLAlchemy → Supabase Postgres connection...")

    db_url = os.getenv("DATABASE_URL", "")

    if not db_url or db_url.startswith("sqlite"):
        print("   ⚠️  DATABASE_URL is set to SQLite (or missing).")
        print("   👉 Update .env:")
        print("      DATABASE_URL=postgresql+asyncpg://postgres:[PASSWORD]@db.<ref>.supabase.co:5432/postgres")
        return False

    # Auto-upgrade plain postgresql:// → postgresql+asyncpg://
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        print("   ℹ️  Auto-upgraded URL dialect to postgresql+asyncpg://")

    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text

        engine = create_async_engine(db_url, connect_args={"timeout": 10})
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"   ✅ Connected!  PostgreSQL version: {version}")
        await engine.dispose()
        return True
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        print("\n   Common fixes:")
        print("   • Wrong password in DATABASE_URL")
        print("   • Use port 5432 (direct), NOT 6543 (PgBouncer/pooler)")
        print("   • Check: Supabase Dashboard → Settings → Database → Connection string (URI tab)")
        return False


# ─────────────────────────────────────────────
# 2. Table existence check
# ─────────────────────────────────────────────
async def check_tables() -> bool:
    print("\n🗂️   [2/3] Checking that ORM tables exist in Supabase...")

    db_url = os.getenv("DATABASE_URL", "")
    if not db_url or db_url.startswith("sqlite"):
        print("   ⏭️  Skipped (no Postgres URL configured).")
        return False

    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    expected_tables = {"usage_logs", "user_limits"}

    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text

        engine = create_async_engine(db_url)
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' "
                    "AND tablename = ANY(:tables)"
                ),
                {"tables": list(expected_tables)},
            )
            found = {row[0] for row in result}

        await engine.dispose()

        missing = expected_tables - found
        if missing:
            print(f"   ⚠️  Missing tables: {missing}")
            print("   👉 Run the app once so the lifespan hook calls init_db(), or run:")
            print("      python -c \"import asyncio; from src.storage.database import PostgresStorage; asyncio.run(PostgresStorage().init_db())\"")
            return False
        else:
            print(f"   ✅ Tables present: {found}")
            return True
    except Exception as e:
        print(f"   ❌ Table check failed: {e}")
        return False


# ─────────────────────────────────────────────
# 3. Supabase SDK check
# ─────────────────────────────────────────────
def check_supabase_sdk() -> bool:
    print("\n🔑  [3/3] Testing Supabase SDK connection...")
    url = os.getenv("SUPABASE_URL", "")
    # Support both the new key name and the legacy fallback
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")

    if not url or not key or key in ("your-publishable-key-here", "your-anon-key-here"):
        print("   ⚠️  SUPABASE_PUBLISHABLE_KEY not set in .env")
        print("   👉 Supabase Dashboard → Settings → API Keys → Publishable key")
        print("      (This replaced the old 'anon' key — click the new tab, not Legacy)")
        return False

    try:
        from supabase import create_client
        client = create_client(url, key)
        response = client.auth.get_session()
        print(f"   ✅ SDK connected to {url}")
        print(f"   ℹ️  Session: {'Active' if response else 'No active session (expected for publishable key)'}")
        return True
    except Exception as e:
        print(f"   ❌ SDK connection failed: {e}")
        print("\n   Common fixes:")
        print("   • Use the Publishable key (not Secret key) from Settings → API Keys")
        print("   • SUPABASE_URL should be: https://<project-ref>.supabase.co")
        return False



# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
async def main():
    print("=" * 58)
    print("  TokenLedger — Async DB Connection Health Check")
    print("=" * 58)

    r1 = await check_sqlalchemy()
    r2 = await check_tables() if r1 else False
    r3 = check_supabase_sdk()

    print("\n" + "=" * 58)
    print("  Summary")
    print("=" * 58)
    print(f"  Async SQLAlchemy (asyncpg): {'✅ OK' if r1 else '❌ FAIL'}")
    print(f"  ORM tables exist:           {'✅ OK' if r2 else '❌ FAIL / SKIPPED'}")
    print(f"  Supabase SDK:               {'✅ OK' if r3 else '❌ FAIL'}")
    print("=" * 58)

    if not (r1 and r2 and r3):
        print("\n  ⚠️  Fix the issues above and re-run this script.")
        sys.exit(1)
    else:
        print("\n  🎉 All checks passed! You're good to go.\n")


if __name__ == "__main__":
    asyncio.run(main())
