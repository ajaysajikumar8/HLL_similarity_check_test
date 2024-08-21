from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b1bd3c57ae1d'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add the 'status' column with a default value and drop unnecessary columns
    with op.batch_alter_table('compositions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.Integer(), nullable=False, server_default='0'))
        batch_op.drop_column('packing_unit')
        batch_op.drop_column('unit_price')

    # Adjust the 'id' column in 'price_cap' table, dropping identity and setting it as an integer
    with op.batch_alter_table('price_cap', schema=None) as batch_op:
        # Drop the IDENTITY property from the 'id' column
        batch_op.execute('ALTER TABLE price_cap ALTER COLUMN id DROP IDENTITY IF EXISTS')
        
        # Remove the default value (if any) from the 'id' column
        batch_op.execute('ALTER TABLE price_cap ALTER COLUMN id DROP DEFAULT')
        
        # Change the 'id' column type to INTEGER
        batch_op.alter_column('id', type_=sa.Integer())

def downgrade():
    # Revert changes made to the 'id' column in 'price_cap' table
    with op.batch_alter_table('price_cap', schema=None) as batch_op:
        # Change the 'id' column back to INTEGER with IDENTITY and a default value
        batch_op.execute('ALTER TABLE price_cap ALTER COLUMN id SET DATA TYPE INTEGER')
        batch_op.execute('ALTER TABLE price_cap ALTER COLUMN id SET DEFAULT nextval(pg_get_serial_sequence(\'price_cap\', \'id\'))')
        batch_op.execute('ALTER TABLE price_cap ALTER COLUMN id ADD IDENTITY')

    # Revert the changes made to the 'compositions' table
    with op.batch_alter_table('compositions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('unit_price', sa.Numeric(), nullable=True))
        batch_op.add_column(sa.Column('packing_unit', sa.String(), nullable=True))
        batch_op.drop_column('status')
