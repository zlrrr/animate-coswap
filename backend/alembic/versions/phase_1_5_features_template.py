"""Add Phase 1.5 enhanced features

Revision ID: phase_1_5_features
Revises: bc7a249e6a4d
Create Date: 2025-10-31

This migration adds support for Phase 1.5 features:
- Separated storage for photos (temporary) and templates (permanent)
- Template preprocessing system
- Batch processing
- Flexible face mapping
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


# revision identifiers, used by Alembic.
revision = 'phase_1_5_features'
down_revision = 'bc7a249e6a4d'  # Update this to your last migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema"""

    # =================================================================
    # 1. Update images table - add new columns
    # =================================================================
    print("Updating images table...")
    op.add_column('images', sa.Column('storage_type', sa.String(length=20), server_default='permanent', nullable=False))
    op.add_column('images', sa.Column('expires_at', sa.DateTime(), nullable=True))
    op.add_column('images', sa.Column('session_id', sa.String(length=100), nullable=True))

    # Create indexes
    op.create_index('ix_images_storage_type', 'images', ['storage_type'], unique=False)
    op.create_index('ix_images_session', 'images', ['session_id'], unique=False)

    # =================================================================
    # 2. Update templates table
    # =================================================================
    print("Updating templates table...")

    # Rename columns
    op.alter_column('templates', 'title', new_column_name='name')
    op.alter_column('templates', 'image_id', new_column_name='original_image_id')

    # Add new columns
    op.add_column('templates', sa.Column('is_preprocessed', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('templates', sa.Column('male_face_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('templates', sa.Column('female_face_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('templates', sa.Column('updated_at', sa.DateTime(), nullable=True))

    # Remove old columns that are no longer needed
    op.drop_column('templates', 'artist')
    op.drop_column('templates', 'source_url')
    op.drop_column('templates', 'face_positions')

    # =================================================================
    # 3. Create template_preprocessing table
    # =================================================================
    print("Creating template_preprocessing table...")
    op.create_table('template_preprocessing',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('original_image_id', sa.Integer(), nullable=False),
        sa.Column('faces_detected', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('face_data', sa.JSON(), nullable=False),
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
    # 4. Create batch_tasks table
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
    # 5. Update faceswap_tasks table
    # =================================================================
    print("Updating faceswap_tasks table...")

    # Step 1: Add task_id column as nullable first
    op.add_column('faceswap_tasks', sa.Column('task_id', sa.String(length=100), nullable=True))

    # Step 2: Generate UUIDs for existing rows
    print("Generating task_ids for existing rows...")
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE faceswap_tasks
        SET task_id = 'task_' || id || '_' || substr(md5(random()::text), 1, 8)
        WHERE task_id IS NULL
    """))

    # Step 3: Now make it NOT NULL and UNIQUE
    op.alter_column('faceswap_tasks', 'task_id', nullable=False)
    op.create_unique_constraint('uq_faceswap_tasks_task_id', 'faceswap_tasks', ['task_id'])

    # Add other new columns
    op.add_column('faceswap_tasks', sa.Column('batch_id', sa.String(length=100), nullable=True))
    op.add_column('faceswap_tasks', sa.Column('face_mappings', sa.JSON(), nullable=True))
    op.add_column('faceswap_tasks', sa.Column('use_preprocessed', sa.Boolean(), server_default='true', nullable=False))

    # Rename columns
    op.alter_column('faceswap_tasks', 'husband_image_id', new_column_name='husband_photo_id')
    op.alter_column('faceswap_tasks', 'wife_image_id', new_column_name='wife_photo_id')

    # Add foreign key for batch_id
    op.create_foreign_key('fk_faceswap_tasks_batch_id', 'faceswap_tasks', 'batch_tasks', ['batch_id'], ['batch_id'])
    op.create_index('ix_tasks_batch', 'faceswap_tasks', ['batch_id'], unique=False)

    print("Migration completed successfully!")


def downgrade() -> None:
    """Downgrade database schema"""

    # Reverse all changes
    print("Downgrading faceswap_tasks table...")
    op.drop_index('ix_tasks_batch', table_name='faceswap_tasks')
    op.drop_constraint('fk_faceswap_tasks_batch_id', 'faceswap_tasks', type_='foreignkey')
    op.alter_column('faceswap_tasks', 'husband_photo_id', new_column_name='husband_image_id')
    op.alter_column('faceswap_tasks', 'wife_photo_id', new_column_name='wife_image_id')
    op.drop_column('faceswap_tasks', 'use_preprocessed')
    op.drop_column('faceswap_tasks', 'face_mappings')
    op.drop_column('faceswap_tasks', 'batch_id')
    op.drop_constraint('uq_faceswap_tasks_task_id', 'faceswap_tasks', type_='unique')
    op.drop_column('faceswap_tasks', 'task_id')

    print("Dropping batch_tasks table...")
    op.drop_index('ix_batch_status', table_name='batch_tasks')
    op.drop_table('batch_tasks')

    print("Dropping template_preprocessing table...")
    op.drop_index('ix_preprocessing_status', table_name='template_preprocessing')
    op.drop_table('template_preprocessing')

    print("Reverting templates table...")
    op.add_column('templates', sa.Column('face_positions', sa.JSON(), nullable=True))
    op.add_column('templates', sa.Column('source_url', sa.String(length=500), nullable=True))
    op.add_column('templates', sa.Column('artist', sa.String(length=255), nullable=True))
    op.drop_column('templates', 'updated_at')
    op.drop_column('templates', 'female_face_count')
    op.drop_column('templates', 'male_face_count')
    op.drop_column('templates', 'is_preprocessed')
    op.alter_column('templates', 'original_image_id', new_column_name='image_id')
    op.alter_column('templates', 'name', new_column_name='title')

    print("Reverting images table...")
    op.drop_index('ix_images_session', table_name='images')
    op.drop_index('ix_images_storage_type', table_name='images')
    op.drop_column('images', 'session_id')
    op.drop_column('images', 'expires_at')
    op.drop_column('images', 'storage_type')

    print("Downgrade completed!")
