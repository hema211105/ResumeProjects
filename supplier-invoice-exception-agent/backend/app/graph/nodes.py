import logging
from typing import Any

from langgraph.types import interrupt

from app.schemas import Evidence, InvestigationResult
from app.tools.finance import create_exception_case, find_goods_receipt_by_po, get_invoice, get_purchase_order, place_invoice_on_hold

logger = logging.getLogger(__name__)
TAX_RATE = 0.08
HIGH_VALUE_THRESHOLD = 5000.0


def supervisor(state: dict[str, Any]) -> dict[str, Any]:
    return {"intent": "invoice_exception_investigation", "current_stage": "Supervisor", "entities": {"invoice_id": state.get("entities", {}).get("invoice_id")}}


def invoice_extraction(state: dict[str, Any]) -> dict[str, Any]:
    invoice_id = state.get("entities", {}).get("invoice_id") or state.get("invoice_id")
    result = get_invoice(str(invoice_id))
    if not result.ok:
        return {"errors": [*state.get("errors", []), result.error or "Invoice extraction failed"], "current_stage": "Invoice Extraction"}
    return {"invoice": result.data, "tool_results": [*state.get("tool_results", []), result.model_dump()], "current_stage": "Invoice Extraction"}


def po_matching(state: dict[str, Any]) -> dict[str, Any]:
    invoice = state.get("invoice", {})
    po_number = invoice.get("po_number")
    result = get_purchase_order(str(po_number)) if po_number else None
    po = result.data if result and result.ok else None
    discrepancies = []
    if po is None:
        discrepancies.append("Purchase order is missing or unavailable")
    else:
        if po["supplier"] != invoice["supplier"]:
            discrepancies.append("Supplier does not match the purchase order")
        if po["currency"] != invoice["currency"]:
            discrepancies.append("Currency does not match the purchase order")
        if abs(po["unit_price"] - invoice["unit_price"]) > 0.01:
            discrepancies.append(f"Invoice unit price {invoice['unit_price']:.2f} differs from PO {po['unit_price']:.2f}")
        if invoice["quantity"] > po["quantity"]:
            discrepancies.append(f"Invoice quantity {invoice['quantity']:g} exceeds ordered quantity {po['quantity']:g}")
    tool_results = [*state.get("tool_results", []), result.model_dump()] if result else state.get("tool_results", [])
    return {"purchase_order": po, "entities": {**state.get("entities", {}), "po_discrepancies": discrepancies}, "tool_results": tool_results, "current_stage": "PO Matching"}


def goods_receipt_validation(state: dict[str, Any]) -> dict[str, Any]:
    invoice = state.get("invoice", {})
    po_number = invoice.get("po_number")
    result = find_goods_receipt_by_po(str(po_number)) if po_number else None
    receipt = result.data if result and result.ok else None
    discrepancies = []
    if receipt is None:
        discrepancies.append("No goods receipt found for this purchase order")
    elif invoice.get("quantity", 0) > receipt["quantity_received"]:
        discrepancies.append(f"Invoice bills {invoice['quantity']:g} units; receipt supports {receipt['quantity_received']:g}")
    return {
        "goods_receipt": receipt,
        "entities": {**state.get("entities", {}), "receipt_discrepancies": discrepancies},
        "tool_results": [*state.get("tool_results", []), result.model_dump()] if result else state.get("tool_results", []),
        "current_stage": "Goods Receipt Validation",
    }


def tax_validation(state: dict[str, Any]) -> dict[str, Any]:
    invoice = state.get("invoice", {})
    expected = round(float(invoice.get("subtotal", 0)) * TAX_RATE, 2)
    actual = round(float(invoice.get("tax", 0)), 2)
    return {
        "tax_result": {"valid": abs(expected - actual) <= 0.02, "expected_tax": expected, "invoice_tax": actual, "rate": TAX_RATE,
                        "message": "Tax matches the synthetic 8% rule" if abs(expected - actual) <= 0.02 else f"Tax differs from expected amount {expected:.2f}"},
        "current_stage": "Tax Validation",
    }


