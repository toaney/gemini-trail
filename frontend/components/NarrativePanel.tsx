"use client";

import { useEffect, useRef } from "react";

interface Props {
  lines: string[];
  streaming: boolean;
}

export default function NarrativePanel({ lines, streaming }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  return (
    <div className="flex-1 overflow-y-auto font-mono text-sand-100 text-sm leading-relaxed p-4 space-y-3">
      {lines.map((line, i) => {
        if (line.startsWith("> ")) {
          return (
            <div key={i} className="text-zinc-500 text-xs">
              {line}
            </div>
          );
        }
        if (!line) return null;
        return (
          <p key={i} className="text-sand-100 whitespace-pre-wrap">
            {line}
            {i === lines.length - 1 && streaming && (
              <span className="animate-pulse text-rust-400">▌</span>
            )}
          </p>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
