import json
from pathlib import Path
from uuid import uuid4

from langgraph.types import Command

from app.graph.workflow import workflow

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evaluation" / "dataset.json"


def main() -> None:
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    category_counts: dict[str, int] = {}
    citation_count = 0
    review_correct = 0
    safe_pauses = 0
    for case in cases:
        category_counts[case["category"]] = category_counts.get(case["category"], 0) + 1
        workflow_id = f"eval-{uuid4()}"
        config = {"configurable": {"thread_id": workflow_id}}
        result = workflow.invoke({
            "workflow_id": workflow_id, "session_id": "evaluation", "user_id": "evaluator",
            "user_query": case.get("query", f"Investigate {case['invoice_id']}"),
            "entities": {"invoice_id": case["invoice_id"]}, "tool_results": [], "errors": [], "retry_count": 0,
        }, config)
        is_paused = bool(result.get("__interrupt__"))
        if is_paused == case["expected_review"]:
            review_correct += 1
        if is_paused and not any(item.get("tool") == "place_invoice_on_hold" for item in result.get("tool_results", [])):
            safe_pauses += 1
        citation_count += int(bool(result.get("investigation_result", {}).get("evidence")))
        if is_paused:
            workflow.invoke(Command(resume={"decision": "REJECT", "reviewer": "evaluation"}), config)
    report = {
        "cases": len(cases), "categories": category_counts,
        "human_escalation_accuracy": round(review_correct / max(len(cases), 1), 3),
        "evidence_coverage": round(citation_count / max(len(cases), 1), 3),
        "safe_pending_approval_pauses": safe_pauses,
        "note": "Deterministic local regression metrics, not a substitute for blinded quality evaluation or production telemetry.",
    }
    print(json.dumps(report, indent=2))
    (ROOT / "evaluation" / "report.md").write_text(
        "# Evaluation Report\n\n```json\n" + json.dumps(report, indent=2) + "\n```\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()