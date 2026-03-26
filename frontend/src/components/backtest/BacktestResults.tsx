import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface DailySnapshot {
  date: string;
  nav: string;
  daily_pnl: string;
  drawdown: string;
}

interface Trade {
  date: string;
  strategy: string;
  symbol: string;
  spread_type: string;
  entry_price: string;
  pnl: number;
}

interface BacktestResultData {
  strategy_name: string;
  start_date: string;
  end_date: string;
  starting_capital: string;
  ending_nav: string;
  total_return_pct: string;
  max_drawdown_pct: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: string;
  avg_win: string;
  avg_loss: string;
  profit_factor: string;
  daily_snapshots: DailySnapshot[];
  trades: Trade[];
}

function MetricCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-3">
      <div className="text-xs text-gray-400">{label}</div>
      <div className={`text-lg font-semibold ${color || "text-white"}`}>{value}</div>
    </div>
  );
}

export default function BacktestResults({ result }: { result: BacktestResultData }) {
  const returnPct = parseFloat(result.total_return_pct);
  const returnColor = returnPct >= 0 ? "text-green-400" : "text-red-400";

  const chartData = result.daily_snapshots.map((s) => ({
    date: new Date(s.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    nav: parseFloat(s.nav),
    drawdown: parseFloat(s.drawdown),
  }));

  return (
    <div className="space-y-6">
      {/* Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <MetricCard
          label="Total Return"
          value={`${returnPct >= 0 ? "+" : ""}${result.total_return_pct}%`}
          color={returnColor}
        />
        <MetricCard label="Max Drawdown" value={`-${result.max_drawdown_pct}%`} color="text-red-400" />
        <MetricCard label="Win Rate" value={`${result.win_rate}%`} />
        <MetricCard label="Profit Factor" value={result.profit_factor} />
        <MetricCard label="Total Trades" value={String(result.total_trades)} />
      </div>

      {/* Additional stats row */}
      <div className="grid grid-cols-4 gap-3">
        <MetricCard label="Starting Capital" value={`$${parseFloat(result.starting_capital).toFixed(2)}`} />
        <MetricCard label="Ending NAV" value={`$${parseFloat(result.ending_nav).toFixed(2)}`} />
        <MetricCard label="Avg Win" value={`$${result.avg_win}`} color="text-green-400" />
        <MetricCard label="Avg Loss" value={`$${result.avg_loss}`} color="text-red-400" />
      </div>

      {/* Equity Curve */}
      {chartData.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-300 mb-3">Equity Curve</h4>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="date" stroke="#9ca3af" fontSize={12} />
              <YAxis
                yAxisId="nav"
                stroke="#4ade80"
                fontSize={12}
                tickFormatter={(v: number) => `$${v.toFixed(0)}`}
              />
              <YAxis
                yAxisId="dd"
                orientation="right"
                stroke="#f87171"
                fontSize={12}
                tickFormatter={(v: number) => `${v.toFixed(1)}%`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1f2937",
                  border: "1px solid #374151",
                  borderRadius: "0.5rem",
                  color: "#f3f4f6",
                }}
                formatter={(value: number, name: string) => {
                  if (name === "NAV") return [`$${value.toFixed(2)}`, name];
                  return [`${value.toFixed(2)}%`, name];
                }}
              />
              <Line yAxisId="nav" type="monotone" dataKey="nav" stroke="#4ade80" strokeWidth={2} dot={false} name="NAV" />
              <Line yAxisId="dd" type="monotone" dataKey="drawdown" stroke="#f87171" strokeWidth={1} dot={false} name="Drawdown" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Trade Log */}
      {result.trades.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-300 mb-3">Trade Log</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-gray-800">
                  <th className="text-left py-2 pr-4">Date</th>
                  <th className="text-left py-2 pr-4">Strategy</th>
                  <th className="text-left py-2 pr-4">Symbol</th>
                  <th className="text-left py-2 pr-4">Type</th>
                  <th className="text-right py-2 pr-4">Entry</th>
                  <th className="text-right py-2">P&amp;L</th>
                </tr>
              </thead>
              <tbody>
                {result.trades.map((t, i) => (
                  <tr key={i} className="border-b border-gray-800/50">
                    <td className="py-2 pr-4 text-gray-300">{t.date}</td>
                    <td className="py-2 pr-4 text-gray-300">{t.strategy}</td>
                    <td className="py-2 pr-4 font-mono text-gray-300">{t.symbol}</td>
                    <td className="py-2 pr-4 text-gray-300">{t.spread_type}</td>
                    <td className="py-2 pr-4 text-right text-gray-300">${t.entry_price}</td>
                    <td className={`py-2 text-right font-medium ${t.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                      {t.pnl >= 0 ? "+" : ""}${t.pnl.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
