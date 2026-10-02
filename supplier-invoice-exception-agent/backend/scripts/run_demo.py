from uuid import uuid4

from langgraph.types import Command

from app.graph.workflow import workflow


def main() -> None:
    workflow_id = f"demo-{uuid4()}"
    config = {"configurable": {"thread_id": workflow_id}}
    result = workflow.invoke({
        "workflow_id": workflow_id, "session_id": "demo-session", "user_id": "demo-user",
        "user_query": "Investigate invoice INV-1002", "entities": {"invoice_id": "INV-1002"},
        "tool_results": [], "errors": [], "retry_count": 0,
    }, config)
    if result.get("__interrupt__"):
        print("Approval required. No financial action has been executed.")
        print(result["__interrupt__"][0].value)
        decision = input("Type APPROVE, REJECT, or MODIFY: ").strip().upper()
        result = workflow.invoke(Command(resume={"decision": decision, "reviewer": "local-demo", "rationale": "Interactive demo decision"}), config)
    print(result.get("final_response", "Workflow stopped for manual review."))


if __name__ == "__main__":
    main()