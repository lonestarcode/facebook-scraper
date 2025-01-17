"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-03-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create marketplace_listings table
    op.create_table(
        'marketplace_listings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('listing_id', sa.String(100), unique=True),
        sa.Column('title', sa.String(500)),
        sa.Column('price', sa.Float()),
        sa.Column('description', sa.Text()),
        sa.Column('location', sa.String(200)),
        sa.Column('category', sa.String(100)),
        sa.Column('seller_id', sa.String(100)),
        sa.Column('listing_url', sa.String(1000)),
        sa.Column('images', postgresql.JSON()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create listing_analyses table
    op.create_table(
        'listing_analyses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('listing_id', sa.Integer()),
        sa.Column('quality_score', sa.Float()),
        sa.Column('keywords', postgresql.JSON()),
        sa.Column('category_confidence', sa.Float()),
        sa.Column('analyzed_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['listing_id'], ['marketplace_listings.id'])
    )

def downgrade():
    op.drop_table('listing_analyses')
    op.drop_table('marketplace_listings') 