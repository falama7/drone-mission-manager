"""Initial migration

Revision ID: 431d5844ec0b
Revises: 
Create Date: 2025-05-13 05:47:13.870673

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '431d5844ec0b'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('missions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.Column('flight_date', sa.Date(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('missions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_missions_name'), ['name'], unique=False)

    op.create_table('files',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('mission_id', sa.Integer(), nullable=False),
    sa.Column('filename', sa.String(length=256), nullable=False),
    sa.Column('file_path', sa.String(length=512), nullable=False),
    sa.Column('file_type', sa.String(length=64), nullable=False),
    sa.Column('file_size', sa.Integer(), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['mission_id'], ['missions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('mission_metadata',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('mission_id', sa.Integer(), nullable=False),
    sa.Column('area_covered', sa.Float(), nullable=True),
    sa.Column('center_latitude', sa.Float(), nullable=True),
    sa.Column('center_longitude', sa.Float(), nullable=True),
    sa.Column('min_altitude', sa.Float(), nullable=True),
    sa.Column('max_altitude', sa.Float(), nullable=True),
    sa.Column('drone_model', sa.String(length=64), nullable=True),
    sa.Column('camera_model', sa.String(length=64), nullable=True),
    sa.Column('flight_duration', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['mission_id'], ['missions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('mission_metadata')
    op.drop_table('files')
    with op.batch_alter_table('missions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_missions_name'))

    op.drop_table('missions')
    # ### end Alembic commands ###
