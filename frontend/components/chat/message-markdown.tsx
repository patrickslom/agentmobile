"use client";

import { useCallback, useMemo, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { Highlight, Prism } from "prism-react-renderer";
import type { Language } from "prism-react-renderer";

const INLINE_CODE_CLASSNAME = "rounded border border-border bg-background px-1 py-0.5 font-mono text-[0.85em]";

type MessageMarkdownProps = {
  content: string;
};

function parseLanguage(className?: string): string {
  const match = /language-([\w-]+)/.exec(className ?? "");
  return (match?.[1] ?? "").toLowerCase();
}

function normalizeLanguage(language: string): Language | null {
  if (!language) {
    return null;
  }

  if (language === "js") {
    return "jsx";
  }

  if (language === "ts") {
    return "typescript";
  }

  if (language === "sh" || language === "shell") {
    return "bash";
  }

  if (language in Prism.languages) {
    return language as Language;
  }

  return null;
}

function CopyCodeButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);

  const onCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      setCopied(false);
    }
  }, [value]);

  return (
    <button
      type="button"
      onClick={() => void onCopy()}
      className="rounded-md border border-border bg-background px-2 py-1 text-xs font-medium transition hover:bg-muted"
      aria-label="Copy code block"
    >
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

export default function MessageMarkdown({ content }: MessageMarkdownProps) {
  const components = useMemo<Components>(
    () => ({
      p({ children }) {
        return <p className="mb-3 last:mb-0">{children}</p>;
      },
      ul({ children }) {
        return <ul className="mb-3 list-disc space-y-1 pl-6">{children}</ul>;
      },
      ol({ children }) {
        return <ol className="mb-3 list-decimal space-y-1 pl-6">{children}</ol>;
      },
      blockquote({ children }) {
        return <blockquote className="mb-3 border-l-2 border-border pl-3 text-muted-foreground">{children}</blockquote>;
      },
      code({ className, children, ...props }) {
        const rawCode = String(children ?? "");
        const normalizedCode = rawCode.replace(/\n$/, "");
        const language = normalizeLanguage(parseLanguage(className));

        if (!className) {
          return (
            <code className={INLINE_CODE_CLASSNAME} {...props}>
              {children}
            </code>
          );
        }

        if (!language) {
          return (
            <div className="my-3 overflow-hidden rounded-xl border border-border bg-muted/60">
              <div className="flex items-center justify-between border-b border-border px-3 py-2">
                <span className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
                  {parseLanguage(className) || "code"}
                </span>
                <CopyCodeButton value={normalizedCode} />
              </div>
              <pre className="m-0 max-h-[28rem] overflow-x-auto rounded-none border-0 bg-transparent px-4 py-3 text-sm">
                <code>{normalizedCode}</code>
              </pre>
            </div>
          );
        }

        return (
          <div className="my-3 overflow-hidden rounded-xl border border-border bg-muted/60">
            <div className="flex items-center justify-between border-b border-border px-3 py-2">
              <span className="text-xs uppercase tracking-[0.12em] text-muted-foreground">{language}</span>
              <CopyCodeButton value={normalizedCode} />
            </div>
            <Highlight
              code={normalizedCode}
              language={language}
              theme={undefined}
            >
              {({ className: highlightClassName, style, tokens, getLineProps, getTokenProps }) => (
                <pre
                  className={`${highlightClassName} m-0 max-h-[28rem] overflow-x-auto rounded-none border-0 bg-transparent px-4 py-3 text-sm`}
                  style={{ ...style, backgroundColor: "transparent" }}
                >
                  {tokens.map((line, index) => (
                    <div key={index} {...getLineProps({ line })}>
                      {line.map((token, tokenIndex) => (
                        <span key={tokenIndex} {...getTokenProps({ token })} />
                      ))}
                    </div>
                  ))}
                </pre>
              )}
            </Highlight>
          </div>
        );
      },
    }),
    [],
  );

  return <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>{content}</ReactMarkdown>;
}
