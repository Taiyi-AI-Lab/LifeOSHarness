import { Copy } from "lucide-react";

type JsonBlockProps = {
  title?: string;
  value: unknown;
};

export function JsonBlock({ title, value }: JsonBlockProps) {
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);

  async function copy() {
    await navigator.clipboard.writeText(text);
  }

  return (
    <section className="code-panel">
      <div className="code-panel__header">
        <span>{title || "Preview"}</span>
        <button className="icon-button" type="button" onClick={copy} aria-label="Copy preview">
          <Copy size={16} aria-hidden="true" />
        </button>
      </div>
      <pre>{text || "No data yet."}</pre>
    </section>
  );
}
