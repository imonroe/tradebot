import { useState, useCallback } from "react";

interface KillSwitchProps {
  active: boolean;
}

export function KillSwitch({ active: initialActive }: KillSwitchProps) {
  const [active, setActive] = useState(initialActive);
  const [loading, setLoading] = useState(false);

  const toggle = useCallback(async () => {
    setLoading(true);
    try {
      const endpoint = active
        ? "/api/kill-switch/deactivate"
        : "/api/kill-switch/activate";
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: active ? undefined : JSON.stringify({ reason: "Manual toggle" }),
      });
      if (res.ok) {
        const data = await res.json();
        setActive(data.active);
      }
    } finally {
      setLoading(false);
    }
  }, [active]);

  return (
    <button
      onClick={toggle}
      disabled={loading}
      className={`px-3 py-1 rounded text-xs font-bold transition-colors ${
        active
          ? "bg-red-700 text-red-100 hover:bg-red-600"
          : "bg-gray-700 text-gray-300 hover:bg-gray-600"
      } ${loading ? "opacity-50 cursor-not-allowed" : ""}`}
    >
      {active ? "KILL SWITCH ON" : "KILL SWITCH OFF"}
    </button>
  );
}
