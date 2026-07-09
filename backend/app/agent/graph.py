import os
import re
import datetime
from typing import Dict, Any, List, Optional, TypedDict, Annotated, Sequence
from sqlalchemy.orm import Session

from backend.app.models import HCP, Product, Sample, Interaction
from backend.app.database import SessionLocal
from backend.app.agent.tools import hcp_lookup_tool, compliance_sample_check_tool, suggest_next_best_action_tool
from backend.app.services import create_interaction, update_interaction

# Optional imports for LangGraph / LangChain
try:
    from langgraph.graph import StateGraph, START, END
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
except ImportError:
    # Fallback placeholders if imports fail, although we installed them
    StateGraph = None

# Define state shape
class AgentState(TypedDict):
    messages: List[Dict[str, str]]  # list of {"role": str, "content": str}
    thread_id: str
    active_hcp_id: Optional[int]
    pending_extraction: Optional[Dict[str, Any]]
    warning: Optional[str]

# --- Smart Rule-Based Fallback Parser ---
# This ensures a fully functional, zero-setup interactive demo out-of-the-box when GROQ_API_KEY is not set.

def parse_with_rules(text: str, active_hcp_id: Optional[int], db: Session) -> Dict[str, Any]:
    text_lower = text.lower()
    
    # 1. Resolve HCP
    hcp_id = active_hcp_id
    hcp_name = None
    if "mehta" in text_lower:
        hcp = db.query(HCP).filter(HCP.name.like("%Mehta%")).first()
        if hcp:
            hcp_id = hcp.id
            hcp_name = hcp.name
    elif "sharma" in text_lower:
        hcp = db.query(HCP).filter(HCP.name.like("%Sharma%")).first()
        if hcp:
            hcp_id = hcp.id
            hcp_name = hcp.name
    elif "verma" in text_lower:
        hcp = db.query(HCP).filter(HCP.name.like("%Verma%")).first()
        if hcp:
            hcp_id = hcp.id
            hcp_name = hcp.name
            
    # Default to first HCP if none resolved yet
    if not hcp_id:
        hcp = db.query(HCP).first()
        if hcp:
            hcp_id = hcp.id
            hcp_name = hcp.name

    # 2. Resolve Product & Samples
    samples_dropped = []
    products_discussed = []
    
    # Check for lot numbers and quantities
    # E.g., "5 units of CX10-2027" or "CX10-2027 quantity 4" or "dropped 5 CX10-2027"
    lot_matches = re.findall(r'(cx10-2027|cx10-exp|ps50-2027|os100-2027)', text_lower)
    for lot in lot_matches:
        lot_upper = lot.upper()
        sample = db.query(Sample).filter(Sample.lot_number == lot_upper).first()
        if sample:
            product = db.query(Product).filter(Product.id == sample.product_id).first()
            if product and product.name not in products_discussed:
                products_discussed.append(product.name)
            
            # Find quantity near this lot number
            qty = 1
            # Search context around the match
            pos = text_lower.find(lot)
            surround = text_lower[max(0, pos-20):min(len(text_lower), pos+30)]
            qty_match = re.search(r'\b(\d+)\b', surround)
            if qty_match:
                qty = int(qty_match.group(1))
            
            samples_dropped.append({
                "product_id": sample.product_id,
                "sample_id": sample.id,
                "lot_number": sample.lot_number,
                "product_name": product.name if product else "Unknown",
                "qty": qty
            })
            
    # If no lots matched but product named, add products_discussed
    if not products_discussed:
        if "cardiox" in text_lower:
            products_discussed.append("CardioX")
        if "pedrasafe" in text_lower:
            products_discussed.append("PedraSafe")
        if "oncoshield" in text_lower:
            products_discussed.append("OncoShield")

    # 3. Sentiment
    sentiment = "positive"
    if "objection" in text_lower or "object" in text_lower:
        sentiment = "objection"
    elif "negative" in text_lower or "poor" in text_lower or "dislike" in text_lower:
        sentiment = "negative"
    elif "neutral" in text_lower or "indifferent" in text_lower:
        sentiment = "neutral"
    elif "positive" in text_lower or "happy" in text_lower or "good" in text_lower:
        sentiment = "positive"

    # 4. Channel
    channel = "visit"
    if "call" in text_lower or "phone" in text_lower:
        channel = "call"
    elif "virtual" in text_lower or "zoom" in text_lower or "teams" in text_lower or "video" in text_lower:
        channel = "virtual"
    elif "email" in text_lower or "mail" in text_lower:
        channel = "email"
    elif "visit" in text_lower or "met" in text_lower or "saw" in text_lower:
        channel = "visit"

    # 5. Duration
    duration = 15
    dur_match = re.search(r'(\d+)\s*(min|minute|hour|hr)', text_lower)
    if dur_match:
        val = int(dur_match.group(1))
        unit = dur_match.group(2)
        if "hour" in unit or "hr" in unit:
            duration = val * 60
        else:
            duration = val

    # 6. Follow up date
    follow_up_days = 14
    if "week" in text_lower:
        # Check if a number is specified before week
        week_match = re.search(r'(\d+)\s*week', text_lower)
        if week_match:
            follow_up_days = int(week_match.group(1)) * 7
        else:
            follow_up_days = 7
    elif "month" in text_lower:
        follow_up_days = 30
    elif "day" in text_lower:
        day_match = re.search(r'(\d+)\s*day', text_lower)
        if day_match:
            follow_up_days = int(day_match.group(1))
            
    follow_up_date = datetime.date.today() + datetime.timedelta(days=follow_up_days)

    # 7. Discussion Topics
    topics = []
    if products_discussed:
        topics = [f"Product Discussion: {p}" for p in products_discussed]
    else:
        topics = ["General check-in"]
    if "efficacy" in text_lower:
        topics.append("Efficacy and safety details")
    if "sample" in text_lower or "drop" in text_lower:
        topics.append("Sample distribution")

    # 8. Summary
    summary_text = f"Met with {hcp_name or 'HCP'} via {channel}. Discussed "
    if products_discussed:
        summary_text += f"{', '.join(products_discussed)}. "
    else:
        summary_text += "general updates. "
    if samples_dropped:
        sample_details = [f"{s.get('qty')} units of Lot {s.get('lot_number')}" for s in samples_dropped]
        summary_text += f"Dropped samples: {', '.join(sample_details)}. "
    summary_text += f"Sentiment was {sentiment}."

    return {
        "hcp_id": hcp_id,
        "hcp_name": hcp_name,
        "channel": channel,
        "interaction_datetime": datetime.datetime.now().isoformat(),
        "duration_minutes": duration,
        "discussion_topics": topics,
        "products_discussed": products_discussed,
        "sentiment": sentiment,
        "samples_dropped": samples_dropped,
        "materials_shared": ["Clinical Brochure"] if products_discussed else [],
        "next_best_action": suggest_next_best_action_tool(db, hcp_id, sentiment)["next_best_action"] if hcp_id else "Follow up",
        "follow_up_date": follow_up_date.isoformat(),
        "raw_transcript": text,
        "summary": summary_text,
        "entry_mode": "chat",
        "status": "draft"
    }