def policy_rag(state: dict[str, Any]) -> dict[str, Any]:
    from app.rag.retriever import search_documents

    invoice = state.get("invoice", {})
    issue_context = " ".join(state.get("entities", {}).get("po_discrepancies", []) + state.get("entities", {}).get("receipt_discrepancies", []))
    query = f"{issue_context} invoice tax approval threshold {invoice.get('total', '')}"
    documents = search_documents(query, k=4)
    from app.rag.generation import generate_grounded_answer

    answer = generate_grounded_answer(query, documents)
    return {"retrieved_documents": documents, "policy_answer": answer, "current_stage": "Policy RAG"}


def investigation(state: dict[str, Any]) -> dict[str, Any]:
    invoice = state.get("invoice", {})
    po = state.get("purchase_order")
    receipt = state.get("goods_receipt")
    tax_result = state.get("tax_result", {})
    po_issues = state.get("entities", {}).get("po_discrepancies", [])
    receipt_issues = state.get("entities", {}).get("receipt_discrepancies", [])
    issues = [*po_issues, *receipt_issues]
    if not tax_result.get("valid", False):
        issues.append(tax_result.get("message", "Tax could not be validated"))
    if not issues:
        issues = ["No discrepancy detected across the available invoice, PO, receipt, and tax evidence"]
    issue_type = "no_exception" if len(issues) == 1 and issues[0].startswith("No discrepancy") else "quantity_mismatch" if receipt_issues or any("quantity" in issue.lower() for issue in po_issues) else "tax_mismatch" if not tax_result.get("valid") else "po_mismatch"
    evidence = [Evidence(claim=f"Invoice {invoice.get('invoice_id')} bills {invoice.get('quantity')} units at {invoice.get('currency')} {invoice.get('unit_price')} each.", source="Supplier invoice", citation=f"invoice:{invoice.get('invoice_id')}")]
    if po:
        evidence.append(Evidence(claim=f"PO {po['id']} authorizes {po['quantity']} units at {po['currency']} {po['unit_price']} each for {po['supplier']}.", source="Purchase order", citation=f"purchase_order:{po['id']}"))
    if receipt:
        evidence.append(Evidence(claim=f"Goods receipt {receipt['id']} records {receipt['quantity_received']} units received.", source="Goods receipt", citation=f"goods_receipt:{receipt['id']}"))
    evidence.append(Evidence(claim=tax_result.get("message", "Tax rule unavailable"), source="Tax validation", citation="rule:synthetic-standard-tax"))
    retrieved = state.get("retrieved_documents", [])
    for document in retrieved:
        evidence.append(Evidence(claim=document.get("excerpt", "")[:300], source=document.get("title", "Policy document"), citation=document.get("citation", f"{document.get('document_id', 'document')}:{document.get('section', 'General')}")))
    requires_approval = issue_type != "no_exception" or float(invoice.get("total", 0)) > HIGH_VALUE_THRESHOLD
    action = "place_invoice_on_hold" if issue_type != "no_exception" else "manual_review_high_value" if float(invoice.get("total", 0)) > HIGH_VALUE_THRESHOLD else "release_for_standard_ap"
    result = InvestigationResult(
        issue_type=issue_type, summary=" ".join(issues), evidence=evidence,
        policy_reference=[f"{document.get('title', 'Policy')} § {document.get('section', 'General')}" for document in retrieved] or ["No policy document was retrieved; manual policy review required"],
        recommended_action=action, confidence=0.94 if po and receipt and tax_result.get("valid") else 0.72,
        requires_human_review=requires_approval,
    )
    proposed = [{"action": action, "consequential": action == "place_invoice_on_hold", "requires_approval": requires_approval}]
    return {"investigation_result": result.model_dump(), "proposed_actions": proposed, "confidence": result.confidence, "current_stage": "Exception Investigation"}


def approval(state: dict[str, Any]) -> dict[str, Any]:
    decision = interrupt({
        "type": "human_approval_required", "workflow_id": state["workflow_id"],
        "invoice_id": state.get("invoice", {}).get("invoice_id"),
        "proposed_actions": state.get("proposed_actions", []), "investigation": state.get("investigation_result", {}),
    })
    return {"human_approval": decision, "current_stage": "Human Approval"}


