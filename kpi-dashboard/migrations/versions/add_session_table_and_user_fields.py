"""add session table and user fields for authentication

Revision ID: g0b1c2d3e4f5
Revises: f9a1c2d3e4b5
Create Date: 2025-11-04 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'g0b1c2d3e4f5'
down_revision = 'f9a1c2d3e4b5'
branch_labels = None
depends_on = None


def upgrade():
    """Add session table and user authentication fields"""
    
    # Create sessions table for Flask-Session
    op.create_table(
        'sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('session_id', sa.String(255), unique=True, nullable=False),
        sa.Column('data', sa.LargeBinary(), nullable=True),
        sa.Column('expiry', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.user_id'), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_activity', sa.DateTime(), server_default=sa.func.now()),
    )
    
    # Create indexes for sessions table
    op.create_index('idx_session_session_id', 'sessions', ['session_id'])
    op.create_index('idx_session_expiry', 'sessions', ['expiry'])
    op.create_index('idx_session_user', 'sessions', ['user_id'])
    
    # Add authentication fields to users table
    try:
        op.add_column('users', sa.Column('active', sa.Boolean(), default=True))
    except:
        print("  ⚠️  Column 'active' may already exist")
    
    try:
        op.add_column('users', sa.Column('last_login', sa.DateTime(), nullable=True))
    except:
        print("  ⚠️  Column 'last_login' may already exist")
    
    print("✅ Session table created")
    print("✅ User authentication fields added")


def downgrade():
    """Remove session table and user fields"""
    
    # Drop indexes
    op.drop_index('idx_session_user', 'sessions')
    op.drop_index('idx_session_expiry', 'sessions')
    op.drop_index('idx_session_session_id', 'sessions')
    
    # Drop sessions table
    op.drop_table('sessions')
    
    # Remove authentication fields from users
    op.drop_column('users', 'last_login')
    op.drop_column('users', 'active')
    
    print("⚠️  Rolled back: Session table and user fields removed")

