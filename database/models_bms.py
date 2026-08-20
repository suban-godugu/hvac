"""BMS connection, discovery, and canonical point mapping. No secrets."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, JSON, String, UniqueConstraint

from database.base import Base


class BmsConnectionDB(Base):
    __tablename__ = "bms_connections"
    id = Column(String, primary_key=True)
    building_id = Column(String, nullable=True, index=True)
    protocol = Column(String, nullable=False)
    host = Column(String, nullable=True)
    port = Column(Integer, nullable=True)
    enabled = Column(Boolean, default=True)
    connected = Column(Boolean, default=False)
    last_connected_at = Column(DateTime, nullable=True)
    last_error = Column(String, nullable=True)
    write_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (Index("ix_bms_conn_bldg", "building_id", "protocol"),)


class BmsDeviceDB(Base):
    __tablename__ = "bms_devices"
    id = Column(String, primary_key=True)
    connection_id = Column(String, ForeignKey("bms_connections.id"), nullable=False, index=True)
    device_identifier = Column(String, nullable=False)
    name = Column(String, nullable=True)
    device_type = Column(String, nullable=True)
    status = Column(String, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("connection_id", "device_identifier", name="uq_bms_device_ident"),)


class BmsPointDB(Base):
    __tablename__ = "bms_points"
    id = Column(String, primary_key=True)
    device_id = Column(String, ForeignKey("bms_devices.id"), nullable=False, index=True)
    point_identifier = Column(String, nullable=False)
    name = Column(String, nullable=True)
    object_type = Column(String, nullable=True)
    object_instance = Column(String, nullable=True)
    register = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    data_type = Column(String, nullable=True)
    readable = Column(Boolean, default=True)
    writable = Column(Boolean, default=False)
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    enabled = Column(Boolean, default=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("device_id", "point_identifier", name="uq_bms_point_ident"),)


class EquipmentPointMappingDB(Base):
    __tablename__ = "equipment_point_mappings"
    id = Column(String, primary_key=True)
    equipment_id = Column(String, nullable=False, index=True)
    canonical_point = Column(String, nullable=False)
    bms_point_id = Column(String, ForeignKey("bms_points.id"), nullable=False, index=True)
    direction = Column(String, nullable=False)
    safety_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("equipment_id", "canonical_point", name="uq_eq_canonical"),)
