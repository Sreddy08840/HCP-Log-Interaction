from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uuid
import os
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

load_dotenv()

from backend.app.database import init_db, get_db
from backend.app import models, schemas, services
from backend.app.agent.graph import execute_agent_step, AgentState
from backend.app.agent.tools import compliance_sample_check_tool

app = FastAPI(title="AI-First CRM — HCP Interaction API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup DB initialization
@app.on_event("startup")
def startup_event():
    print("Initializing Database...")
    init_db()
    print("Database Initialized & Seeded.")

# In-memory thread storage for LangGraph state persistence
threads_store: Dict[str, Dict[str, Any]] = {}

@app.get("/api/hcps", response_model=List[schemas.HCPResponse])
def read_hcps(q: Optional[str] = None, db: Session = Depends(get_db)):
    return services.search_hcps(db, q)

@app.get("/api/products", response_model=List[schemas.ProductResponse])
def read_products(db: Session = Depends(get_db)):
    return db.query(models.Product).all()

@app.get("/api/samples", response_model=List[schemas.SampleResponse])
def read_samples(db: Session = Depends(get_db)):
    return db.query(models.Sample).all()

@app.get("/api/interactions", response_model=List[schemas.InteractionResponse])
def read_interactions(db: Session = Depends(get_db)):
    # Fetch recent interactions
    interactions = db.query(models.Interaction).order_by(models.Interaction.created_at.desc()).all()
    # Serialize samples_dropped details for frontend display
    result = []
    for inter in interactions:
        inter_dict = {c.name: getattr(inter, c.name) for c in inter.__table__.columns}
        
        # Populate full detail of samples dropped (e.g. lot number and product name)
        detailed_samples = []
        for s in inter.samples_dropped:
            sample_obj = db.query(models.Sample).filter(models.Sample.id == s.get("sample_id")).first()
            prod_obj = db.query(models.Product).filter(models.Product.id == s.get("product_id")).first()
            detailed_samples.append({
                "product_id": s.get("product_id"),
                "sample_id": s.get("sample_id"),
                "qty": s.get("qty"),
                "lot_number": sample_obj.lot_number if sample_obj else "Unknown",
                "product_name": prod_obj.name if prod_obj else "Unknown"
            })
        inter_dict["samples_dropped"] = detailed_samples
        result.append(inter_dict)
    return result

@app.post("/api/interactions", response_model=schemas.InteractionResponse)
def create_new_interaction(data: schemas.InteractionCreate, db: Session = Depends(get_db)):
    # Verify samples compliance before creating via structured form!
    # Convert schema items to dictionaries for checking
    samples_dropped_check = [{"sample_id": s.sample_id, "product_id": s.product_id, "qty": s.qty} for s in data.samples_dropped]
    compliance = compliance_sample_check_tool(db, data.hcp_id, samples_dropped_check)
    if not compliance["compliant"]:
        raise HTTPException(
            status_code=400,
            detail=f"Compliance check failed: {compliance['reason']}"
        )
    
    # Default rep user id = 1
    db_interaction = services.create_interaction(db, data, rep_id=1)
    
    # Serialize response
    inter_dict = {c.name: getattr(db_interaction, c.name) for c in db_interaction.__table__.columns}
    inter_dict["samples_dropped"] = samples_dropped_check
    return inter_dict

@app.put("/api/interactions/{id}", response_model=schemas.InteractionResponse)
def update_existing_interaction(id: int, data: schemas.InteractionUpdate, db: Session = Depends(get_db)):
    # Default rep user id = 1
    try:
        # Pre-check compliance if samples are being updated
        if data.samples_dropped is not None:
            db_inter = db.query(models.Interaction).filter(models.Interaction.id == id).first()
            if not db_inter:
                raise HTTPException(status_code=404, detail="Interaction not found")
            
            hcp_id = data.hcp_id if data.hcp_id is not None else db_inter.hcp_id
            samples_dropped_check = [{"sample_id": s.sample_id, "product_id": s.product_id, "qty": s.qty} for s in data.samples_dropped]
            compliance = compliance_sample_check_tool(db, hcp_id, samples_dropped_check)
            if not compliance["compliant"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Compliance check failed: {compliance['reason']}"
                )

        db_interaction = services.update_interaction(db, id, data, rep_id=1)
        
        # Serialize response
        inter_dict = {c.name: getattr(db_interaction, c.name) for c in db_interaction.__table__.columns}
        
        detailed_samples = []
        for s in db_interaction.samples_dropped:
            sample_obj = db.query(models.Sample).filter(models.Sample.id == s.get("sample_id")).first()
            prod_obj = db.query(models.Product).filter(models.Product.id == s.get("product_id")).first()
            detailed_samples.append({
                "product_id": s.get("product_id"),
                "sample_id": s.get("sample_id"),
                "qty": s.get("qty"),
                "lot_number": sample_obj.lot_number if sample_obj else "Unknown",
                "product_name": prod_obj.name if prod_obj else "Unknown"
            })
        inter_dict["samples_dropped"] = detailed_samples
        return inter_dict
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/audit-logs", response_model=List[schemas.AuditLogResponse])
def read_audit_logs(db: Session = Depends(get_db)):
    return db.query(models.InteractionAuditLog).order_by(models.InteractionAuditLog.changed_at.desc()).all()

@app.post("/api/agent/chat", response_model=schemas.ChatResponse)
def agent_chat(req: schemas.ChatRequest, db: Session = Depends(get_db)):
    thread_id = req.thread_id
    if not thread_id:
        thread_id = uuid.uuid4().hex
        
    # Get or initialize state
    if thread_id not in threads_store:
        threads_store[thread_id] = {
            "messages": [
                {
                    "role": "assistant",
                    "content": "Hello! I am your AI assistant. Tell me about your HCP visit to log an interaction, or ask me for details."
                }
            ],
            "thread_id": thread_id,
            "active_hcp_id": req.active_hcp_id,
            "pending_extraction": None,
            "warning": None
        }
        
    # Retrieve state
    state: AgentState = threads_store[thread_id]
    
    # Update active HCP if passed
    if req.active_hcp_id:
        state["active_hcp_id"] = req.active_hcp_id
        
    # Append user message
    state["messages"].append({
        "role": "user",
        "content": req.message
    })
    
    # Run one step of the agent state graph
    updated_state = execute_agent_step(state, db)
    
    # Save back to threads store
    threads_store[thread_id] = updated_state
    
    # Check warning key and add GROQ missing key message if no Groq Key in env
    warning = updated_state.get("warning")
    groq_warning = None
    if not os.environ.get("GROQ_API_KEY"):
        groq_warning = "Demo Mode: Running in local keyword extraction mode (GROQ_API_KEY is not configured)."
        
    # Build Pydantic response
    chat_messages = [
        schemas.ChatMessage(role=m["role"], content=m["content"])
        for m in updated_state["messages"]
    ]
    
    return schemas.ChatResponse(
        messages=chat_messages,
        thread_id=thread_id,
        pending_extraction=updated_state.get("pending_extraction"),
        warning=warning or groq_warning
    )
