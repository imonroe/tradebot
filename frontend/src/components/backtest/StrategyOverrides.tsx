import { useState } from "react";

interface StrategyOverridesProps {
  config: Record<string, unknown>;
  overrides: Record<string, number | string>;
  onChange: (overrides: Record<string, number | string>) => void;
}

/** Flattens a nested config object into dot-notation paths with leaf values. */
function flattenConfig(
  obj: Record<string, unknown>,
  prefix = ""
): { path: string; value: unknown }[] {
  const entries: { path: string; value: unknown }[] = [];
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (
      value !== null &&
      typeof value === "object" &&
      !Array.isArray(value)
    ) {
      entries.push(
        ...flattenConfig(value as Record<string, unknown>, path)
      );
    } else {
      entries.push({ path, value });
    }
  }
  return entries;
}

/** Sections we allow overriding (skip strategy metadata and market). */
const OVERRIDE_SECTIONS = ["entry", "exit", "position_sizing", "risk"];

export default function StrategyOverrides({
  config,
  overrides,
  onChange,
}: StrategyOverridesProps) {
  const [expanded, setExpanded] = useState(false);

  const fields = flattenConfig(config).filter((f) =>
    OVERRIDE_SECTIONS.some((s) => f.path.startsWith(s))
  );

  const handleChange = (path: string, raw: string) => {
    const next = { ...overrides };
    if (raw === "") {
      delete next[path];
    } else {
      const num = Number(raw);
      next[path] = isNaN(num) ? raw : num;
    }
    onChange(next);
  };

  return (
    <div className="border border-gray-700 rounded-lg">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 text-sm text-gray-300 hover:text-white"
      >
        <span>Strategy Overrides</span>
        <span>{expanded ? "▲" : "▼"}</span>
      </button>
      {expanded && (
        <div className="px-3 pb-3 space-y-2">
          {fields.map(({ path, value }) => (
            <div key={path} className="flex items-center gap-2">
              <label className="text-xs text-gray-400 w-56 truncate" title={path}>
                {path}
              </label>
              <input
                type="text"
                placeholder={String(value)}
                value={overrides[path] ?? ""}
                onChange={(e) => handleChange(path, e.target.value)}
                className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white placeholder-gray-600"
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
