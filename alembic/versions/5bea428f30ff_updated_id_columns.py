"""updated id columns

Revision ID: 5bea428f30ff
Revises: d48c8d6a8155
Create Date: 2026-09-10 18:22:27.741693

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5bea428f30ff'
down_revision: Union[str, Sequence[str], None] = 'd48c8d6a8155'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "freelancer_skills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("freelancer_id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.Uuid(), nullable=False),
        sa.Column(
            "proficiency_level",
            sa.String(),
            nullable=False,
            server_default="INTERMEDIATE",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["freelancer_id"],
            ["freelancer_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"],
            ["skills.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_freelancer_skills_freelancer_id"),
        "freelancer_skills",
        ["freelancer_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_freelancer_skills_skill_id"),
        "freelancer_skills",
        ["skill_id"],
        unique=False,
    )

    op.create_table(
        "job_skills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"],
            ["skills.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_job_skills_job_id"),
        "job_skills",
        ["job_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_job_skills_skill_id"),
        "job_skills",
        ["skill_id"],
        unique=False,
    )
def downgrade() -> None:
    op.drop_index(
        op.f("ix_job_skills_skill_id"),
        table_name="job_skills",
    )
    op.drop_index(
        op.f("ix_job_skills_job_id"),
        table_name="job_skills",
    )
    op.drop_table("job_skills")

    op.drop_index(
        op.f("ix_freelancer_skills_skill_id"),
        table_name="freelancer_skills",
    )
    op.drop_index(
        op.f("ix_freelancer_skills_freelancer_id"),
        table_name="freelancer_skills",
    )
    op.drop_table("freelancer_skills")