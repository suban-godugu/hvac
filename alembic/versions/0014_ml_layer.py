"""Shared HVAC ML registry tables. Does not drop existing HVAC tables."""
from alembic import op
import sqlalchemy as sa

revision = "0014_ml_layer"
down_revision = "0013_o16_water_cooled_hp"
branch_labels = None
depends_on = None


def _tables():
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _tables()
    if "ml_dataset_registry" not in existing:
        op.create_table(
            "ml_dataset_registry",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("source", sa.String(), nullable=False),
            sa.Column("path", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("alias_of", sa.String(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
    if "ml_dataset_files" not in existing:
        op.create_table(
            "ml_dataset_files",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("dataset_id", sa.String(), nullable=False),
            sa.Column("file_path", sa.String(), nullable=False),
            sa.Column("file_name", sa.String(), nullable=False),
            sa.Column("format", sa.String(), nullable=True),
            sa.Column("size_bytes", sa.Integer(), nullable=True),
            sa.Column("row_count", sa.Integer(), nullable=True),
            sa.Column("columns_json", sa.JSON(), nullable=True),
            sa.Column("schema_json", sa.JSON(), nullable=True),
        )
    if "ml_dataset_quality" not in existing:
        op.create_table(
            "ml_dataset_quality",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("dataset_id", sa.String(), nullable=False),
            sa.Column("file_id", sa.String(), nullable=True),
            sa.Column("missing_pct", sa.Float(), nullable=True),
            sa.Column("duplicate_rows", sa.Integer(), nullable=True),
            sa.Column("timestamp_valid", sa.Boolean(), nullable=True),
            sa.Column("numeric_valid_pct", sa.Float(), nullable=True),
            sa.Column("outlier_rate", sa.Float(), nullable=True),
            sa.Column("sampling_interval_seconds", sa.Float(), nullable=True),
            sa.Column("sample_rows", sa.Integer(), nullable=True),
            sa.Column("details_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
    if "ml_dataset_opportunity_map" not in existing:
        op.create_table(
            "ml_dataset_opportunity_map",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("dataset_id", sa.String(), nullable=False),
            sa.Column("opportunity_id", sa.String(), nullable=False),
            sa.Column("agent_id", sa.String(), nullable=False),
            sa.Column("file_name", sa.String(), nullable=True),
            sa.Column("feature_map", sa.JSON(), nullable=False),
            sa.Column("target_column", sa.String(), nullable=True),
            sa.Column("task_type", sa.String(), nullable=False),
            sa.Column("training_allowed", sa.Boolean(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
        )
    if "ml_feature_definitions" not in existing:
        op.create_table(
            "ml_feature_definitions",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("opportunity_id", sa.String(), nullable=False),
            sa.Column("feature_name", sa.String(), nullable=False),
            sa.Column("unit", sa.String(), nullable=True),
            sa.Column("min_value", sa.Float(), nullable=True),
            sa.Column("max_value", sa.Float(), nullable=True),
            sa.Column("required", sa.Boolean(), nullable=False),
            sa.Column("source_column", sa.String(), nullable=True),
        )
    if "ml_training_runs" not in existing:
        op.create_table(
            "ml_training_runs",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("opportunity_id", sa.String(), nullable=False),
            sa.Column("dataset_id", sa.String(), nullable=True),
            sa.Column("map_id", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("algorithm", sa.String(), nullable=True),
            sa.Column("metrics_json", sa.JSON(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
    if "ml_model_registry" not in existing:
        op.create_table(
            "ml_model_registry",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("opportunity_id", sa.String(), nullable=False),
            sa.Column("agent_id", sa.String(), nullable=False),
            sa.Column("model_type", sa.String(), nullable=False),
            sa.Column("model_version", sa.String(), nullable=False),
            sa.Column("features_json", sa.JSON(), nullable=True),
            sa.Column("target_json", sa.JSON(), nullable=True),
            sa.Column("artifact_path", sa.String(), nullable=True),
            sa.Column("training_dataset_id", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
    if "ml_model_metrics" not in existing:
        op.create_table(
            "ml_model_metrics",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("model_id", sa.String(), nullable=False),
            sa.Column("split", sa.String(), nullable=False),
            sa.Column("metrics_json", sa.JSON(), nullable=False),
        )
    if "ml_predictions" not in existing:
        op.create_table(
            "ml_predictions",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("opportunity_id", sa.String(), nullable=False),
            sa.Column("equipment_id", sa.String(), nullable=True),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("model_id", sa.String(), nullable=True),
            sa.Column("input_json", sa.JSON(), nullable=True),
            sa.Column("prediction_json", sa.JSON(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("source", sa.String(), nullable=False),
            sa.Column("provenance", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
    if "ml_prediction_features" not in existing:
        op.create_table(
            "ml_prediction_features",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("prediction_id", sa.String(), nullable=False),
            sa.Column("feature", sa.String(), nullable=False),
            sa.Column("value", sa.Float(), nullable=True),
            sa.Column("importance", sa.Float(), nullable=True),
        )
    if "ml_agent_predictions" not in existing:
        op.create_table(
            "ml_agent_predictions",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("opportunity_id", sa.String(), nullable=False),
            sa.Column("agent_id", sa.String(), nullable=False),
            sa.Column("prediction_id", sa.String(), nullable=True),
            sa.Column("recommendation_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    existing = _tables()
    for name in (
        "ml_agent_predictions",
        "ml_prediction_features",
        "ml_predictions",
        "ml_model_metrics",
        "ml_model_registry",
        "ml_training_runs",
        "ml_feature_definitions",
        "ml_dataset_opportunity_map",
        "ml_dataset_quality",
        "ml_dataset_files",
        "ml_dataset_registry",
    ):
        if name in existing:
            op.drop_table(name)
