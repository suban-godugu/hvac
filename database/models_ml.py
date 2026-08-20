"""Shared HVAC ML registry tables. Training/reference data only — never LIVE_BMS."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text

from database.base import Base


class MLDatasetRegistryDB(Base):
    __tablename__ = "ml_dataset_registry"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    source = Column(String, nullable=False, default="TRAINING_DATASET")
    path = Column(String, nullable=False)
    status = Column(String, nullable=False)
    alias_of = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class MLDatasetFileDB(Base):
    __tablename__ = "ml_dataset_files"
    id = Column(String, primary_key=True)
    dataset_id = Column(String, ForeignKey("ml_dataset_registry.id"), nullable=False)
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    format = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    row_count = Column(Integer, nullable=True)
    columns_json = Column(JSON, nullable=True)
    schema_json = Column(JSON, nullable=True)


class MLDatasetQualityDB(Base):
    __tablename__ = "ml_dataset_quality"
    id = Column(String, primary_key=True)
    dataset_id = Column(String, ForeignKey("ml_dataset_registry.id"), nullable=False)
    file_id = Column(String, ForeignKey("ml_dataset_files.id"), nullable=True)
    missing_pct = Column(Float, nullable=True)
    duplicate_rows = Column(Integer, nullable=True)
    timestamp_valid = Column(Boolean, nullable=True)
    numeric_valid_pct = Column(Float, nullable=True)
    outlier_rate = Column(Float, nullable=True)
    sampling_interval_seconds = Column(Float, nullable=True)
    sample_rows = Column(Integer, nullable=True)
    details_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MLDatasetOpportunityMapDB(Base):
    __tablename__ = "ml_dataset_opportunity_map"
    id = Column(String, primary_key=True)
    dataset_id = Column(String, ForeignKey("ml_dataset_registry.id"), nullable=False)
    opportunity_id = Column(String, nullable=False)
    agent_id = Column(String, nullable=False)
    file_name = Column(String, nullable=True)
    feature_map = Column(JSON, nullable=False)
    target_column = Column(String, nullable=True)
    task_type = Column(String, nullable=False)
    training_allowed = Column(Boolean, nullable=False, default=False)
    status = Column(String, nullable=False)
    notes = Column(Text, nullable=True)


class MLFeatureDefinitionDB(Base):
    __tablename__ = "ml_feature_definitions"
    id = Column(String, primary_key=True)
    opportunity_id = Column(String, nullable=False)
    feature_name = Column(String, nullable=False)
    unit = Column(String, nullable=True)
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    required = Column(Boolean, nullable=False, default=False)
    source_column = Column(String, nullable=True)


class MLTrainingRunDB(Base):
    __tablename__ = "ml_training_runs"
    id = Column(String, primary_key=True)
    opportunity_id = Column(String, nullable=False)
    dataset_id = Column(String, nullable=True)
    map_id = Column(String, nullable=True)
    status = Column(String, nullable=False)
    algorithm = Column(String, nullable=True)
    metrics_json = Column(JSON, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MLModelRegistryDB(Base):
    __tablename__ = "ml_model_registry"
    id = Column(String, primary_key=True)
    opportunity_id = Column(String, nullable=False)
    agent_id = Column(String, nullable=False)
    model_type = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    features_json = Column(JSON, nullable=True)
    target_json = Column(JSON, nullable=True)
    artifact_path = Column(String, nullable=True)
    training_dataset_id = Column(String, nullable=True)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class MLModelMetricsDB(Base):
    __tablename__ = "ml_model_metrics"
    id = Column(String, primary_key=True)
    model_id = Column(String, ForeignKey("ml_model_registry.id"), nullable=False)
    split = Column(String, nullable=False)
    metrics_json = Column(JSON, nullable=False)


class MLPredictionDB(Base):
    __tablename__ = "ml_predictions"
    id = Column(String, primary_key=True)
    opportunity_id = Column(String, nullable=False)
    equipment_id = Column(String, nullable=True)
    building_id = Column(String, nullable=True)
    model_id = Column(String, nullable=True)
    input_json = Column(JSON, nullable=True)
    prediction_json = Column(JSON, nullable=True)
    confidence = Column(Float, nullable=True)
    source = Column(String, nullable=False, default="ML_MODEL")
    provenance = Column(String, nullable=False, default="MODEL PREDICTION")
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class MLPredictionFeatureDB(Base):
    __tablename__ = "ml_prediction_features"
    id = Column(String, primary_key=True)
    prediction_id = Column(String, ForeignKey("ml_predictions.id"), nullable=False)
    feature = Column(String, nullable=False)
    value = Column(Float, nullable=True)
    importance = Column(Float, nullable=True)


class MLAgentPredictionDB(Base):
    __tablename__ = "ml_agent_predictions"
    id = Column(String, primary_key=True)
    opportunity_id = Column(String, nullable=False)
    agent_id = Column(String, nullable=False)
    prediction_id = Column(String, ForeignKey("ml_predictions.id"), nullable=True)
    recommendation_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
