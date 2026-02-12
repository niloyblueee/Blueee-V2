import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import mermaid from "mermaid";

function MermaidBlock({ code }) {
  const [svg, setSvg] = useState("");
  const id = useMemo(() => `mermaid-${Math.random().toString(36).slice(2)}`, []);

  useEffect(() => {
    let isMounted = true;
    mermaid.initialize({ startOnLoad: false, theme: "dark" });
    mermaid
      .render(id, code)
      .then((result) => {
        if (isMounted) {
          setSvg(result.svg);
        }
      })
      .catch(() => {
        if (isMounted) {
          setSvg("<pre>Mermaid render failed</pre>");
        }
      });

    return () => {
      isMounted = false;
    };
  }, [code, id]);

  return (
    <div
      className="my-4 overflow-auto rounded-xl border border-circuit/20 bg-obsidian/80 p-4 text-sm"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}

export default function ResearchCanvas({ content }) {
  if (!content) {
    return (
      <div className="glass-panel h-full rounded-3xl p-6">
        <p className="text-sm text-slate-400">
          Drop a complex query or a trip plan to populate the canvas.
        </p>
      </div>
    );
  }

  return (
    <div className="glass-panel h-full rounded-3xl p-6">
      <h3 className="text-lg font-semibold text-white">Research Canvas</h3>
      <div className="mt-4 prose prose-invert max-w-none text-sm">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            code({ inline, className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || "");
              const lang = match?.[1];
              if (!inline && lang === "mermaid") {
                return <MermaidBlock code={String(children)} />;
              }
              return (
                <code
                  className={`${className || ""} rounded bg-black/40 px-2 py-1 text-circuit`}
                  {...props}
                >
                  {children}
                </code>
              );
            }
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
}