def execute_approved_action(state: dict[str, Any]) -> dict[str, Any]:
    approval_result = state.get("human_approval") or {}
    if approval_result.get("decision") not in {"APPROVE", "MODIFY"}:
        return {"tool_results": state.get("tool_results", []), "current_stage": "Action Not Executed"}
    proposed_action = state.get("investigation_result", {}).get("recommended_action")
    action = approval_result.get("modified_action") or proposed_action
    if action == "release_for_standard_ap" or action == "manual_review_high_value":
        return {"current_stage": "Human Review Recorded; No Financial Action"}
    if action not in {"place_invoice_on_hold", "create_exception_case"}:
        return {"errors": [*state.get("errors", []), "Unsupported modified action; no action executed"], "current_stage": "Action Blocked"}
    if action == "place_invoice_on_hold":
        result = place_invoice_on_hold(state.get("invoice", {}).get("invoice_id", ""), authorized=True)
    else:
        result = create_exception_case(state.get("invoice", {}).get("invoice_id", ""), state.get("investigation_result", {}).get("issue_type", "unknown"))
    return {"tool_results": [*state.get("tool_results", []), result.model_dump()], "current_stage": "Approved Action"}


def validator(state: dict[str, Any]) -> dict[str, Any]:
    result = state.get("investigation_result", {})
    citations_present = bool(result.get("evidence")) and all(item.get("citation") for item in result.get("evidence", []))
    action = result.get("recommended_action")
    approved = (state.get("human_approval") or {}).get("decision") in {"APPROVE", "MODIFY"}
    action_results = [item for item in state.get("tool_results", []) if item.get("tool") == "place_invoice_on_hold" and item.get("ok")]
    if action == "place_invoice_on_hold" and action_results and not approved:
        status, reason = "BLOCK", "Sensitive action has no recorded human approval"
    elif not state.get("invoice") or not citations_present:
        status, reason = "HUMAN_REVIEW", "Required invoice evidence or citations are missing"
    elif state.get("errors"):
        status, reason = "HUMAN_REVIEW", "Workflow encountered an error requiring operator review"
    elif result.get("requires_human_review") and not state.get("human_approval"):
        status, reason = "HUMAN_REVIEW", "Human approval is pending"
    elif result.get("confidence", 0) < 0.6:
        status, reason = ("RETRY" if state.get("retry_count", 0) < 2 else "HUMAN_REVIEW"), "Confidence is below the automated threshold"
    else:
        status, reason = "PASS", "Evidence and policy checks passed"
    return {"validation_result": {"status": status, "reason": reason, "citations_present": citations_present}, "current_stage": "Validation"}


def response(state: dict[str, Any]) -> dict[str, Any]:
    invoice = state.get("invoice", {})
    finding = state.get("investigation_result", {})
    validation = state.get("validation_result", {})
    approval_state = state.get("human_approval") or {}
    successful_actions = [item["tool"] for item in state.get("tool_results", []) if item.get("ok") and item.get("tool") in {"place_invoice_on_hold", "create_exception_case"}]
    action_line = "Invoice hold placed after human approval." if "place_invoice_on_hold" in successful_actions else "Exception case created after human approval." if "create_exception_case" in successful_actions else "No financial action has been executed."
    if approval_state.get("decision") == "REJECT":
        action_line = "The proposed action was rejected; no financial action was executed."
    citations = "; ".join(item["citation"] for item in finding.get("evidence", []))
    message = (
        f"Invoice {invoice.get('invoice_id', 'unknown')} ({invoice.get('supplier', 'supplier unknown')}, {invoice.get('currency', '')} {invoice.get('total', 0):,.2f}). "
        f"Finding: {finding.get('summary', 'Insufficient information to investigate')}. "
        f"Recommendation: {finding.get('recommended_action', 'manual_review')}. {action_line} "
        f"Validation: {validation.get('status', 'PENDING')} - {validation.get('reason', 'not yet completed')}. "
        f"Approval: {approval_state.get('decision', 'PENDING' if finding.get('requires_human_review') else 'NOT_REQUIRED')}. "
        f"Evidence: {citations or 'none'}"
    )
    return {"final_response": message, "current_stage": "Response"}
