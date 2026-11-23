"""G2 initial relational schema

Revision ID: 0001_g2_initial
Revises:
Create Date: 2026-11-23
"""
from alembic import op
import sqlalchemy as sa
revision = "0001_g2_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("rules",sa.Column("id",sa.String(36),primary_key=True),sa.Column("rule_id",sa.String(100),nullable=False),sa.Column("domain",sa.String(50),nullable=False),sa.Column("title",sa.String(200),nullable=False),sa.Column("latest_version",sa.String(40),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_rules_rule_id","rules",["rule_id"],unique=True); op.create_index("ix_rules_domain","rules",["domain"])
    op.create_table("rule_versions",sa.Column("id",sa.String(36),primary_key=True),sa.Column("rule_pk",sa.String(36),sa.ForeignKey("rules.id",ondelete="CASCADE"),nullable=False),sa.Column("version",sa.String(40),nullable=False),sa.Column("status",sa.String(20),nullable=False),sa.Column("definition",sa.JSON(),nullable=False),sa.Column("content_hash",sa.String(64),nullable=False),sa.Column("created_by",sa.String(120),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("published_at",sa.DateTime(timezone=True)),sa.UniqueConstraint("rule_pk","version",name="uq_rule_version"))
    op.create_index("ix_rule_versions_rule_pk","rule_versions",["rule_pk"]); op.create_index("ix_rule_versions_status","rule_versions",["status"]); op.create_index("ix_rule_versions_content_hash","rule_versions",["content_hash"])
    op.create_table("analysis_runs",sa.Column("id",sa.String(36),primary_key=True),sa.Column("analysis_type",sa.String(40),nullable=False),sa.Column("status",sa.String(20),nullable=False),sa.Column("input_payload",sa.JSON(),nullable=False),sa.Column("result_summary",sa.JSON()),sa.Column("requested_by",sa.String(120),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("completed_at",sa.DateTime(timezone=True)))
    op.create_index("ix_analysis_runs_analysis_type","analysis_runs",["analysis_type"]); op.create_index("ix_analysis_runs_status","analysis_runs",["status"])
    op.create_table("findings",sa.Column("id",sa.String(36),primary_key=True),sa.Column("run_id",sa.String(36),sa.ForeignKey("analysis_runs.id",ondelete="CASCADE"),nullable=False),sa.Column("rule_id",sa.String(100),nullable=False),sa.Column("rule_version",sa.String(40),nullable=False),sa.Column("severity",sa.String(20),nullable=False),sa.Column("status",sa.String(20),nullable=False),sa.Column("result_payload",sa.JSON()),sa.Column("error_code",sa.String(80)))
    op.create_index("ix_findings_run_id","findings",["run_id"]); op.create_index("ix_findings_rule_id","findings",["rule_id"]); op.create_index("ix_findings_status","findings",["status"]); op.create_index("ix_findings_run_rule","findings",["run_id","rule_id"])
    op.create_table("approvals",sa.Column("id",sa.String(36),primary_key=True),sa.Column("target_type",sa.String(30),nullable=False),sa.Column("target_id",sa.String(100),nullable=False),sa.Column("action",sa.String(30),nullable=False),sa.Column("decision",sa.String(20),nullable=False),sa.Column("approver",sa.String(120),nullable=False),sa.Column("comment",sa.Text()),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_approvals_target_type","approvals",["target_type"]); op.create_index("ix_approvals_target_id","approvals",["target_id"])
    op.create_table("audit_events",sa.Column("id",sa.String(36),primary_key=True),sa.Column("actor",sa.String(120),nullable=False),sa.Column("action",sa.String(80),nullable=False),sa.Column("resource_type",sa.String(40),nullable=False),sa.Column("resource_id",sa.String(100),nullable=False),sa.Column("details",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_audit_events_actor","audit_events",["actor"]); op.create_index("ix_audit_events_action","audit_events",["action"])
    op.create_table("curve_artifacts",sa.Column("id",sa.String(100),primary_key=True),sa.Column("x_unit",sa.String(40),nullable=False),sa.Column("y_unit",sa.String(40),nullable=False),sa.Column("z_unit",sa.String(40),nullable=False),sa.Column("x_values",sa.JSON(),nullable=False),sa.Column("y_values",sa.JSON(),nullable=False),sa.Column("z_values",sa.JSON(),nullable=False),sa.Column("interpolation",sa.String(30),nullable=False),sa.Column("source_ref",sa.String(500),nullable=False),sa.Column("checksum",sa.String(64),nullable=False),sa.Column("approved",sa.Boolean(),nullable=False),sa.Column("created_by",sa.String(120),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_table("idempotency_records",sa.Column("key",sa.String(128),primary_key=True),sa.Column("request_hash",sa.String(64),nullable=False),sa.Column("response_payload",sa.JSON(),nullable=False),sa.Column("status_code",sa.Integer(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))

def downgrade():
    op.drop_table("idempotency_records"); op.drop_table("curve_artifacts"); op.drop_index("ix_audit_events_action",table_name="audit_events"); op.drop_index("ix_audit_events_actor",table_name="audit_events"); op.drop_table("audit_events")
    op.drop_index("ix_approvals_target_id",table_name="approvals"); op.drop_index("ix_approvals_target_type",table_name="approvals"); op.drop_table("approvals")
    op.drop_index("ix_findings_run_rule",table_name="findings"); op.drop_index("ix_findings_status",table_name="findings"); op.drop_index("ix_findings_rule_id",table_name="findings"); op.drop_index("ix_findings_run_id",table_name="findings"); op.drop_table("findings")
    op.drop_index("ix_analysis_runs_status",table_name="analysis_runs"); op.drop_index("ix_analysis_runs_analysis_type",table_name="analysis_runs"); op.drop_table("analysis_runs")
    op.drop_index("ix_rule_versions_content_hash",table_name="rule_versions"); op.drop_index("ix_rule_versions_status",table_name="rule_versions"); op.drop_index("ix_rule_versions_rule_pk",table_name="rule_versions"); op.drop_table("rule_versions")
    op.drop_index("ix_rules_domain",table_name="rules"); op.drop_index("ix_rules_rule_id",table_name="rules"); op.drop_table("rules")
