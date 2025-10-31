#!/usr/bin/env python3
"""
Test script to verify Settings configuration loads correctly
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

def test_settings_load():
    """Test that settings can be loaded without validation errors"""
    try:
        from app.core.config import settings

        print("✅ Settings loaded successfully!")
        print("\nConfiguration values:")
        print(f"  DATABASE_URL: {settings.DATABASE_URL}")
        print(f"  REDIS_URL: {settings.REDIS_URL}")
        print(f"  PROJECT_NAME: {settings.PROJECT_NAME}")
        print(f"  VERSION: {settings.VERSION}")
        print(f"  STORAGE_TYPE: {settings.STORAGE_TYPE}")
        print(f"  MODELS_PATH: {settings.MODELS_PATH}")
        print(f"  ACCELERATION_PROVIDER: {settings.ACCELERATION_PROVIDER}")
        print(f"  SECRET_KEY: {'*' * len(settings.SECRET_KEY)}")  # Hide secret
        print(f"  ALGORITHM: {settings.ALGORITHM}")
        print(f"  ACCESS_TOKEN_EXPIRE_MINUTES: {settings.ACCESS_TOKEN_EXPIRE_MINUTES}")

        return True

    except Exception as e:
        print(f"❌ Failed to load settings: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_alembic_env():
    """Test that alembic env.py can import settings"""
    try:
        # Change to backend directory
        os.chdir(os.path.join(os.path.dirname(__file__), '..', 'backend'))

        # Try to import the alembic env module
        sys.path.insert(0, os.path.join(os.getcwd(), 'alembic'))

        # This simulates what alembic does
        from app.core.config import settings
        from app.models.database import Base

        print("\n✅ Alembic environment imports work!")
        print(f"  Base metadata: {Base.metadata}")
        print(f"  Number of tables: {len(Base.metadata.tables)}")
        if Base.metadata.tables:
            print(f"  Tables: {', '.join(Base.metadata.tables.keys())}")

        return True

    except Exception as e:
        print(f"\n❌ Failed to import alembic environment: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("  Testing Settings Configuration")
    print("=" * 70)

    result1 = test_settings_load()
    result2 = test_alembic_env()

    print("\n" + "=" * 70)
    if result1 and result2:
        print("✅ All configuration tests passed!")
        print("=" * 70)
        sys.exit(0)
    else:
        print("❌ Some configuration tests failed")
        print("=" * 70)
        sys.exit(1)
