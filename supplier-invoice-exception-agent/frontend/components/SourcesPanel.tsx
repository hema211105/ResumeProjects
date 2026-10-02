import { BookOpen, ExternalLink } from "lucide-react";

type Source = { title: string; section: string; citation: string; excerpt: string; category: string };

export function SourcesPanel({ sources }: { sources: Source[] }) {
  return (
    <section className="panel sources-panel">
      <div className="panel-heading">
        <div><span className="eyebrow">KNOWLEDGE BASE</span><h2>Evidence sources</h2></div>
        <BookOpen size={18} aria-hidden="true" />
      </div>
      {sources.length === 0 ? <p className="empty-state">Policy passages will appear with the investigation.</p> : (
        <div className="source-list">
          {sources.map((source) => (
            <article className="source-item" key={source.citation}>
              <div className="source-topline"><span className="source-category">{source.category}</span><span>{source.citation}</span></div>
              <h3>{source.title}<ExternalLink size={13} aria-hidden="true" /></h3>
              <p className="source-section">{source.section}</p>
              <p className="source-excerpt">“{source.excerpt}”</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}