def apply_chat_edit(pending: Dict[str, Any], text: str, db: Session) -> Dict[str, Any]:
    text_lower = text.lower()
    updated = pending.copy()
    
    # Edit sentiment
    if "sentiment" in text_lower or "mark" in text_lower or "change" in text_lower:
        for s in ["positive", "neutral", "negative", "objection"]:
            if s in text_lower:
                updated["sentiment"] = s
                
    # Edit quantity
    # E.g. "change quantity to 5" or "quantity 8"
    qty_match = re.search(r'(?:quantity|qty|units|amount|change to)\s*(?:to\s*)?(\d+)', text_lower)
    if qty_match and updated.get("samples_dropped"):
        new_qty = int(qty_match.group(1))
        # Update first sample drop qty
        new_samples = []
        for s in updated["samples_dropped"]:
            copy_s = s.copy()
            copy_s["qty"] = new_qty
            new_samples.append(copy_s)
        updated["samples_dropped"] = new_samples
        
    # Edit follow-up date
    # E.g. "follow up in 3 weeks" or "follow up in 10 days"
    if "follow" in text_lower:
        days = 14
        days_match = re.search(r'(\d+)\s*day', text_lower)
        weeks_match = re.search(r'(\d+)\s*week', text_lower)
        if days_match:
            days = int(days_match.group(1))
        elif weeks_match:
            days = int(weeks_match.group(1)) * 7
            
        new_date = datetime.date.today() + datetime.timedelta(days=days)
        updated["follow_up_date"] = new_date.isoformat()
        
    # Edit duration
    dur_match = re.search(r'(?:duration|time|minutes|min)\s*(?:to\s*)?(\d+)', text_lower)
    if dur_match:
        updated["duration_minutes"] = int(dur_match.group(1))
        
    # Regenerate summary based on edits
    hcp_name = updated.get("hcp_name") or "HCP"
    summary_text = f"Met with {hcp_name} via {updated.get('channel')}. Discussed {', '.join(updated.get('products_discussed', [])) or 'general updates'}. "
    if updated.get("samples_dropped"):
        sample_details = [f"{s.get('qty')} units of Lot {s.get('lot_number')}" for s in updated.get('samples_dropped', [])]
        summary_text += f"Dropped samples: {', '.join(sample_details)}. "
    summary_text += f"Sentiment was {updated.get('sentiment')}."
    updated["summary"] = summary_text

    return updated

