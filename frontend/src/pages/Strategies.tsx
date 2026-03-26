import { useState } from "react";
import { useApi } from "../hooks/useApi";
import BacktestRunner from "../components/backtest/BacktestRunner";
import BacktestHistory from "../components/backtest/BacktestHistory";

interface Strategy {
  name: string;
  symbol: string;
  type: string;
  has_position: boolean;
}

type Tab = "overview" | "backtest";
type BacktestSubView = "run" | "history";

function StrategiesOverview() {
  const { data: strategies, loading } = useApi<Strategy[]>(
    "/api/strategies",
    10000
  );

  if (loading)
    return <div className="text-gray-400">Loading strategies...</div>;

  return (
    <div>
      {!strategies || strategies.length === 0 ? (
        <div className="text-gray-500 bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
          No strategies loaded
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {strategies.map((s) => (
            <div
              key={s.name}
              className="bg-gray-900 border border-gray-800 rounded-lg p-4"
            >
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold">{s.name}</h3>
                <span
                  className={`px-2 py-0.5 rounded text-xs ${
                    s.has_position
                      ? "bg-blue-900 text-blue-300"
                      : "bg-gray-700 text-gray-300"
                  }`}
                >
                  {s.has_position ? "In Position" : "Watching"}
                </span>
              </div>
              <div className="text-sm text-gray-400 space-y-1">
                <div>
                  Symbol: <span className="text-gray-200 font-mono">{s.symbol}</span>
                </div>
                <div>
                  Type: <span className="text-gray-200">{s.type}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Strategies() {
  const [tab, setTab] = useState<Tab>("overview");
  const [backtestView, setBacktestView] = useState<BacktestSubView>("run");

  return (
    <div>
      {/* Tab navigation */}
      <div className="flex items-center gap-6 mb-6 border-b border-gray-800">
        <button
          onClick={() => setTab("overview")}
          className={`pb-2 text-sm font-medium border-b-2 ${
            tab === "overview"
              ? "border-green-400 text-white"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          Overview
        </button>
        <button
          onClick={() => setTab("backtest")}
          className={`pb-2 text-sm font-medium border-b-2 ${
            tab === "backtest"
              ? "border-green-400 text-white"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          Backtest
        </button>
      </div>

      {tab === "overview" && <StrategiesOverview />}

      {tab === "backtest" && (
        <div>
          {/* Sub-view toggle */}
          <div className="flex items-center gap-4 mb-4">
            <button
              onClick={() => setBacktestView("run")}
              className={`px-3 py-1 rounded text-sm ${
                backtestView === "run"
                  ? "bg-gray-700 text-white"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              Run
            </button>
            <button
              onClick={() => setBacktestView("history")}
              className={`px-3 py-1 rounded text-sm ${
                backtestView === "history"
                  ? "bg-gray-700 text-white"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              History
            </button>
          </div>

          {backtestView === "run" && <BacktestRunner />}
          {backtestView === "history" && <BacktestHistory />}
        </div>
      )}
    </div>
  );
}
