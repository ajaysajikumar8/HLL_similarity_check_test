from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b1bd3c57ae1d'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add column with default value
    with op.batch_alter_table('compositions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.Integer(), nullable=False, server_default='0'))
        batch_op.drop_column('packing_unit')
        batch_op.drop_column('unit_price')

    # Handle identity column adjustments
    with op.batch_alter_table('price_cap', schema=None) as batch_op:
        batch_op.execute('ALTER TABLE price_cap ALTER COLUMN id DROP IDENTITY')
        batch_op.execute('ALTER TABLE price_cap ALTER COLUMN id DROP DEFAULT')
        batch_op.execute('ALTER TABLE price_cap ALTER COLUMN id SET DATA TYPE INTEGER')

def downgrade():
    # Reverse changes in downgrade
    with op.batch_alter_table('price_cap', schema=None) as batch_op:
        batch_op.execute('ALTER TABLE price_cap ALTER COLUMN id SET DATA TYPE INTEGER')
        batch_op.execute('ALTER TABLE price_cap ALTER COLUMN id SET DEFAULT nextval(pg_get_serial_sequence(\'price_cap\', \'id\'))')
        batch_op.execute('ALTER TABLE price_cap ALTER COLUMN id ADD IDENTITY')

    with op.batch_alter_table('compositions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('unit_price', sa.NUMERIC(), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('packing_unit', sa.VARCHAR(), autoincrement=False, nullable=True))
        batch_op.drop_column('status')
