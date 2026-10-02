from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.core.config import get_settings
from app.agents.approval import run as approval
from app.agents.goods_receipt import run as goods_receipt_validation
from app.agents.investigation import run as investigation
from app.agents.invoice_extraction import run as invoice_extraction
from app.agents.policy_rag import run as policy_rag
from app.agents.po_matching import run as po_matching
from app.agents.response import run as response
from app.agents.supervisor import run as supervisor
from app.agents.tax_validation import run as tax_validation
from app.agents.validator import run as validator
from app.graph.nodes import execute_approved_action
from app.graph.state import AgentState

checkpointer = MemorySaver()


def _after_investigation(state: AgentState) -> str:
    return "approval" if state.get("investigation_result", {}).get("requires_human_review") else "validator"


def _after_approval(state: AgentState) -> str:
    return "execute_action" if (state.get("human_approval") or {}).get("decision") in {"APPROVE", "MODIFY"} else "validator"


def _after_validation(state: AgentState) -> str:
    status = state.get("validation_result", {}).get("status")
    if status == "RETRY" and state.get("retry_count", 0) < get_settings().max_workflow_retries:
        return "retry_investigation"
    return "response"


def build_workflow(checkpointer=None):
    graph = StateGraph(AgentState)
    graph.add_node("supervisor", supervisor)
    graph.add_node("invoice_extraction", invoice_extraction)
    graph.add_node("po_matching", po_matching)
    graph.add_node("goods_receipt_validation", goods_receipt_validation)
    graph.add_node("tax_validation", tax_validation)
    graph.add_node("policy_rag", policy_rag)
    graph.add_node("investigation", investigation)
    graph.add_node("approval", approval)
    graph.add_node("execute_action", execute_approved_action)
    graph.add_node("validator", validator)
    graph.add_node("retry_investigation", lambda state: {**investigation(state), "retry_count": state.get("retry_count", 0) + 1})
    graph.add_node("response", response)
    graph.add_edge(START, "supervisor")
    graph.add_edge("supervisor", "invoice_extraction")
    graph.add_edge("invoice_extraction", "po_matching")
    graph.add_edge("po_matching", "goods_receipt_validation")
    graph.add_edge("goods_receipt_validation", "tax_validation")
    graph.add_edge("tax_validation", "policy_rag")
    graph.add_edge("policy_rag", "investigation")
    graph.add_conditional_edges("investigation", _after_investigation, {"approval": "approval", "validator": "validator"})
    graph.add_conditional_edges("approval", _after_approval, {"execute_action": "execute_action", "validator": "validator"})
    graph.add_edge("execute_action", "validator")
    graph.add_conditional_edges("validator", _after_validation, {"retry_investigation": "retry_investigation", "response": "response"})
    graph.add_edge("retry_investigation", "validator")
    graph.add_edge("response", END)
    return graph.compile(checkpointer=checkpointer or MemorySaver())


workflow = build_workflow()
