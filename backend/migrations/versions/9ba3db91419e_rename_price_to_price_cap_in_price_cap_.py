"""Rename price to price_cap in price_cap_implants table

Revision ID: 9ba3db91419e
Revises: 9e9be651454e
Create Date: 2024-09-20 16:28:53.216155

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '9ba3db91419e'
down_revision = '9e9be651454e'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    """Helper function to check if a column exists in a table."""
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade():
    # Check if the 'price' column exists and the 'price_cap' column doesn't exist
    if column_exists('price_cap_implants', 'price') and not column_exists('price_cap_implants', 'price_cap'):
        with op.batch_alter_table('price_cap_implants', schema=None) as batch_op:
            batch_op.add_column(sa.Column('price_cap', sa.Numeric(), nullable=True))
            batch_op.drop_column('price')


def downgrade():
    # Check if the 'price_cap' column exists and the 'price' column doesn't exist
    if column_exists('price_cap_implants', 'price_cap') and not column_exists('price_cap_implants', 'price'):
        with op.batch_alter_table('price_cap_implants', schema=None) as batch_op:
            batch_op.add_column(sa.Column('price', sa.Numeric(), nullable=True))
            batch_op.drop_column('price_cap')

