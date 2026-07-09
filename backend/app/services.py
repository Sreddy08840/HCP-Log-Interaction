from sqlalchemy.orm import Session
from sqlalchemy import or_
from backend.app.models import User, HCP, Product, Sample, Interaction, InteractionAuditLog
from backend.app.schemas import InteractionCreate, InteractionUpdate
import datetime
import json
from typing import Dict, Any, List

def calculate_diff(old_obj: Dict[str, Any], new_obj: Dict[str, Any]) -> Dict[str, Any]:
    diff = {}
    for key, val in new_obj.items():
        # Skip internal SQLAlchemy fields or fields we don't care to diff
        if key in ("created_at", "updated_at", "id", "rep_id"):
            continue
        old_val = old_obj.get(key)
        
        # Serialize list/dict structures for accurate comparison
        if isinstance(old_val, (list, dict)) or isinstance(val, (list, dict)):
            if json.dumps(old_val, sort_keys=True) != json.dumps(val, sort_keys=True):
                diff[key] = {"old": old_val, "new": val}
        elif isinstance(old_val, (datetime.date, datetime.datetime)):
            # convert date to string for json diff
            old_str = old_val.isoformat()
            new_str = val.isoformat() if isinstance(val, (datetime.date, datetime.datetime)) else val
            if old_str != new_str:
                diff[key] = {"old": old_str, "new": new_str}
        else:
            if old_val != val:
                diff[key] = {"old": old_val, "new": val}
    return diff

def search_hcps(db: Session, query: str) -> List[HCP]:
    if not query:
        return db.query(HCP).all()
    search_term = f"%{query}%"
    return db.query(HCP).filter(
        or_(
            HCP.name.ilike(search_term),
            HCP.specialty.ilike(search_term),
            HCP.institution.ilike(search_term)
        )
    ).all()

def create_interaction(db: Session, data: InteractionCreate, rep_id: int) -> Interaction:
    # Build DB object
    db_interaction = Interaction(
        hcp_id=data.hcp_id,
        rep_id=rep_id,
        channel=data.channel,
        interaction_datetime=data.interaction_datetime,
        duration_minutes=data.duration_minutes,
        discussion_topics=data.discussion_topics,
        products_discussed=data.products_discussed,
        sentiment=data.sentiment,
        # Convert list of Pydantic models to dicts for JSON column
        samples_dropped=[s.dict() for s in data.samples_dropped],
        materials_shared=data.materials_shared,
        next_best_action=data.next_best_action,
        follow_up_date=data.follow_up_date,
        raw_transcript=data.raw_transcript,
        summary=data.summary,
        entry_mode=data.entry_mode,
        status=data.status,
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow()
    )
    db.add(db_interaction)
    db.commit()
    db.refresh(db_interaction)
    
    # Update HCP last interaction date
    hcp = db.query(HCP).filter(HCP.id == data.hcp_id).first()
    if hcp:
        hcp.last_interaction_at = db_interaction.interaction_datetime
        db.add(hcp)
        db.commit()
    
    # Create Audit Log
    new_data = {c.name: getattr(db_interaction, c.name) for c in db_interaction.__table__.columns}
    # JSON-serialize datetime objects for diff
    for k, v in new_data.items():
        if isinstance(v, (datetime.datetime, datetime.date)):
            new_data[k] = v.isoformat()

    audit_log = InteractionAuditLog(
        interaction_id=db_interaction.id,
        changed_by=rep_id,
        change_type="create",
        diff_json={"changes": new_data},
        changed_at=datetime.datetime.utcnow()
    )
    db.add(audit_log)
    db.commit()
    
    return db_interaction

def update_interaction(db: Session, interaction_id: int, data: InteractionUpdate, rep_id: int) -> Interaction:
    db_interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not db_interaction:
        raise ValueError(f"Interaction with id {interaction_id} not found")
    
    # Capture old state for audit diff
    old_state = {c.name: getattr(db_interaction, c.name) for c in db_interaction.__table__.columns}
    
    # Update fields
    update_dict = data.dict(exclude_unset=True)
    for key, val in update_dict.items():
        if key == "samples_dropped" and val is not None:
            setattr(db_interaction, key, [s.dict() for s in val])
        else:
            setattr(db_interaction, key, val)
            
    db_interaction.updated_at = datetime.datetime.utcnow()
    db.add(db_interaction)
    db.commit()
    db.refresh(db_interaction)
    
    # Update HCP last interaction date
    hcp = db.query(HCP).filter(HCP.id == db_interaction.hcp_id).first()
    if hcp:
        hcp.last_interaction_at = db_interaction.interaction_datetime
        db.add(hcp)
        db.commit()
        
    # Create Audit Log
    new_state = {c.name: getattr(db_interaction, c.name) for c in db_interaction.__table__.columns}
    diff = calculate_diff(old_state, new_state)
    
    if diff:
        audit_log = InteractionAuditLog(
            interaction_id=db_interaction.id,
            changed_by=rep_id,
            change_type="edit",
            diff_json=diff,
            changed_at=datetime.datetime.utcnow()
        )
        db.add(audit_log)
        db.commit()
        
    return db_interaction
