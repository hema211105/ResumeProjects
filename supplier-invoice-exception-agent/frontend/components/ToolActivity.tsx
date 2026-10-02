import { Check, CircleX, Wrench } from "lucide-react";

export function ToolActivity({ tools }: { tools: { tool: string; ok: boolean; error?: string }[] }) {
  return (
    <section className="panel tool-panel">
      <div className="panel-heading"><div><span className="eyebrow">EXECUTION TRACE</span><h2>Tool activity</h2></div><Wrench size={17} /></div>
      {tools.length === 0 ? <p className="empty-state">No tools have run yet.</p> : <ul className="tool-list">
        {tools.map((tool, index) => <li key={`${tool.tool}-${index}`}><span className={`tool-result ${tool.ok ? "ok" : "failed"}`}>{tool.ok ? <Check size={13} /> : <CircleX size={13} />}</span><span>{tool.tool.replaceAll("_", " ")}</span><b>{tool.ok ? "success" : tool.error ?? "failed"}</b></li>)}
      </ul>}
    </section>
  );
}