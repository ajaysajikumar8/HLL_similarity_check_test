"""Rename priceCap table to price_cap_compositions

Revision ID: 9e9be651454e
Revises: 1a3fd941099b
Create Date: 2024-09-20 14:51:01.239047

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9e9be651454e'
down_revision = '1a3fd941099b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('price_cap')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('price_cap',
    sa.Column('compositions', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('strength', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('dosage_form', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('packing_unit', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('price_cap', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('compositions_striped', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('composition_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['composition_id'], ['compositions.id'], name='price_cap_composition_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='price_cap_pkey')
    )
    # ### end Alembic commands ###
