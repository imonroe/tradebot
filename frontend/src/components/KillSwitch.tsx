import { useState, useCallback, useEffect } from "react";

interface KillSwitchProps {
  active: boolean;
}

export function KillSwitch({ active }: KillSwitchProps) {
  const [activeState, setActiveState] = useState(active);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setActiveState(active);
  }, [active]);

  const toggle = useCallback(async () => {
    setLoading(true);
    try {
      const endpoint = activeState
        ? "/api/kill-switch/deactivate"
        : "/api/kill-switch/activate";
      const res = await fetch(
        endpoint,
        activeState
          ? { method: "POST" }
          : {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ reason: "Manual toggle" }),
            }
      );
      if (res.ok) {
        const data = await res.json();
        setActiveState(data.active);
      }
    } finally {
      setLoading(false);
    }
  }, [activeState]);

  return (
    <button
      onClick={toggle}
      disabled={loading}
      aria-pressed={activeState}
      aria-label="Kill switch"
      className={`px-3 py-1 rounded text-xs font-bold transition-colors ${
        activeState
          ? "bg-red-700 text-red-100 hover:bg-red-600"
          : "bg-gray-700 text-gray-300 hover:bg-gray-600"
      } ${loading ? "opacity-50 cursor-not-allowed" : ""}`}
    >
      {activeState ? "KILL SWITCH ON" : "KILL SWITCH OFF"}
    </button>
  );
}
