from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date

class UserBase(BaseModel):
    name: str
    email: str
    territory_id: Optional[str] = None
    role: str

class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True

class HCPBase(BaseModel):
    name: str
    specialty: str
    institution: str
    npi_id: str
    segment: str
    preferred_channel: str
    last_interaction_at: Optional[datetime] = None

class HCPResponse(HCPBase):
    id: int

    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    name: str
    indication: str
    dosage_forms: List[str]

class ProductResponse(ProductBase):
    id: int

    class Config:
        from_attributes = True

class SampleBase(BaseModel):
    product_id: int
    lot_number: str
    expiry_date: date

class SampleResponse(SampleBase):
    id: int

    class Config:
        from_attributes = True

class SampleDrop(BaseModel):
    product_id: int
    sample_id: int
    qty: int

class InteractionCreate(BaseModel):
    hcp_id: int
    channel: str
    interaction_datetime: datetime
    duration_minutes: int
    discussion_topics: List[str] = []
    products_discussed: List[str] = []
    sentiment: str
    samples_dropped: List[SampleDrop] = []
    materials_shared: List[str] = []
    next_best_action: Optional[str] = None
    follow_up_date: Optional[date] = None
    raw_transcript: Optional[str] = None
    summary: Optional[str] = None
    entry_mode: str  # form or chat
    status: str = "confirmed"

class InteractionUpdate(BaseModel):
    hcp_id: Optional[int] = None
    channel: Optional[str] = None
    interaction_datetime: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    discussion_topics: Optional[List[str]] = None
    products_discussed: Optional[List[str]] = None
    sentiment: Optional[str] = None
    samples_dropped: Optional[List[SampleDrop]] = None
    materials_shared: Optional[List[str]] = None
    next_best_action: Optional[str] = None
    follow_up_date: Optional[date] = None
    raw_transcript: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None

class InteractionResponse(BaseModel):
    id: int
    hcp_id: int
    rep_id: int
    channel: str
    interaction_datetime: datetime
    duration_minutes: int
    discussion_topics: List[str]
    products_discussed: List[str]
    sentiment: str
    samples_dropped: List[Dict[str, Any]]
    materials_shared: List[str]
    next_best_action: Optional[str] = None
    follow_up_date: Optional[date] = None
    raw_transcript: Optional[str] = None
    summary: Optional[str] = None
    entry_mode: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    id: int
    interaction_id: int
    changed_by: int
    change_type: str
    diff_json: Dict[str, Any]
    changed_at: datetime

    class Config:
        from_attributes = True

class ChatMessage(BaseModel):
    role: str  # user, assistant, system
    content: str

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    active_hcp_id: Optional[int] = None

class ChatResponse(BaseModel):
    messages: List[ChatMessage]
    thread_id: str
    pending_extraction: Optional[Dict[str, Any]] = None
    warning: Optional[str] = None
