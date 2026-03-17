import { useApi } from "../hooks/useApi";

interface Trade {
  id: number;
  strategy: string;
  symbol: string;
  spread_type: string;
  entry_price: string;
  exit_price: string | null;
  pnl: string | null;
  status: string;
  entry_time: string | null;
  exit_time: string | null;
}

export default function Trades() {
  const { data: trades, loading } = useApi<Trade[]>("/api/trades", 15000);

  if (loading) return <div className="text-gray-400">Loading trades...</div>;

  return (
    <div>
      <h2 className="text-lg font-semibold mb-3">Trade History</h2>
      {!trades || trades.length === 0 ? (
        <div className="text-gray-500 bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
          No trades yet
        </div>
      ) : (
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-800">
              <tr>
                <th className="px-4 py-2 text-left text-gray-400">ID</th>
                <th className="px-4 py-2 text-left text-gray-400">Symbol</th>
                <th className="px-4 py-2 text-left text-gray-400">Strategy</th>
                <th className="px-4 py-2 text-left text-gray-400">Type</th>
                <th className="px-4 py-2 text-right text-gray-400">Entry</th>
                <th className="px-4 py-2 text-right text-gray-400">Exit</th>
                <th className="px-4 py-2 text-right text-gray-400">P&L</th>
                <th className="px-4 py-2 text-left text-gray-400">Status</th>
                <th className="px-4 py-2 text-right text-gray-400">Time</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((t) => {
                const pnl = t.pnl ? parseFloat(t.pnl) : null;
                return (
                  <tr key={t.id} className="border-t border-gray-800">
                    <td className="px-4 py-2 text-gray-500">#{t.id}</td>
                    <td className="px-4 py-2 font-mono">{t.symbol}</td>
                    <td className="px-4 py-2">{t.strategy}</td>
                    <td className="px-4 py-2">{t.spread_type}</td>
                    <td className="px-4 py-2 text-right">${t.entry_price}</td>
                    <td className="px-4 py-2 text-right">
                      {t.exit_price ? `$${t.exit_price}` : "—"}
                    </td>
                    <td
                      className={`px-4 py-2 text-right ${
                        pnl !== null && pnl > 0
                          ? "text-green-400"
                          : pnl !== null && pnl < 0
                            ? "text-red-400"
                            : ""
                      }`}
                    >
                      {pnl !== null ? `$${t.pnl}` : "—"}
                    </td>
                    <td className="px-4 py-2">
                      <span
                        className={`px-2 py-0.5 rounded text-xs ${
                          t.status === "open"
                            ? "bg-blue-900 text-blue-300"
                            : t.status === "closed"
                              ? "bg-gray-700 text-gray-300"
                              : "bg-yellow-900 text-yellow-300"
                        }`}
                      >
                        {t.status}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right text-gray-400 text-xs">
                      {t.entry_time
                        ? new Date(t.entry_time).toLocaleString()
                        : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
