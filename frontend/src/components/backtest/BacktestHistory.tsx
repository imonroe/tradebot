import { useState } from "react";
import { useApi } from "../../hooks/useApi";
import BacktestResults from "./BacktestResults";
import BacktestComparison from "./BacktestComparison";

interface RunSummary {
  id: number;
  strategy_name: string;
  start_date: string;
  end_date: string;
  starting_capital: string;
  total_return_pct: string;
  max_drawdown_pct: string;
  total_trades: number;
  win_rate: string;
  profit_factor: string;
  created_at: string;
}

interface RunDetail extends RunSummary {
  ending_nav: string;
  interval_minutes: number;
  winning_trades: number;
  losing_trades: number;
  avg_win: string;
  avg_loss: string;
  daily_snapshots: { date: string; nav: string; daily_pnl: string; drawdown: string }[];
  trades: { date: string; strategy: string; symbol: string; spread_type: string; entry_price: string; pnl: number }[];
}

export default function BacktestHistory() {
  const { data: runs, loading } = useApi<RunSummary[]>("/api/backtest/runs", 10000);

  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [expandedData, setExpandedData] = useState<RunDetail | null>(null);
  const [comparing, setComparing] = useState(false);
  const [comparisonRuns, setComparisonRuns] = useState<RunDetail[]>([]);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleExpand = async (id: number) => {
    if (expandedId === id) {
      setExpandedId(null);
      setExpandedData(null);
      return;
    }
    setExpandedId(id);
    setLoadingDetail(true);
    try {
      const res = await fetch(`/api/backtest/runs/${id}`);
      if (!res.ok) {
        throw new Error(`Failed to load run details (status ${res.status})`);
      }
      const data: RunDetail = await res.json();
      setExpandedData(data);
    } catch (error) {
      console.error("Error loading run details:", error);
      setExpandedData(null);
      setExpandedId(null);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleDelete = async (id: number) => {
    await fetch(`/api/backtest/runs/${id}`, { method: "DELETE" });
    if (expandedId === id) {
      setExpandedId(null);
      setExpandedData(null);
    }
    setSelected((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  const handleCompare = async () => {
    setLoadingDetail(true);
    try {
      const selectedIds = Array.from(selected);
      const results = await Promise.allSettled(
        selectedIds.map(async (id) => {
          const res = await fetch(`/api/backtest/runs/${id}`);
          if (!res.ok) {
            throw new Error(`Failed to load run ${id}: ${res.status} ${res.statusText}`);
          }
          return (await res.json()) as RunDetail;
        })
      );

      const successfulDetails: RunDetail[] = [];
      const failedIds: number[] = [];

      results.forEach((result, index) => {
        if (result.status === "fulfilled") {
          successfulDetails.push(result.value);
        } else {
          failedIds.push(selectedIds[index]);
        }
      });

      if (failedIds.length > 0) {
        console.error(`Failed to load runs for comparison: ${failedIds.join(", ")}`);
      }

      if (successfulDetails.length > 0) {
        setComparisonRuns(successfulDetails);
        setComparing(true);
      }
    } finally {
      setLoadingDetail(false);
    }
  };

  if (comparing && comparisonRuns.length > 0) {
    return (
      <BacktestComparison
        runs={comparisonRuns}
        onClose={() => {
          setComparing(false);
          setComparisonRuns([]);
        }}
      />
    );
  }

  if (loading) return <div className="text-gray-400">Loading history...</div>;

  if (!runs || runs.length === 0) {
    return (
      <div className="text-gray-500 bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
        No saved backtest runs yet. Run a backtest with "Save to history" enabled.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-400">
          {selected.size} selected
        </span>
        <button
          onClick={handleCompare}
          disabled={selected.size < 2 || loadingDetail}
          className={`px-3 py-1 rounded text-sm ${
            selected.size >= 2
              ? "bg-blue-600 hover:bg-blue-500 text-white"
              : "bg-gray-700 text-gray-500 cursor-not-allowed"
          }`}
        >
          Compare Selected
        </button>
      </div>

      {/* Runs table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-400 border-b border-gray-800">
              <th className="py-2 pr-2 w-8"></th>
              <th className="text-left py-2 pr-4">Strategy</th>
              <th className="text-left py-2 pr-4">Period</th>
              <th className="text-right py-2 pr-4">Return</th>
              <th className="text-right py-2 pr-4">Max DD</th>
              <th className="text-right py-2 pr-4">Win Rate</th>
              <th className="text-right py-2 pr-4">PF</th>
              <th className="text-right py-2 pr-4">Trades</th>
              <th className="text-right py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => {
              const ret = parseFloat(r.total_return_pct);
              return (
                <tr
                  key={r.id}
                  className={`border-b border-gray-800/50 cursor-pointer hover:bg-gray-800/50 ${
                    expandedId === r.id ? "bg-gray-800/30" : ""
                  }`}
                >
                  <td className="py-2 pr-2" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selected.has(r.id)}
                      onChange={() => toggleSelect(r.id)}
                      className="rounded"
                    />
                  </td>
                  <td className="py-2 pr-4 text-gray-300" onClick={() => handleExpand(r.id)}>
                    {r.strategy_name}
                  </td>
                  <td className="py-2 pr-4 text-gray-400" onClick={() => handleExpand(r.id)}>
                    {r.start_date} — {r.end_date}
                  </td>
                  <td
                    className={`py-2 pr-4 text-right ${ret >= 0 ? "text-green-400" : "text-red-400"}`}
                    onClick={() => handleExpand(r.id)}
                  >
                    {ret >= 0 ? "+" : ""}{r.total_return_pct}%
                  </td>
                  <td className="py-2 pr-4 text-right text-red-400" onClick={() => handleExpand(r.id)}>
                    -{r.max_drawdown_pct}%
                  </td>
                  <td className="py-2 pr-4 text-right text-gray-300" onClick={() => handleExpand(r.id)}>
                    {r.win_rate}%
                  </td>
                  <td className="py-2 pr-4 text-right text-gray-300" onClick={() => handleExpand(r.id)}>
                    {r.profit_factor}
                  </td>
                  <td className="py-2 pr-4 text-right text-gray-300" onClick={() => handleExpand(r.id)}>
                    {r.total_trades}
                  </td>
                  <td className="py-2 text-right" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => handleDelete(r.id)}
                      className="text-gray-500 hover:text-red-400 text-xs"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Expanded detail */}
      {expandedId && expandedData && (
        <div className="border border-gray-700 rounded-lg p-4">
          <BacktestResults result={expandedData} />
        </div>
      )}
      {expandedId && loadingDetail && !expandedData && (
        <div className="text-gray-400 text-center py-4">Loading details...</div>
      )}
    </div>
  );
}
