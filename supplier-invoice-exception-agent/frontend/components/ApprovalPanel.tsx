import { Check, CircleAlert, Pencil, X } from "lucide-react";

type Finding = {
  recommended_action: string;
  summary: string;
  confidence: number;
  policy_reference: string[];
  evidence: { claim: string; citation: string }[];
};

export function ApprovalPanel({ pending, finding, decision, loading, onDecision }: {
  pending: boolean;
  finding?: Finding;
  decision?: string;
  loading: boolean;
  onDecision: (decision: "APPROVE" | "REJECT" | "MODIFY") => void;
}) {
  return (
    <section className={`panel approval-panel ${pending ? "approval-pending" : ""}`}>
      <div className="panel-heading">
        <div><span className="eyebrow">HUMAN CONTROL</span><h2>Action review</h2></div>
        {pending ? <CircleAlert size={18} /> : <span className="approval-status">{decision ?? "NOT REQUIRED"}</span>}
      </div>
      {!finding ? <p className="empty-state">A proposed action and its evidence will be shown here.</p> : (
        <>
          <div className="action-summary"><span>PROPOSED ACTION</span><strong>{finding.recommended_action.replaceAll("_", " ")}</strong><p>{finding.summary}</p></div>
          <div className="approval-meta"><span>Confidence <b>{Math.round(finding.confidence * 100)}%</b></span><span>Policy <b>{finding.policy_reference.length} references</b></span></div>
          {pending ? <div className="approval-actions">
            <button className="button button-primary" disabled={loading} onClick={() => onDecision("APPROVE")}><Check size={16} /> Approve</button>
            <button className="button button-secondary" disabled={loading} onClick={() => onDecision("MODIFY")}><Pencil size={15} /> Modify</button>
            <button className="button button-quiet" disabled={loading} onClick={() => onDecision("REJECT")}><X size={16} /> Reject</button>
          </div> : <p className="approval-closed">{decision ? `Decision recorded: ${decision.toLowerCase()}.` : "No consequential action is waiting for approval."}</p>}
        </>
      )}
    </section>
  );
}