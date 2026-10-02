import logging
import re
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from langgraph.types import Command
from sqlalchemy import text

from app.core.config import get_settings
from app.core.logging import configure_logging, request_id_var
from app.graph.workflow import build_workflow, workflow
from app.models.db import Base, SessionLocal, engine
from app.models.tables import Approval, AuditLog, Session, Workflow
from app.rag.ingestion import ingest
from app.rag.retriever import search_documents
from app.schemas import ApprovalRequest, ChatRequest, RunRequest
from app.tools.finance import record_approval

settings = get_settings()
configure_logging()
logger = logging.getLogger(__name__)
checkpoint_manager = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global checkpoint_manager, workflow
    Base.metadata.create_all(bind=engine)
    if settings.database_url.startswith("postgresql"):
        from langgraph.checkpoint.postgres import PostgresSaver
        from sqlalchemy.engine import make_url

        dsn = make_url(settings.database_url).set(drivername="postgresql").render_as_string(hide_password=False)
        checkpoint_manager = PostgresSaver.from_conn_string(dsn)
        checkpointer = checkpoint_manager.__enter__()
        checkpointer.setup()
        workflow = build_workflow(checkpointer=checkpointer)
    yield
    if checkpoint_manager is not None:
        checkpoint_manager.__exit__(None, None, None)


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    token = request_id_var.set(request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-ms"] = str(round((time.perf_counter() - started) * 1000))
        return response
    finally:
        request_id_var.reset(token)


def _workflow_response(state: dict, workflow_id: str, status: str) -> dict:
    return {
        "workflow_id": workflow_id,
        "status": status,
        "current_stage": state.get("current_stage"),
        "invoice": state.get("invoice"),
        "investigation_result": state.get("investigation_result"),
        "retrieved_documents": state.get("retrieved_documents", []),
        "tool_results": state.get("tool_results", []),
        "validation_result": state.get("validation_result"),
        "human_approval": state.get("human_approval"),
        "final_response": state.get("final_response"),
        "pending_approval": status == "awaiting_approval",
    }


def _save_workflow(state: dict, workflow_id: str, session_id: str, status: str) -> None:
    with SessionLocal() as db:
        row = db.get(Workflow, workflow_id)
        values = {key: value for key, value in state.items() if key != "__interrupt__"}
        if row is None:
            row = Workflow(id=workflow_id, session_id=session_id, status=status, invoice_id=state.get("invoice", {}).get("invoice_id"), state=values)
            db.add(row)
        else:
            row.status, row.state = status, values
        db.add(AuditLog(workflow_id=workflow_id, actor="agent", event="workflow_state", details={"status": status, "stage": state.get("current_stage")}))
        db.commit()


def _start_run(request: RunRequest) -> dict:
    workflow_id = str(uuid4())
    session_id = request.session_id or str(uuid4())
    config = {"configurable": {"thread_id": workflow_id}}
    with SessionLocal() as db:
        if db.get(Session, session_id) is None:
            db.add(Session(id=session_id, title=f"Invoice {request.invoice_id}"))
            db.commit()
    state = workflow.invoke({
        "workflow_id": workflow_id, "session_id": session_id, "user_id": request.user_id,
        "user_query": request.query, "conversation_history": [], "intent": "invoice_exception_investigation",
        "entities": {"invoice_id": request.invoice_id}, "tool_results": [], "errors": [], "retry_count": 0,
    }, config)
    status = "awaiting_approval" if state.get("__interrupt__") else "completed"
    _save_workflow(state, workflow_id, session_id, status)
    return _workflow_response(state, workflow_id, status)


@app.post("/api/agent/run")
def run_agent(request: RunRequest):
    return _start_run(request)


@app.post("/api/chat")
def chat(request: ChatRequest):
    invoice_match = re.search(r"\bINV-\d+\b", request.message, re.IGNORECASE)
    if not invoice_match:
        raise HTTPException(status_code=422, detail="Include an invoice identifier such as INV-1001 to start an investigation.")
    return _start_run(RunRequest(invoice_id=invoice_match.group(0).upper(), user_id=request.user_id, session_id=request.session_id, query=request.message))


@app.post("/api/approval/{workflow_id}")
def submit_approval(workflow_id: str, request: ApprovalRequest):
    with SessionLocal() as db:
        row = db.get(Workflow, workflow_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        if row.status != "awaiting_approval":
            raise HTTPException(status_code=409, detail="Workflow is not awaiting approval")
        record_approval(workflow_id, request.decision, request.reviewer, request.rationale)
        db.add(Approval(workflow_id=workflow_id, decision=request.decision, reviewer=request.reviewer, rationale=request.rationale))
        db.add(AuditLog(workflow_id=workflow_id, actor=request.reviewer, event="approval_decision", details=request.model_dump()))
        db.commit()
        session_id = row.session_id
    config = {"configurable": {"thread_id": workflow_id}}
    resume = request.model_dump()
    result = workflow.invoke(Command(resume=resume), config)
    status = "completed"
    _save_workflow(result, workflow_id, session_id, status)
    return _workflow_response(result, workflow_id, status)


@app.get("/api/workflows/{workflow_id}")
def get_workflow(workflow_id: str):
    with SessionLocal() as db:
        row = db.get(Workflow, workflow_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        result = _workflow_response(row.state, workflow_id, row.status)
        result["audit"] = [item.details for item in db.query(AuditLog).filter_by(workflow_id=workflow_id).all()]
        return result


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    with SessionLocal() as db:
        session = db.get(Session, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        runs = db.query(Workflow).filter_by(session_id=session_id).order_by(Workflow.created_at).all()
        return {"session_id": session_id, "title": session.title, "workflows": [_workflow_response(run.state, run.id, run.status) for run in runs]}


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith((".md", ".txt")):
        raise HTTPException(status_code=415, detail="Only .md and .txt policy documents are accepted")
    contents = await file.read(settings.upload_max_bytes + 1)
    if len(contents) > settings.upload_max_bytes:
        raise HTTPException(status_code=413, detail="Document exceeds the 10 MB upload limit")
    if b"\x00" in contents:
        raise HTTPException(status_code=415, detail="Binary content is not accepted")
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", file.filename)
    target = __import__("pathlib").Path(__file__).resolve().parents[3] / "data" / "knowledge_base" / "uploads" / safe_name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(contents)
    return {"filename": safe_name, "bytes": len(contents), "status": "uploaded", "next_step": "POST /api/documents/ingest"}


@app.post("/api/documents/ingest")
def ingest_documents():
    return {"status": "ingested", **ingest()}


@app.get("/api/health")
def health():
    database = "ok"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        database = "unavailable"
    return {"status": "ok" if database == "ok" else "degraded", "database": database, "rag": "ready"}


@app.get("/api/metrics")
def metrics():
    with SessionLocal() as db:
        return {
            "workflows": db.query(Workflow).count(),
            "awaiting_approval": db.query(Workflow).filter_by(status="awaiting_approval").count(),
            "approvals": db.query(Approval).count(),
            "documents": len(search_documents("invoice policy", k=20)),
        }
