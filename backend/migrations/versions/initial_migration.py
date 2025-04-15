"""Initial database schema

Revision ID: 001_initial
Revises: 
Create Date: 2023-04-14 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('username', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('email', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(50), nullable=True),
        sa.Column('last_name', sa.String(50), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_admin', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    
    # Create API Keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('key', sa.String(64), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
    )
    
    # Create user_auth table for session tokens
    op.create_table(
        'user_auth',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token', sa.String(255), nullable=False, index=True),
        sa.Column('token_type', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('device_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
    )
    
    # Create listings table
    op.create_table(
        'listings',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('listing_id', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('price_text', sa.String(128), nullable=True),
        sa.Column('location', sa.String(255), nullable=True, index=True),
        sa.Column('category', sa.String(255), nullable=True, index=True),
        sa.Column('url', sa.String(1024), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('scraped_at', sa.DateTime(), nullable=False),
        sa.Column('search_term', sa.String(255), nullable=True),
        sa.Column('status', sa.Enum('NEW', 'PROCESSED', 'MATCHED', 'ARCHIVED', 'ERROR', name='listing_status'), default='NEW'),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    
    # Create listing_images table
    op.create_table(
        'listing_images',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('listing_id', sa.Integer(), sa.ForeignKey('listings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('url', sa.String(1024), nullable=False),
        sa.Column('position', sa.Integer(), default=0),
        sa.Column('downloaded', sa.Boolean(), default=False),
        sa.Column('local_path', sa.String(1024), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )
    
    # Create search_terms table
    op.create_table(
        'search_terms',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('term', sa.String(255), unique=True, nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('total_listings_found', sa.Integer(), default=0),
    )
    
    # Create alerts table
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('search_query', sa.String(512), nullable=False),
        sa.Column('min_price', sa.Float(), nullable=True),
        sa.Column('max_price', sa.Float(), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('radius_miles', sa.Integer(), nullable=True),
        sa.Column('categories', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notification_email', sa.String(255), nullable=True),
        sa.Column('notification_sms', sa.String(50), nullable=True),
        sa.Column('notify_immediately', sa.Boolean(), default=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_matched_at', sa.DateTime(), nullable=True),
    )
    
    # Create listing_alerts table (for many-to-many relationship)
    op.create_table(
        'listing_alerts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('listing_id', sa.Integer(), sa.ForeignKey('listings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('alert_id', sa.Integer(), sa.ForeignKey('alerts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('matched_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('notified', sa.Boolean(), default=False),
        sa.Column('notified_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('listing_id', 'alert_id', name='uq_listing_alert'),
    )
    
    # Create price_alerts table
    op.create_table(
        'price_alerts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('search_term', sa.String(255), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('min_price', sa.Float(), nullable=True),
        sa.Column('max_price', sa.Float(), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('notification_method', sa.Enum('email', 'sms', 'push', name='notification_methods'), default='email'),
        sa.Column('notification_target', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('last_triggered', sa.DateTime(), nullable=True),
    )
    
    # Create alert_history table
    op.create_table(
        'alert_history',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('alert_id', sa.Integer(), sa.ForeignKey('price_alerts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('listing_id', sa.Integer(), sa.ForeignKey('listings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('triggered_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('notification_sent', sa.Boolean(), default=False),
        sa.Column('notification_time', sa.DateTime(), nullable=True),
    )
    
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), default='pending'),
    )
    
    # Create indexes
    op.create_index('idx_listings_price', 'listings', ['price'])
    op.create_index('idx_listings_scraped_at', 'listings', ['scraped_at'])
    op.create_index('idx_alerts_user_id', 'alerts', ['user_id'])
    op.create_index('idx_price_alerts_user_id', 'price_alerts', ['user_id'])
    op.create_index('idx_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('idx_notifications_created_at', 'notifications', ['created_at'])
    op.create_index('idx_notifications_status', 'notifications', ['status'])
    op.create_index('idx_user_auth_user_id', 'user_auth', ['user_id'])
    op.create_index('idx_api_keys_user_id', 'api_keys', ['user_id'])
    

def downgrade() -> None:
    # Drop all tables in reverse order
    op.drop_table('notifications')
    op.drop_table('alert_history')
    op.drop_table('price_alerts')
    op.drop_table('listing_alerts')
    op.drop_table('alerts')
    op.drop_table('search_terms')
    op.drop_table('listing_images')
    op.drop_table('listings')
    op.drop_table('user_auth')
    op.drop_table('api_keys')
    op.drop_table('users')
    
    # Drop custom types
    op.execute('DROP TYPE IF EXISTS listing_status')
    op.execute('DROP TYPE IF EXISTS notification_methods') 