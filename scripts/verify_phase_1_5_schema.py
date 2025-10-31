#!/usr/bin/env python3
"""
Phase 1.5 Database Schema Verification Script

This script verifies that the database schema matches the Phase 1.5 requirements:
- All tables exist
- All Phase 1.5 columns are present
- Indexes are created
- Foreign keys are set up correctly

Usage:
    cd backend
    python ../scripts/verify_phase_1_5_schema.py
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import create_engine, inspect, text
from app.core.config import settings


def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_check(condition, success_msg, failure_msg):
    """Print check result with color"""
    if condition:
        print(f"✅ {success_msg}")
        return True
    else:
        print(f"❌ {failure_msg}")
        return False


def main():
    """Main verification function"""

    print_header("Phase 1.5 Database Schema Verification")

    # Connect to database
    try:
        engine = create_engine(settings.DATABASE_URL)
        inspector = inspect(engine)
        connection = engine.connect()
        print("✅ Connected to database")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return False

    all_checks_passed = True

    # =================================================================
    # Check 1: Verify all tables exist
    # =================================================================
    print_header("1. Checking Tables")

    expected_tables = [
        'users',
        'images',
        'templates',
        'template_preprocessing',  # Phase 1.5
        'batch_tasks',  # Phase 1.5
        'faceswap_tasks',
        'crawl_tasks',
        'alembic_version'
    ]

    existing_tables = inspector.get_table_names()

    for table in expected_tables:
        if not print_check(
            table in existing_tables,
            f"Table exists: {table}",
            f"Table missing: {table}"
        ):
            all_checks_passed = False

    # =================================================================
    # Check 2: Verify images table Phase 1.5 columns
    # =================================================================
    print_header("2. Verifying Images Table (Phase 1.5)")

    images_columns = {col['name']: col for col in inspector.get_columns('images')}

    phase_1_5_image_columns = [
        ('storage_type', 'Separated storage types'),
        ('expires_at', 'Auto-cleanup expiration'),
        ('session_id', 'Temporary photo grouping')
    ]

    for col_name, description in phase_1_5_image_columns:
        if not print_check(
            col_name in images_columns,
            f"Column exists: {col_name} ({description})",
            f"Column missing: {col_name} ({description})"
        ):
            all_checks_passed = False

    # Check indexes
    images_indexes = inspector.get_indexes('images')
    index_names = [idx['name'] for idx in images_indexes]

    for idx_name in ['ix_images_storage_type', 'ix_images_session']:
        if not print_check(
            idx_name in index_names,
            f"Index exists: {idx_name}",
            f"Index missing: {idx_name}"
        ):
            all_checks_passed = False

    # =================================================================
    # Check 3: Verify templates table Phase 1.5 columns
    # =================================================================
    print_header("3. Verifying Templates Table (Phase 1.5)")

    templates_columns = {col['name']: col for col in inspector.get_columns('templates')}

    phase_1_5_template_columns = [
        ('name', 'Renamed from title'),
        ('original_image_id', 'Renamed from image_id'),
        ('is_preprocessed', 'Preprocessing status'),
        ('male_face_count', 'Gender-specific count'),
        ('female_face_count', 'Gender-specific count'),
        ('updated_at', 'Track template updates')
    ]

    for col_name, description in phase_1_5_template_columns:
        if not print_check(
            col_name in templates_columns,
            f"Column exists: {col_name} ({description})",
            f"Column missing: {col_name} ({description})"
        ):
            all_checks_passed = False

    # Check that old columns are NOT present
    old_columns = ['title', 'image_id', 'artist', 'source_url', 'face_positions']
    for col_name in old_columns:
        if col_name in templates_columns:
            print(f"⚠️  Old column still exists: {col_name} (should be removed)")
            all_checks_passed = False

    # =================================================================
    # Check 4: Verify template_preprocessing table
    # =================================================================
    print_header("4. Verifying Template Preprocessing Table (Phase 1.5)")

    if 'template_preprocessing' not in existing_tables:
        print("❌ Template preprocessing table does not exist")
        all_checks_passed = False
    else:
        preprocessing_columns = {col['name']: col for col in inspector.get_columns('template_preprocessing')}

        required_preprocessing_columns = [
            'id',
            'template_id',
            'original_image_id',
            'faces_detected',
            'face_data',
            'masked_image_id',
            'preprocessing_status',
            'error_message',
            'processed_at',
            'created_at'
        ]

        for col_name in required_preprocessing_columns:
            if not print_check(
                col_name in preprocessing_columns,
                f"Column exists: {col_name}",
                f"Column missing: {col_name}"
            ):
                all_checks_passed = False

        # Check index
        preprocessing_indexes = inspector.get_indexes('template_preprocessing')
        index_names = [idx['name'] for idx in preprocessing_indexes]
        if not print_check(
            'ix_preprocessing_status' in index_names,
            "Index exists: ix_preprocessing_status",
            "Index missing: ix_preprocessing_status"
        ):
            all_checks_passed = False

    # =================================================================
    # Check 5: Verify batch_tasks table
    # =================================================================
    print_header("5. Verifying Batch Tasks Table (Phase 1.5)")

    if 'batch_tasks' not in existing_tables:
        print("❌ Batch tasks table does not exist")
        all_checks_passed = False
    else:
        batch_columns = {col['name']: col for col in inspector.get_columns('batch_tasks')}

        required_batch_columns = [
            'id',
            'batch_id',
            'user_id',
            'husband_photo_id',
            'wife_photo_id',
            'template_ids',
            'status',
            'total_tasks',
            'completed_tasks',
            'failed_tasks',
            'created_at',
            'completed_at'
        ]

        for col_name in required_batch_columns:
            if not print_check(
                col_name in batch_columns,
                f"Column exists: {col_name}",
                f"Column missing: {col_name}"
            ):
                all_checks_passed = False

        # Check index
        batch_indexes = inspector.get_indexes('batch_tasks')
        index_names = [idx['name'] for idx in batch_indexes]
        if not print_check(
            'ix_batch_status' in index_names,
            "Index exists: ix_batch_status",
            "Index missing: ix_batch_status"
        ):
            all_checks_passed = False

    # =================================================================
    # Check 6: Verify faceswap_tasks Phase 1.5 updates
    # =================================================================
    print_header("6. Verifying FaceSwap Tasks Table (Phase 1.5)")

    faceswap_columns = {col['name']: col for col in inspector.get_columns('faceswap_tasks')}

    phase_1_5_faceswap_columns = [
        ('task_id', 'Unique task identifier'),
        ('batch_id', 'Batch processing reference'),
        ('husband_photo_id', 'Renamed from husband_image_id'),
        ('wife_photo_id', 'Renamed from wife_image_id'),
        ('face_mappings', 'Custom face mapping'),
        ('use_preprocessed', 'Use preprocessed templates')
    ]

    for col_name, description in phase_1_5_faceswap_columns:
        if not print_check(
            col_name in faceswap_columns,
            f"Column exists: {col_name} ({description})",
            f"Column missing: {col_name} ({description})"
        ):
            all_checks_passed = False

    # Check that old columns are NOT present
    old_faceswap_columns = ['husband_image_id', 'wife_image_id']
    for col_name in old_faceswap_columns:
        if col_name in faceswap_columns:
            print(f"⚠️  Old column still exists: {col_name} (should be renamed)")
            all_checks_passed = False

    # Check indexes
    faceswap_indexes = inspector.get_indexes('faceswap_tasks')
    index_names = [idx['name'] for idx in faceswap_indexes]
    if not print_check(
        'ix_tasks_batch' in index_names,
        "Index exists: ix_tasks_batch",
        "Index missing: ix_tasks_batch"
    ):
        all_checks_passed = False

    # =================================================================
    # Check 7: Verify foreign keys
    # =================================================================
    print_header("7. Verifying Foreign Keys")

    # Check template_preprocessing foreign keys
    preprocessing_fks = inspector.get_foreign_keys('template_preprocessing')
    fk_referred_tables = [fk['referred_table'] for fk in preprocessing_fks]

    for table in ['templates', 'images']:
        if not print_check(
            table in fk_referred_tables,
            f"Foreign key to {table} exists",
            f"Foreign key to {table} missing"
        ):
            all_checks_passed = False

    # Check batch_tasks foreign keys
    batch_fks = inspector.get_foreign_keys('batch_tasks')
    fk_referred_tables = [fk['referred_table'] for fk in batch_fks]

    for table in ['users', 'images']:
        if not print_check(
            table in fk_referred_tables,
            f"Batch tasks foreign key to {table} exists",
            f"Batch tasks foreign key to {table} missing"
        ):
            all_checks_passed = False

    # Check faceswap_tasks foreign keys
    faceswap_fks = inspector.get_foreign_keys('faceswap_tasks')
    fk_referred_tables = [fk['referred_table'] for fk in faceswap_fks]

    for table in ['batch_tasks', 'templates', 'images', 'users']:
        if not print_check(
            table in fk_referred_tables,
            f"FaceSwap tasks foreign key to {table} exists",
            f"FaceSwap tasks foreign key to {table} missing"
        ):
            all_checks_passed = False

    # =================================================================
    # Check 8: Verify Alembic migration
    # =================================================================
    print_header("8. Verifying Alembic Migration")

    try:
        result = connection.execute(text("SELECT version_num FROM alembic_version"))
        version = result.fetchone()

        if version:
            version_num = version[0]
            print(f"✅ Alembic version: {version_num}")

            if version_num == '00f2e8fecd91':
                print("✅ Correct revision for Phase 1.5 initial schema")
            else:
                print(f"⚠️  Unexpected revision: {version_num}")
        else:
            print("❌ No alembic version found")
            all_checks_passed = False
    except Exception as e:
        print(f"❌ Error checking alembic version: {e}")
        all_checks_passed = False

    # =================================================================
    # Final Summary
    # =================================================================
    print_header("Verification Summary")

    if all_checks_passed:
        print("✅ All Phase 1.5 schema checks passed!")
        print("\n📋 Database is ready for Phase 1.5 development")
        print("\nNext steps:")
        print("  1. Implement separated upload APIs (Checkpoint 1.5.1)")
        print("  2. Implement template preprocessing (Checkpoint 1.5.2)")
        print("  3. Implement flexible face mapping (Checkpoint 1.5.3)")
        print("  4. Implement batch processing (Checkpoint 1.5.4)")
        print("  5. Implement auto-cleanup (Checkpoint 1.5.5)")
        print("\nRefer to: docs/PHASE-1.5-QUICK-REFERENCE.md")
        return True
    else:
        print("❌ Some schema checks failed")
        print("\nPlease review the errors above and:")
        print("  1. Check if migration was applied: cd backend && alembic current")
        print("  2. Re-run migration: ./scripts/apply_phase_1_5_migration.sh")
        print("  3. If needed, reset database and start fresh")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
