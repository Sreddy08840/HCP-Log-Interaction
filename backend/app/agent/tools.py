from sqlalchemy.orm import Session
from backend.app.models import HCP, Product, Sample, Interaction
from backend.app.services import search_hcps
import datetime
from typing import Dict, Any, List, Optional

def hcp_lookup_tool(db: Session, query: str) -> List[Dict[str, Any]]:
    """Search for Healthcare Professionals (HCPs) using fuzzy/substring matching."""
    hcps = search_hcps(db, query)
    return [
        {
            "id": h.id,
            "name": h.name,
            "specialty": h.specialty,
            "institution": h.institution,
            "npi_id": h.npi_id,
            "segment": h.segment,
            "preferred_channel": h.preferred_channel,
            "last_interaction_at": h.last_interaction_at.isoformat() if h.last_interaction_at else None
        } for h in hcps
    ]

def compliance_sample_check_tool(db: Session, hcp_id: int, samples_dropped: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate samples being dropped to an HCP:
    - Check if lot is expired.
    - Check if NPI license is valid (simulated).
    - Check state limits: max 10 units per sample drop in a single transaction.
    """
    hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
    if not hcp:
        return {"compliant": False, "reason": f"HCP with ID {hcp_id} not found."}
    
    # Check NPI length as a simulation of active license
    if len(hcp.npi_id) < 10:
        return {"compliant": False, "reason": f"HCP NPI ID {hcp.npi_id} is invalid or suspended."}
        
    for s_drop in samples_dropped:
        qty = s_drop.get("qty", 0)
        sample_id = s_drop.get("sample_id")
        
        # Check qty limits
        if qty <= 0:
            return {"compliant": False, "reason": "Sample quantity must be greater than zero."}
        if qty > 10:
            return {
                "compliant": False,
                "reason": f"Non-compliant: Quantity of {qty} exceeds the single-transaction limit of 10 samples."
            }
            
        # Check lot and expiry
        sample = db.query(Sample).filter(Sample.id == sample_id).first()
        if not sample:
            # Try to resolve by lot number if sample_id is string or lot representation
            lot_number = s_drop.get("lot_number")
            if lot_number:
                sample = db.query(Sample).filter(Sample.lot_number == lot_number).first()
                
        if not sample:
            return {"compliant": False, "reason": f"Sample with ID/Lot {sample_id} not found in catalog."}
            
        # Check expiration date
        today = datetime.date.today()
        if sample.expiry_date < today:
            return {
                "compliant": False,
                "reason": f"Non-compliant: Lot '{sample.lot_number}' expired on {sample.expiry_date.isoformat()} and cannot be distributed."
            }
            
    return {"compliant": True, "reason": "All checks passed successfully."}

def suggest_next_best_action_tool(db: Session, hcp_id: int, last_sentiment: str) -> Dict[str, Any]:
    """
    Suggest follow-up action and timing based on HCP history and segment.
    """
    hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
    if not hcp:
        return {"next_best_action": "Follow up with HCP", "follow_up_days": 14}
        
    # Standard logics based on HCP segment and sentiment
    segment = hcp.segment
    
    if last_sentiment == "objection":
        return {
            "next_best_action": "Involve Medical Science Liaison (MSL) to address clinical objections",
            "follow_up_days": 5
        }
    elif last_sentiment == "negative":
        return {
            "next_best_action": "Schedule follow-up visit to review clinical data and address concerns",
            "follow_up_days": 7
        }
    
    # Segment-based defaults
    if segment == "KOL":
        return {
            "next_best_action": "Share premium clinical efficacy studies and invite to upcoming symposium",
            "follow_up_days": 14
        }
    elif segment == "High":
        return {
            "next_best_action": "Send patient support program materials and follow up via email",
            "follow_up_days": 14
        }
    else:
        return {
            "next_best_action": "Follow up via phone call to check sample feedback",
            "follow_up_days": 30
        }
