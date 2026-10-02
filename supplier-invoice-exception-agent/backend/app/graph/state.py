from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    session_id: str
    user_id: str
    workflow_id: str
    user_query: str
    conversation_history: list[dict[str, str]]
    intent: str
    entities: dict[str, Any]
    invoice: dict[str, Any]
    purchase_order: dict[str, Any] | None
    goods_receipt: dict[str, Any] | None
    tax_result: dict[str, Any]
    retrieved_documents: list[dict[str, Any]]
    policy_answer: dict[str, Any]
    investigation_result: dict[str, Any]
    proposed_actions: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    confidence: float
    validation_result: dict[str, Any]
    human_approval: dict[str, Any] | None
    errors: list[str]
    final_response: str
    retry_count: int
    current_stage: str
