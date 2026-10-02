const stages = [
  "Supervisor",
  "Invoice Extraction",
  "PO Matching",
  "Goods Receipt Validation",
  "Tax Validation",
  "Policy RAG",
  "Exception Investigation",
  "Human Approval",
  "Validation",
  "Response",
];

export function WorkflowSteps({ current, pending }: { current?: string; pending: boolean }) {
  const activeIndex = current === "Approved Action" ? stages.indexOf("Validation") : stages.indexOf(current ?? "");
  return (
    <ol className="workflow-steps" aria-label="Workflow progress">
      {stages.map((stage, index) => {
        const done = activeIndex > index || (current === "Response" && index === stages.length - 1);
        const active = stage === current || (pending && stage === "Human Approval");
        return (
          <li className={`workflow-step ${done ? "is-done" : ""} ${active ? "is-active" : ""}`} key={stage}>
            <span className="step-marker">{done ? "✓" : String(index + 1).padStart(2, "0")}</span>
            <span>{stage}</span>
          </li>
        );
      })}
    </ol>
  );
}