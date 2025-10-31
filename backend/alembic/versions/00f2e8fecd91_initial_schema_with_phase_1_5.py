"""Initial schema with Phase 1.5 features

Revision ID: 00f2e8fecd91
Revises:
Create Date: 2025-10-31

This migration creates the complete database schema including Phase 1.5 features:
- Users, images, templates with preprocessing support
- FaceSwap tasks with batch processing and flexible mapping
- Template preprocessing system
- Batch task management
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '00f2e8fecd91'
down_revision = None  # This is the first migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all database tables with Phase 1.5 features"""

    # =================================================================
    # 1. Create users table
    # =================================================================
    print("Creating users table...")
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    # =================================================================
    # 2. Create images table (with Phase 1.5 storage features)
    # =================================================================
    print("Creating images table...")
    op.create_table('images',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('image_type', sa.String(length=20), nullable=True),  # 'photo', 'template', 'preprocessed', 'result'
        sa.Column('storage_type', sa.String(length=20), nullable=True),  # 'permanent', 'temporary'
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),  # Phase 1.5: Auto-cleanup
        sa.Column('session_id', sa.String(length=100), nullable=True),  # Phase 1.5: Group temp photos
        sa.Column('image_metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_images_image_type', 'images', ['image_type'], unique=False)
    op.create_index('ix_images_storage_type', 'images', ['storage_type'], unique=False)
    op.create_index('ix_images_session', 'images', ['session_id'], unique=False)

    # =================================================================
    # 3. Create templates table (with Phase 1.5 preprocessing features)
    # =================================================================
    print("Creating templates table...")
    op.create_table('templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),  # Phase 1.5: Renamed from 'title'
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('original_image_id', sa.Integer(), nullable=False),  # Phase 1.5: Renamed from 'image_id'
        sa.Column('is_preprocessed', sa.Boolean(), nullable=True),  # Phase 1.5: Preprocessing status
        sa.Column('face_count', sa.Integer(), nullable=True),
        sa.Column('male_face_count', sa.Integer(), nullable=True),  # Phase 1.5: Gender-specific counts
        sa.Column('female_face_count', sa.Integer(), nullable=True),  # Phase 1.5: Gender-specific counts
        sa.Column('popularity_score', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),  # Phase 1.5: Track updates
        sa.ForeignKeyConstraint(['original_image_id'], ['images.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # =================================================================
    # 4. Create template_preprocessing table (Phase 1.5)
    # =================================================================
    print("Creating template_preprocessing table...")
    op.create_table('template_preprocessing',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('original_image_id', sa.Integer(), nullable=False),
        sa.Column('faces_detected', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('face_data', sa.JSON(), nullable=False),  # Face info (bbox, gender, landmarks)
        sa.Column('masked_image_id', sa.Integer(), nullable=True),
        sa.Column('preprocessing_status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['template_id'], ['templates.id'], ),
        sa.ForeignKeyConstraint(['original_image_id'], ['images.id'], ),
        sa.ForeignKeyConstraint(['masked_image_id'], ['images.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('template_id')
    )
    op.create_index('ix_preprocessing_status', 'template_preprocessing', ['preprocessing_status'], unique=False)

    # =================================================================
    # 5. Create batch_tasks table (Phase 1.5)
    # =================================================================
    print("Creating batch_tasks table...")
    op.create_table('batch_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('batch_id', sa.String(length=100), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('husband_photo_id', sa.Integer(), nullable=False),
        sa.Column('wife_photo_id', sa.Integer(), nullable=False),
        sa.Column('template_ids', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('total_tasks', sa.Integer(), nullable=False),
        sa.Column('completed_tasks', sa.Integer(), server_default='0', nullable=False),
        sa.Column('failed_tasks', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['husband_photo_id'], ['images.id'], ),
        sa.ForeignKeyConstraint(['wife_photo_id'], ['images.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('batch_id')
    )
    op.create_index('ix_batch_status', 'batch_tasks', ['status'], unique=False)

    # =================================================================
    # 6. Create faceswap_tasks table (with Phase 1.5 features)
    # =================================================================
    print("Creating faceswap_tasks table...")
    op.create_table('faceswap_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.String(length=100), nullable=False),  # Phase 1.5: Unique task ID
        sa.Column('batch_id', sa.String(length=100), nullable=True),  # Phase 1.5: Batch processing
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('husband_photo_id', sa.Integer(), nullable=False),  # Phase 1.5: Renamed from husband_image_id
        sa.Column('wife_photo_id', sa.Integer(), nullable=False),  # Phase 1.5: Renamed from wife_image_id
        sa.Column('result_image_id', sa.Integer(), nullable=True),
        sa.Column('face_mappings', sa.JSON(), nullable=True),  # Phase 1.5: Custom face mapping
        sa.Column('use_preprocessed', sa.Boolean(), nullable=True),  # Phase 1.5: Use preprocessed templates
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('progress', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('processing_time', sa.Float(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['batch_id'], ['batch_tasks.batch_id'], ),
        sa.ForeignKeyConstraint(['husband_photo_id'], ['images.id'], ),
        sa.ForeignKeyConstraint(['result_image_id'], ['images.id'], ),
        sa.ForeignKeyConstraint(['template_id'], ['templates.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['wife_photo_id'], ['images.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id')
    )
    op.create_index('ix_faceswap_tasks_status', 'faceswap_tasks', ['status'], unique=False)
    op.create_index('ix_tasks_batch', 'faceswap_tasks', ['batch_id'], unique=False)

    # =================================================================
    # 7. Create crawl_tasks table (for Phase 3+)
    # =================================================================
    print("Creating crawl_tasks table...")
    op.create_table('crawl_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=True),
        sa.Column('search_query', sa.String(), nullable=True),
        sa.Column('filters', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('images_collected', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    print("✅ All tables created successfully with Phase 1.5 features!")


def downgrade() -> None:
    """Drop all tables"""
    print("Dropping all tables...")

    op.drop_table('crawl_tasks')

    op.drop_index('ix_tasks_batch', table_name='faceswap_tasks')
    op.drop_index('ix_faceswap_tasks_status', table_name='faceswap_tasks')
    op.drop_table('faceswap_tasks')

    op.drop_index('ix_batch_status', table_name='batch_tasks')
    op.drop_table('batch_tasks')

    op.drop_index('ix_preprocessing_status', table_name='template_preprocessing')
    op.drop_table('template_preprocessing')

    op.drop_table('templates')

    op.drop_index('ix_images_session', table_name='images')
    op.drop_index('ix_images_storage_type', table_name='images')
    op.drop_index('ix_images_image_type', table_name='images')
    op.drop_table('images')

    op.drop_index('ix_users_username', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')

    print("✅ All tables dropped!")
