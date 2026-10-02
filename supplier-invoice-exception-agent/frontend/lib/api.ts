export type WorkflowResult = {
  workflow_id: string;
  status: string;
  current_stage?: string;
  invoice?: { invoice_id: string; supplier: string; currency: string; total: number; quantity: number; unit_price: number };
  investigation_result?: {
    issue_type: string;
    summary: string;
    recommended_action: string;
    confidence: number;
    requires_human_review: boolean;
    evidence: { claim: string; source: string; citation: string }[];
    policy_reference: string[];
  };
  retrieved_documents: { title: string; section: string; citation: string; excerpt: string; category: string }[];
  tool_results: { tool: string; ok: boolean; error?: string; data?: unknown }[];
  validation_result?: { status: string; reason: string };
  human_approval?: { decision: string; reviewer?: string; rationale?: string };
  final_response?: string;
  pending_approval: boolean;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

async function parseResponse(response: Response) {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${response.status})`);
  }
  return response.json();
}

export async function runInvestigation(invoiceId: string, sessionId?: string): Promise<WorkflowResult> {
  const response = await fetch(`${API_URL}/agent/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ invoice_id: invoiceId, session_id: sessionId, query: `Investigate ${invoiceId}` }),
  });
  return parseResponse(response);
}

export async function submitApproval(workflowId: string, decision: "APPROVE" | "REJECT" | "MODIFY"): Promise<WorkflowResult> {
  const response = await fetch(`${API_URL}/approval/${workflowId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision, reviewer: "ap.reviewer", rationale: "Reviewed invoice evidence in the AP console", modified_action: decision === "MODIFY" ? "create_exception_case" : undefined }),
  });
  return parseResponse(response);
}