from uuid import uuid4

from langgraph.types import Command

from app.graph.workflow import workflow


def _config(workflow_id: str):
    return {"configurable": {"thread_id": workflow_id}}


def test_exception_pauses_for_human_approval_before_hold():
    workflow_id = f"wf-{uuid4()}"
    result = workflow.invoke({
        "workflow_id": workflow_id, "session_id": "session-test", "user_id": "tester",
        "user_query": "Investigate INV-1002", "entities": {"invoice_id": "INV-1002"},
        "tool_results": [], "errors": [], "retry_count": 0,
    }, _config(workflow_id))
    assert result["__interrupt__"][0].value["type"] == "human_approval_required"
    assert not any(item["tool"] == "place_invoice_on_hold" for item in result.get("tool_results", []))


def test_approval_is_required_before_action_and_response_claim():
    workflow_id = f"wf-{uuid4()}"
    workflow.invoke({
        "workflow_id": workflow_id, "session_id": "session-test", "user_id": "tester",
        "user_query": "Investigate INV-1002", "entities": {"invoice_id": "INV-1002"},
        "tool_results": [], "errors": [], "retry_count": 0,
    }, _config(workflow_id))
    result = workflow.invoke(Command(resume={"decision": "APPROVE", "reviewer": "controller", "rationale": "Verified receipt variance"}), _config(workflow_id))
    assert any(item["tool"] == "place_invoice_on_hold" and item["ok"] for item in result["tool_results"])
    assert "Invoice hold placed after human approval" in result["final_response"]
    assert result["validation_result"]["status"] == "PASS"


def test_rejection_never_executes_proposed_hold():
    workflow_id = f"wf-{uuid4()}"
    config = _config(workflow_id)
    workflow.invoke({
        "workflow_id": workflow_id, "session_id": "session-test", "user_id": "tester",
        "user_query": "Investigate INV-1002", "entities": {"invoice_id": "INV-1002"},
        "tool_results": [], "errors": [], "retry_count": 0,
    }, config)
    result = workflow.invoke(Command(resume={"decision": "REJECT", "reviewer": "controller"}), config)
    assert not any(item["tool"] == "place_invoice_on_hold" for item in result["tool_results"])
    assert "no financial action was executed" in result["final_response"]


def test_modify_can_create_only_allowlisted_exception_case():
    workflow_id = f"wf-{uuid4()}"
    config = _config(workflow_id)
    workflow.invoke({
        "workflow_id": workflow_id, "session_id": "session-test", "user_id": "tester",
        "user_query": "Investigate INV-1002", "entities": {"invoice_id": "INV-1002"},
        "tool_results": [], "errors": [], "retry_count": 0,
    }, config)
    result = workflow.invoke(Command(resume={"decision": "MODIFY", "modified_action": "create_exception_case", "reviewer": "controller"}), config)
    assert any(item["tool"] == "create_exception_case" and item["ok"] for item in result["tool_results"])
    assert not any(item["tool"] == "place_invoice_on_hold" for item in result["tool_results"])


def test_high_value_match_waits_for_review_without_proposing_hold():
    workflow_id = f"wf-{uuid4()}"
    config = _config(workflow_id)
    result = workflow.invoke({
        "workflow_id": workflow_id, "session_id": "session-test", "user_id": "tester",
        "user_query": "Review high-value invoice", "entities": {"invoice_id": "INV-1045"},
        "tool_results": [], "errors": [], "retry_count": 0,
    }, config)
    assert result["__interrupt__"][0].value["type"] == "human_approval_required"
    assert result["investigation_result"]["recommended_action"] == "manual_review_high_value"
    approved = workflow.invoke(Command(resume={"decision": "APPROVE", "reviewer": "controller"}), config)
    assert not any(item["tool"] == "place_invoice_on_hold" for item in approved["tool_results"])
    assert "No financial action has been executed" in approved["final_response"]
