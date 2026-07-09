from sqlalchemy import Column, Integer, String, DateTime, Date, JSON, ForeignKey, Text
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    territory_id = Column(String(50), nullable=True)
    role = Column(String(50), nullable=False, default="rep")

class HCP(Base):
    __tablename__ = "hcps"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    specialty = Column(String(100), nullable=False)
    institution = Column(String(150), nullable=False)
    npi_id = Column(String(50), unique=True, index=True, nullable=False)
    segment = Column(String(20), nullable=False)  # KOL, High, Medium, Low
    preferred_channel = Column(String(50), nullable=False, default="visit")
    last_interaction_at = Column(DateTime, nullable=True)

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    indication = Column(String(255), nullable=False)
    dosage_forms = Column(JSON, nullable=False)  # List of strings, e.g. ["5mg", "10mg"]

class Sample(Base):
    __tablename__ = "samples"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    lot_number = Column(String(50), unique=True, nullable=False, index=True)
    expiry_date = Column(Date, nullable=False)

class Interaction(Base):
    __tablename__ = "interactions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    hcp_id = Column(Integer, ForeignKey("hcps.id"), nullable=False)
    rep_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    channel = Column(String(50), nullable=False)  # call, visit, virtual, email
    interaction_datetime = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    duration_minutes = Column(Integer, nullable=False, default=15)
    discussion_topics = Column(JSON, nullable=False, default=list)  # list of strings
    products_discussed = Column(JSON, nullable=False, default=list)  # list of strings
    sentiment = Column(String(50), nullable=False)  # positive, neutral, negative, objection
    samples_dropped = Column(JSON, nullable=False, default=list)  # list of dicts: {"product_id": int, "sample_id": int, "qty": int}
    materials_shared = Column(JSON, nullable=False, default=list)  # list of strings
    next_best_action = Column(String(255), nullable=True)
    follow_up_date = Column(Date, nullable=True)
    raw_transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    entry_mode = Column(String(20), nullable=False)  # form, chat
    status = Column(String(20), nullable=False, default="confirmed")  # draft, confirmed, edited
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class InteractionAuditLog(Base):
    __tablename__ = "interaction_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    interaction_id = Column(Integer, ForeignKey("interactions.id"), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    change_type = Column(String(20), nullable=False)  # create, edit, delete
    diff_json = Column(JSON, nullable=False)  # Dict representing changed fields before/after
    changed_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
