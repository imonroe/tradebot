import { useWebSocket } from "../hooks/useWebSocket";
import { useApi } from "../hooks/useApi";
import { NAVChart } from "../components/NAVChart";
import { KillSwitch } from "../components/KillSwitch";

interface Position {
  broker_order_id: string;
  strategy: string;
  symbol: string;
  spread_type: string;
  fill_price: string;
  timestamp: string;
}

interface PortfolioData {
  nav: string;
  daily_pnl: string;
  drawdown_pct: string;
  open_positions: Position[];
  pdt_day_trades_used: number;
  mode: string;
}

function StatCard({
  label,
  value,
  color = "text-white",
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <div className="text-sm text-gray-400">{label}</div>
      <div className={`text-2xl font-bold mt-1 ${color}`}>{value}</div>
    </div>
  );
}

interface AnalyticsData {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: string;
  avg_win: string;
  avg_loss: string;
  largest_win: string;
  largest_loss: string;
  profit_factor: string;
  total_pnl: string;
  avg_trade_pnl: string;
  current_streak: number;
  streak_type: string;
  sharpe_ratio: string;
  max_drawdown_pct: string;
}

interface KillSwitchData {
  active: boolean;
  reason: string | null;
}

export default function Dashboard() {
  const { data: wsData, connected } = useWebSocket();
  const { data: portfolio, loading } = useApi<PortfolioData>(
    "/api/portfolio",
    10000
  );
  const { data: killSwitchData } = useApi<KillSwitchData>(
    "/api/kill-switch",
    10000
  );
  const { data: analytics } = useApi<AnalyticsData>(
    "/api/portfolio/analytics",
    30000
  );

  // Use WebSocket data if available, fall back to REST
  const nav = wsData?.nav ?? portfolio?.nav ?? "—";
  const dailyPnl = wsData?.daily_pnl ?? portfolio?.daily_pnl ?? "0";
  const drawdown = wsData?.drawdown_pct ?? portfolio?.drawdown_pct ?? "0";
  const pdtUsed =
    wsData?.pdt_day_trades_used ?? portfolio?.pdt_day_trades_used ?? 0;
  const mode = wsData?.mode ?? portfolio?.mode ?? "—";
  const killSwitchActive = killSwitchData?.active ?? wsData?.kill_switch_active ?? false;
  const positions = portfolio?.open_positions ?? [];

  const pnlNum = parseFloat(dailyPnl);
  const pnlColor =
    pnlNum > 0 ? "text-green-400" : pnlNum < 0 ? "text-red-400" : "text-white";
  const pnlDisplay = pnlNum >= 0 ? `+$${dailyPnl}` : `-$${Math.abs(pnlNum)}`;

  if (loading && !wsData) {
    return <div className="text-gray-400">Loading dashboard...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Status bar */}
      <div className="flex items-center gap-4">
        <span
          className={`px-2 py-1 rounded text-xs font-bold ${
            mode === "paper"
              ? "bg-yellow-900 text-yellow-300"
              : "bg-red-900 text-red-300"
          }`}
        >
          {mode?.toUpperCase()} MODE
        </span>
        <span
          className={`flex items-center gap-1 text-xs ${
            connected ? "text-green-400" : "text-red-400"
          }`}
        >
          <span
            className={`w-2 h-2 rounded-full ${
              connected ? "bg-green-400" : "bg-red-400"
            }`}
          />
          {connected ? "Live" : "Disconnected"}
        </span>
        <KillSwitch active={killSwitchActive} />
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="NAV" value={`$${nav}`} />
        <StatCard label="Daily P&L" value={pnlDisplay} color={pnlColor} />
        <StatCard
          label="Drawdown"
          value={`${parseFloat(drawdown).toFixed(2)}%`}
          color={parseFloat(drawdown) > 5 ? "text-red-400" : "text-white"}
        />
        <StatCard label="PDT Used" value={`${pdtUsed}/3`} />
      </div>

      {/* NAV History Chart */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
        <h2 className="text-lg font-semibold text-gray-100 mb-4">
          NAV History (30 Days)
        </h2>
        <NAVChart />
      </div>

      {/* Performance Analytics */}
      {analytics && analytics.total_trades > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">Performance Analytics</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              label="Win Rate"
              value={`${analytics.win_rate}%`}
              color={parseFloat(analytics.win_rate) >= 50 ? "text-green-400" : "text-red-400"}
            />
            <StatCard
              label="Profit Factor"
              value={analytics.profit_factor}
              color={parseFloat(analytics.profit_factor) >= 1 ? "text-green-400" : "text-red-400"}
            />
            <StatCard
              label="Sharpe Ratio"
              value={analytics.sharpe_ratio}
              color={parseFloat(analytics.sharpe_ratio) >= 1 ? "text-green-400" : "text-white"}
            />
            <StatCard
              label="Total P&L"
              value={`$${analytics.total_pnl}`}
              color={parseFloat(analytics.total_pnl) >= 0 ? "text-green-400" : "text-red-400"}
            />
            <StatCard label="Total Trades" value={`${analytics.total_trades} (${analytics.winning_trades}W / ${analytics.losing_trades}L)`} />
            <StatCard label="Avg Win" value={`$${analytics.avg_win}`} color="text-green-400" />
            <StatCard label="Avg Loss" value={`$${analytics.avg_loss}`} color="text-red-400" />
            <StatCard
              label="Streak"
              value={`${analytics.current_streak} ${analytics.streak_type}`}
              color={analytics.streak_type === "win" ? "text-green-400" : analytics.streak_type === "loss" ? "text-red-400" : "text-white"}
            />
          </div>
        </div>
      )}

      {/* Open Positions */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Open Positions</h2>
        {positions.length === 0 ? (
          <div className="text-gray-500 bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
            No open positions
          </div>
        ) : (
          <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-800">
                <tr>
                  <th className="px-4 py-2 text-left text-gray-400">Symbol</th>
                  <th className="px-4 py-2 text-left text-gray-400">Strategy</th>
                  <th className="px-4 py-2 text-left text-gray-400">Type</th>
                  <th className="px-4 py-2 text-right text-gray-400">
                    Fill Price
                  </th>
                  <th className="px-4 py-2 text-right text-gray-400">Time</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((p) => (
                  <tr key={p.broker_order_id} className="border-t border-gray-800">
                    <td className="px-4 py-2 font-mono">{p.symbol}</td>
                    <td className="px-4 py-2">{p.strategy}</td>
                    <td className="px-4 py-2">{p.spread_type}</td>
                    <td className="px-4 py-2 text-right">${p.fill_price}</td>
                    <td className="px-4 py-2 text-right text-gray-400">
                      {new Date(p.timestamp).toLocaleTimeString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
