"""Ajout du champ timezone dans User

Revision ID: 9b848647e235
Revises: 290ea024f62c
Create Date: 2025-03-18 02:03:05.842940

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9b848647e235'
down_revision = '290ea024f62c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('timezone', sa.String(length=50), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('timezone')

    # ### end Alembic commands ###