# --- LangGraph Orchestrator Execution ---

def execute_agent_step(state: AgentState, db: Session) -> AgentState:
    """
    Main logic function that drives the agent node.
    Decides if we are creating a draft, editing a draft, checking compliance, or confirming.
    """
    last_message_content = state["messages"][-1]["content"] if state["messages"] else ""
    last_message_lower = last_message_content.lower().strip()
    
    # 1. Check for Confirmation
    if last_message_lower in ("confirm", "yes", "save", "ok", "confirm log", "submit"):
        if state.get("pending_extraction"):
            draft = state["pending_extraction"]
            
            # Check compliance first before committing!
            compliance = compliance_sample_check_tool(db, draft["hcp_id"], draft["samples_dropped"])
            if not compliance["compliant"]:
                state["warning"] = f"Compliance Block: {compliance['reason']}"
                state["messages"].append({
                    "role": "assistant",
                    "content": f"⚠️ Compliance Violation Blocked Save:\n{compliance['reason']}\n\nPlease correct the details before saving."
                })
                return state
                
            # Perform saving via service layer
            from backend.app.schemas import InteractionCreate, SampleDrop
            
            samples_schema = [
                SampleDrop(
                    product_id=s["product_id"],
                    sample_id=s["sample_id"],
                    qty=s["qty"]
                ) for s in draft["samples_dropped"]
            ]
            
            create_schema = InteractionCreate(
                hcp_id=draft["hcp_id"],
                channel=draft["channel"],
                interaction_datetime=datetime.datetime.fromisoformat(draft["interaction_datetime"]),
                duration_minutes=draft["duration_minutes"],
                discussion_topics=draft["discussion_topics"],
                products_discussed=draft["products_discussed"],
                sentiment=draft["sentiment"],
                samples_dropped=samples_schema,
                materials_shared=draft["materials_shared"],
                next_best_action=draft["next_best_action"],
                follow_up_date=datetime.date.fromisoformat(draft["follow_up_date"]) if draft.get("follow_up_date") else None,
                raw_transcript=draft["raw_transcript"],
                summary=draft["summary"],
                entry_mode="chat",
                status="confirmed"
            )
            
            try:
                # Default rep_id = 1 (Sarah Rep)
                new_interaction = create_interaction(db, create_schema, rep_id=1)
                state["pending_extraction"] = None
                state["warning"] = None
                state["messages"].append({
                    "role": "assistant",
                    "content": f"✅ Interaction successfully saved to CRM Database! (ID: {new_interaction.id}, Mode: Chat-Assisted). Compliance checks completed successfully."
                })
            except Exception as e:
                state["messages"].append({
                    "role": "assistant",
                    "content": f"❌ Error saving to database: {str(e)}"
                })
        else:
            state["messages"].append({
                "role": "assistant",
                "content": "There is no pending interaction draft to confirm. Please tell me about your visit to log an interaction."
            })
        return state

    # 2. Check if we are modifying an existing pending draft
    if state.get("pending_extraction"):
        # Rep wants to edit/change the draft
        updated_draft = apply_chat_edit(state["pending_extraction"], last_message_content, db)
        
        # Pre-check compliance on the updated draft
        compliance = compliance_sample_check_tool(db, updated_draft["hcp_id"], updated_draft["samples_dropped"])
        
        state["pending_extraction"] = updated_draft
        
        msg = f"I've updated the draft interaction details."
        if not compliance["compliant"]:
            state["warning"] = f"Compliance Warning: {compliance['reason']}"
            msg += f"\n\n⚠️ **Compliance Warning**: {compliance['reason']}"
        else:
            state["warning"] = None
            
        msg += "\n\nPlease review the updated card below and click 'Confirm' to save to the database."
        state["messages"].append({
            "role": "assistant",
            "content": msg
        })
        return state
        
    # 3. New Log Interaction Extraction
    try:
        # Check if GROQ_API_KEY is present.
        groq_key = os.environ.get("GROQ_API_KEY")
        if groq_key:
            # Here we would initialize ChatGroq and parse using structured outputs.
            # For robustness in local setups and speed, we integrate the actual code structure
            # but default to parser to show rich behavior, or run the LLM if keys exist.
            # Let's run a simple Groq call if key exists!
            try:
                from langchain_groq import ChatGroq
                from langchain_core.prompts import ChatPromptTemplate
                import json
                
                llm = ChatGroq(model="gemma2-9b-it", groq_api_key=groq_key, temperature=0.1)
                
                # Fetch list of HCPs, products, samples for LLM prompt context
                hcps_db = db.query(HCP).all()
                products_db = db.query(Product).all()
                samples_db = db.query(Sample).all()
                
                context = f"""
                HCPs available: {[{'id': h.id, 'name': h.name, 'specialty': h.specialty, 'institution': h.institution} for h in hcps_db]}
                Products available: {[{'id': p.id, 'name': p.name, 'dosage_forms': p.dosage_forms} for p in products_db]}
                Samples available: {[{'id': s.id, 'product_id': s.product_id, 'lot_number': s.lot_number, 'expiry_date': str(s.expiry_date)} for s in samples_db]}
                """
                
                system_prompt = f"""
                You are a CRM AI assistant for a life-sciences field representative.
                Your task is to parse a natural language visit summary and map it into structured JSON.
                
                Context metadata:
                {context}
                
                Extract:
                - hcp_id: Resolve from the HCP list.
                - channel: 'visit', 'call', 'virtual', 'email' (default 'visit').
                - duration_minutes: int (default 15).
                - sentiment: 'positive', 'neutral', 'negative', 'objection' (default 'positive').
                - discussion_topics: list of strings.
                - products_discussed: list of strings (names of products).
                - samples_dropped: list of objects with fields: product_id, sample_id, lot_number, product_name, qty.
                - follow_up_date: YYYY-MM-DD string. Calculate based on text (default 14 days from today: {datetime.date.today() + datetime.timedelta(days=14)}).
                - summary: 2-3 sentence overview of the meeting.
                
                Return ONLY a JSON block matching this structure:
                {{
                  "hcp_id": 1,
                  "hcp_name": "Dr. Amit Mehta",
                  "channel": "visit",
                  "duration_minutes": 15,
                  "discussion_topics": ["Efficacy"],
                  "products_discussed": ["CardioX"],
                  "sentiment": "positive",
                  "samples_dropped": [
                     {{"product_id": 1, "sample_id": 1, "lot_number": "CX10-2027", "product_name": "CardioX", "qty": 5}}
                  ],
                  "follow_up_date": "2026-07-22",
                  "summary": "Short meeting overview..."
                }}
                """
                
                response = llm.invoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=last_message_content)
                ])
                
                # Clean up markdown code blocks if any
                clean_content = response.content.strip()
                if "```json" in clean_content:
                    clean_content = clean_content.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_content:
                    clean_content = clean_content.split("```")[1].strip()
                
                parsed_json = json.loads(clean_content)
                
                # Ensure date fields and basic details are present
                parsed_json["interaction_datetime"] = datetime.datetime.now().isoformat()
                parsed_json["raw_transcript"] = last_message_content
                parsed_json["entry_mode"] = "chat"
                parsed_json["status"] = "draft"
                parsed_json["materials_shared"] = ["Clinical Brochure"]
                
                draft = parsed_json
            except Exception as ex:
                # Fall back if LLM parsing errors out
                draft = parse_with_rules(last_message_content, state.get("active_hcp_id"), db)
        else:
            # Run local rule parser
            draft = parse_with_rules(last_message_content, state.get("active_hcp_id"), db)
            
        # Check compliance for the newly generated draft
        compliance = compliance_sample_check_tool(db, draft["hcp_id"], draft["samples_dropped"])
        
        state["pending_extraction"] = draft
        
        assistant_content = f"I've extracted the visit details and prepared an interaction log draft."
        if not compliance["compliant"]:
            state["warning"] = f"Compliance Warning: {compliance['reason']}"
            assistant_content += f"\n\n⚠️ **Compliance Warning**: {compliance['reason']}"
        else:
            state["warning"] = None
            
        assistant_content += "\n\nPlease review the editable card below and click 'Confirm' to save it."
        
        state["messages"].append({
            "role": "assistant",
            "content": assistant_content
        })
        
    except Exception as e:
        state["messages"].append({
            "role": "assistant",
            "content": f"Sorry, I had trouble processing that input. Error: {str(e)}"
        })
        
    return state
