"""University tracking / roadmap tables.

Reconstructs revision 013_discovery_tracking, which was applied to the shared
database from an uncommitted working tree. Schema copied from live Postgres:
roadmap_sections, tracked_universities, roadmap_steps (integer user_id FKs
into the leftover users table).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_discovery_tracking"
down_revision: Union[str, None] = "012_goal_centric"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    have = _table_names()
    # Discovery rows FK to users(id). That table is a leftover from an older
    # app on the shared database and is not created by 001–012.
    if "users" not in have:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        )
        op.create_index("ix_users_id", "users", ["id"])

    if "roadmap_sections" not in have:
        op.create_table(
            "roadmap_sections",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("university", sa.String(150), nullable=False),
            sa.Column("degree", sa.String(100), nullable=True),
            sa.Column("term", sa.String(50), nullable=True),
            sa.Column("progress", sa.Integer(), nullable=True),
            sa.Column("number", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(100), nullable=False),
        )
        op.create_index("ix_roadmap_sections_id", "roadmap_sections", ["id"])

    if "tracked_universities" not in have:
        op.create_table(
            "tracked_universities",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("location", sa.String(100), nullable=True),
            sa.Column("avg_gpa", sa.String(50), nullable=True),
            sa.Column("avg_gre", sa.String(50), nullable=True),
            sa.Column("deadlines", sa.String(100), nullable=True),
            sa.Column("status", sa.String(50), nullable=False),
            sa.Column("acceptance_rate", sa.String(20), nullable=True),
            sa.Column("reqs", sa.Text(), nullable=True),
        )
        op.create_index("ix_tracked_universities_id", "tracked_universities", ["id"])

    if "roadmap_steps" not in have:
        op.create_table(
            "roadmap_steps",
            sa.Column("id", sa.String(50), primary_key=True),
            sa.Column(
                "section_id",
                sa.Integer(),
                sa.ForeignKey("roadmap_sections.id"),
                nullable=True,
            ),
            sa.Column("title", sa.String(150), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("priority", sa.String(20), nullable=True),
            sa.Column("type", sa.String(50), nullable=True),
        )
        op.create_index("ix_roadmap_steps_id", "roadmap_steps", ["id"])


def downgrade() -> None:
    have = _table_names()
    if "roadmap_steps" in have:
        op.drop_index("ix_roadmap_steps_id", table_name="roadmap_steps")
        op.drop_table("roadmap_steps")
    if "tracked_universities" in have:
        op.drop_index("ix_tracked_universities_id", table_name="tracked_universities")
        op.drop_table("tracked_universities")
    if "roadmap_sections" in have:
        op.drop_index("ix_roadmap_sections_id", table_name="roadmap_sections")
        op.drop_table("roadmap_sections")
    # users predates this revision on the shared database; leave it.
