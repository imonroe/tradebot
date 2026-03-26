import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface RunDetail {
  id: number;
  strategy_name: string;
  start_date: string;
  end_date: string;
  starting_capital: string;
  ending_nav: string;
  total_return_pct: string;
  max_drawdown_pct: string;
  total_trades: number;
  win_rate: string;
  profit_factor: string;
  daily_snapshots: { date: string; nav: string }[];
}

const COLORS = ["#4ade80", "#60a5fa", "#f59e0b", "#f87171", "#a78bfa"];

export default function BacktestComparison({
  runs,
  onClose,
}: {
  runs: RunDetail[];
  onClose: () => void;
}) {
  // Merge equity curves: union of all dates, one NAV series per run
  const dateSet = new Set<string>();
  for (const run of runs) {
    for (const s of run.daily_snapshots) {
      dateSet.add(s.date);
    }
  }
  const dates = Array.from(dateSet).sort();

  const chartData = dates.map((d) => {
    const point: Record<string, string | number> = { date: d };
    for (const run of runs) {
      const snap = run.daily_snapshots.find((s) => s.date === d);
      if (snap) point[`run_${run.id}`] = parseFloat(snap.nav);
    }
    return point;
  });

  const metrics = ["total_return_pct", "max_drawdown_pct", "win_rate", "profit_factor", "total_trades"] as const;
  const metricLabels: Record<string, string> = {
    total_return_pct: "Return %",
    max_drawdown_pct: "Max DD %",
    win_rate: "Win Rate %",
    profit_factor: "Profit Factor",
    total_trades: "Trades",
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-200">
          Comparing {runs.length} Runs
        </h3>
        <button
          onClick={onClose}
          className="text-sm text-gray-400 hover:text-white"
        >
          Close Comparison
        </button>
      </div>

      {/* Metrics table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left py-2 pr-4 text-gray-400">Metric</th>
              {runs.map((r, i) => (
                <th
                  key={r.id}
                  className="text-right py-2 px-3"
                  style={{ color: COLORS[i % COLORS.length] }}
                >
                  Run #{r.id}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-gray-800/50">
              <td className="py-2 pr-4 text-gray-400">Strategy</td>
              {runs.map((r) => (
                <td key={r.id} className="py-2 px-3 text-right text-gray-300">
                  {r.strategy_name}
                </td>
              ))}
            </tr>
            <tr className="border-b border-gray-800/50">
              <td className="py-2 pr-4 text-gray-400">Period</td>
              {runs.map((r) => (
                <td key={r.id} className="py-2 px-3 text-right text-gray-300">
                  {r.start_date} — {r.end_date}
                </td>
              ))}
            </tr>
            {metrics.map((m) => (
              <tr key={m} className="border-b border-gray-800/50">
                <td className="py-2 pr-4 text-gray-400">{metricLabels[m]}</td>
                {runs.map((r) => (
                  <td key={r.id} className="py-2 px-3 text-right text-gray-300">
                    {String(r[m])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Overlaid equity curves */}
      {chartData.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-300 mb-3">
            Equity Curves
          </h4>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="date" stroke="#9ca3af" fontSize={12} />
              <YAxis
                stroke="#9ca3af"
                fontSize={12}
                tickFormatter={(v: number) => `$${v.toFixed(0)}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1f2937",
                  border: "1px solid #374151",
                  borderRadius: "0.5rem",
                  color: "#f3f4f6",
                }}
                formatter={(value: number) => [`$${value.toFixed(2)}`, ""]}
              />
              <Legend />
              {runs.map((r, i) => (
                <Line
                  key={r.id}
                  type="monotone"
                  dataKey={`run_${r.id}`}
                  stroke={COLORS[i % COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                  name={`#${r.id} ${r.strategy_name}`}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
