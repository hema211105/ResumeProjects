"use client";

import { useState } from "react";
import { ArrowUpRight, FileSearch, LoaderCircle, ShieldCheck, Sparkles } from "lucide-react";
import { ApprovalPanel } from "@/components/ApprovalPanel";
import { SourcesPanel } from "@/components/SourcesPanel";
import { ToolActivity } from "@/components/ToolActivity";
import { WorkflowSteps } from "@/components/WorkflowSteps";
import { runInvestigation, submitApproval, type WorkflowResult } from "@/lib/api";

const examples = ["INV-1001", "INV-1002", "INV-1003"];

export default function Home() {
  const [invoiceId, setInvoiceId] = useState("INV-1002");
  const [result, setResult] = useState<WorkflowResult>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function investigate(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try { setResult(await runInvestigation(invoiceId.trim().toUpperCase())); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Investigation could not be started."); }
    finally { setLoading(false); }
  }

  async function decide(decision: "APPROVE" | "REJECT" | "MODIFY") {
    if (!result) return;
    setLoading(true);
    setError("");
    try { setResult(await submitApproval(result.workflow_id, decision)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Approval could not be recorded."); }
    finally { setLoading(false); }
  }

  const finding = result?.investigation_result;
  const issueTone = finding?.issue_type === "no_exception" ? "clear" : finding ? "flagged" : "neutral";

  return (
    <main className="shell">
      <header className="topbar">
        <a className="brand" href="#desk"><span className="brand-mark">L</span><span>LEDGERLINE<span className="brand-sub">ACCOUNTS PAYABLE</span></span></a>
        <div className="topbar-right"><span className="environment"><i /> DEVELOPMENT ENVIRONMENT</span><button className="avatar" aria-label="Reviewer account">AP</button></div>
      </header>
      <div className="page-heading" id="desk">
        <div><span className="eyebrow">EXCEPTION OPERATIONS / 02 OCT 2026</span><h1>Invoice investigation desk</h1><p>Resolve supplier discrepancies with source evidence and controlled actions.</p></div>
        <div className="secure-note"><ShieldCheck size={18} /><span>Human authorization required<br /><b>for every financial state change</b></span></div>
      </div>

      <div className="desk-grid">
        <div className="main-column">
          <section className="intake-panel">
            <div className="intake-icon"><FileSearch size={21} /></div>
            <div className="intake-content"><span className="eyebrow">START AN INVESTIGATION</span><h2>Which invoice needs attention?</h2>
              <form onSubmit={investigate} className="invoice-form">
                <label className="sr-only" htmlFor="invoice-id">Invoice identifier</label>
                <input id="invoice-id" value={invoiceId} onChange={(event) => setInvoiceId(event.target.value)} placeholder="e.g. INV-1002" required />
                <button className="button button-primary" disabled={loading || !invoiceId.trim()}>{loading ? <LoaderCircle className="spin" size={16} /> : <Sparkles size={16} />} Investigate <ArrowUpRight size={15} /></button>
              </form>
              <div className="examples"><span>DEMO RECORDS</span>{examples.map((example) => <button key={example} onClick={() => setInvoiceId(example)}>{example}</button>)}</div>
              {error && <p className="error-message" role="alert">{error}</p>}
            </div>
          </section>

          <section className="panel progress-panel">
            <div className="panel-heading"><div><span className="eyebrow">LANGGRAPH ORCHESTRATION</span><h2>Investigation workflow</h2></div><span className={`workflow-state ${result?.pending_approval ? "waiting" : ""}`}>{result?.pending_approval ? "AWAITING REVIEW" : result ? "COMPLETED" : "READY"}</span></div>
            <WorkflowSteps current={result?.current_stage} pending={Boolean(result?.pending_approval)} />
          </section>

          <section className="panel findings-panel">
            <div className="panel-heading"><div><span className="eyebrow">INVESTIGATION RESULT</span><h2>Findings</h2></div>{finding && <span className={`issue-pill ${issueTone}`}>{finding.issue_type.replaceAll("_", " ")}</span>}</div>
            {!finding ? <div className="empty-findings"><FileSearch size={22} /><p>Start with an invoice ID. The specialist agents will compare the invoice, PO, receipt, and applicable controls.</p></div> : <>
              <p className="finding-summary">{finding.summary}</p>
              <div className="facts-grid">
                <div><span>SUPPLIER</span><b>{result?.invoice?.supplier}</b></div>
                <div><span>INVOICE TOTAL</span><b>{result?.invoice?.currency} {result?.invoice?.total.toLocaleString(undefined, { minimumFractionDigits: 2 })}</b></div>
                <div><span>CONFIDENCE</span><b>{Math.round(finding.confidence * 100)}%</b></div>
                <div><span>RECOMMENDATION</span><b>{finding.recommended_action.replaceAll("_", " ")}</b></div>
              </div>
              <div className="evidence-list"><h3>Evidence trail</h3>{finding.evidence.map((item) => <div className="evidence-row" key={item.citation}><span>{item.source}</span><p>{item.claim}</p><code>{item.citation}</code></div>)}</div>
              {result?.final_response && <p className="final-response">{result.final_response}</p>}
            </>}
          </section>
          <ToolActivity tools={result?.tool_results ?? []} />
        </div>

        <aside className="side-column">
          <ApprovalPanel pending={Boolean(result?.pending_approval)} finding={finding} decision={result?.human_approval?.decision} loading={loading} onDecision={decide} />
          <SourcesPanel sources={result?.retrieved_documents ?? []} />
          <section className="panel record-panel"><div className="panel-heading"><div><span className="eyebrow">AUDIT CONTEXT</span><h2>Workflow record</h2></div></div>
            <dl><div><dt>Workflow</dt><dd>{result?.workflow_id ?? "Not started"}</dd></div><div><dt>Invoice</dt><dd>{result?.invoice?.invoice_id ?? (invoiceId || "—")}</dd></div><div><dt>Validation</dt><dd>{result?.validation_result?.status ?? "Pending"}</dd></div></dl>
          </section>
        </aside>
      </div>
      <footer className="footer"><span>LEDGERLINE AP OPERATIONS</span><span>Synthetic demo data · No payment rails connected</span></footer>
    </main>
  );
}