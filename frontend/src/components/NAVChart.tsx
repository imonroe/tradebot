import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useApi } from "../hooks/useApi";

interface NavSnapshot {
  date: string;
  nav: string;
  realized_pnl: string;
  unrealized_pnl: string;
  drawdown: string;
  day_trades: number;
}

interface ChartPoint {
  date: string;
  nav: number;
  drawdown: number;
}

export function NAVChart() {
  const { data: history } = useApi<NavSnapshot[]>(
    "/api/portfolio/nav-history?days=30",
    60000
  );

  if (!history || history.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        No NAV history yet. Data will appear after the first trading day.
      </div>
    );
  }

  const chartData: ChartPoint[] = history.map((item) => ({
    date: new Date(item.date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
    nav: parseFloat(item.nav),
    drawdown: parseFloat(item.drawdown),
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
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
        <Line
          yAxisId="nav"
          type="monotone"
          dataKey="nav"
          stroke="#4ade80"
          strokeWidth={2}
          dot={false}
          name="NAV"
        />
        <Line
          yAxisId="dd"
          type="monotone"
          dataKey="drawdown"
          stroke="#f87171"
          strokeWidth={1}
          dot={false}
          name="Drawdown"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
