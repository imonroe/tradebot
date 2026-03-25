import { useState } from "react";
import {
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ErrorBar,
} from "recharts";
import { useApi } from "../hooks/useApi";

interface PriceBar {
  timestamp: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: number;
}

interface CandlePoint {
  time: string;
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  // For bar chart: body bottom and body height
  bodyBottom: number;
  bodyHeight: number;
  // For error bars: wick above and below the body
  wickUp: number;
  wickDown: number;
  isUp: boolean;
}

const INTERVALS = ["1m", "5m", "15m", "1h"] as const;
const HOURS_OPTIONS = [
  { label: "2h", value: 2 },
  { label: "4h", value: 4 },
  { label: "8h", value: 8 },
  { label: "1D", value: 24 },
] as const;

export function CandlestickChart() {
  const [interval, setInterval] = useState<string>("5m");
  const [hours, setHours] = useState<number>(8);

  const { data: bars } = useApi<PriceBar[]>(
    `/api/price-history?interval=${interval}&hours=${hours}`,
    60000
  );

  if (!bars || bars.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        No price data yet. Bars will appear once the bot starts polling.
      </div>
    );
  }

  const chartData: CandlePoint[] = bars.map((b) => {
    const o = parseFloat(b.open);
    const h = parseFloat(b.high);
    const l = parseFloat(b.low);
    const c = parseFloat(b.close);
    const isUp = c >= o;
    const bodyBottom = Math.min(o, c);
    const bodyHeight = Math.abs(c - o) || 0.01; // min height so bar is visible
    const bodyTop = Math.max(o, c);

    return {
      time: new Date(b.timestamp).toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }),
      timestamp: b.timestamp,
      open: o,
      high: h,
      low: l,
      close: c,
      volume: b.volume,
      bodyBottom,
      bodyHeight,
      wickUp: h - bodyTop,
      wickDown: bodyBottom - l,
      isUp,
    };
  });

  // Compute Y axis domain with padding
  const allLows = chartData.map((d) => d.low);
  const allHighs = chartData.map((d) => d.high);
  const minPrice = Math.min(...allLows);
  const maxPrice = Math.max(...allHighs);
  const padding = (maxPrice - minPrice) * 0.05 || 0.5;

  return (
    <div>
      {/* Controls */}
      <div className="flex items-center gap-4 mb-4">
        <div className="flex items-center gap-1">
          <span className="text-xs text-gray-400 mr-1">Interval:</span>
          {INTERVALS.map((iv) => (
            <button
              key={iv}
              onClick={() => setInterval(iv)}
              className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                interval === iv
                  ? "bg-blue-600 text-white"
                  : "bg-gray-800 text-gray-400 hover:bg-gray-700"
              }`}
            >
              {iv}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1">
          <span className="text-xs text-gray-400 mr-1">Period:</span>
          {HOURS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setHours(opt.value)}
              className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                hours === opt.value
                  ? "bg-blue-600 text-white"
                  : "bg-gray-800 text-gray-400 hover:bg-gray-700"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={350}>
        <ComposedChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            dataKey="time"
            stroke="#9ca3af"
            fontSize={11}
            interval="preserveStartEnd"
            minTickGap={40}
          />
          <YAxis
            stroke="#9ca3af"
            fontSize={11}
            domain={[minPrice - padding, maxPrice + padding]}
            tickFormatter={(v: number) => v.toFixed(2)}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1f2937",
              border: "1px solid #374151",
              borderRadius: "0.5rem",
              color: "#f3f4f6",
              fontSize: "12px",
            }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const d = payload[0].payload as CandlePoint;
              const color = d.isUp ? "#4ade80" : "#f87171";
              return (
                <div className="bg-gray-800 border border-gray-700 rounded-lg p-2 text-xs">
                  <div className="text-gray-400 mb-1">{d.timestamp}</div>
                  <div style={{ color }}>
                    O: {d.open.toFixed(2)} H: {d.high.toFixed(2)}
                  </div>
                  <div style={{ color }}>
                    L: {d.low.toFixed(2)} C: {d.close.toFixed(2)}
                  </div>
                  <div className="text-gray-400">Vol: {d.volume.toLocaleString()}</div>
                </div>
              );
            }}
          />
          {/* Candle bodies as stacked bars */}
          <Bar dataKey="bodyBottom" stackId="candle" fill="transparent" isAnimationActive={false} />
          <Bar dataKey="bodyHeight" stackId="candle" isAnimationActive={false}>
            <ErrorBar
              dataKey="wickUp"
              direction="y"
              width={1}
              strokeWidth={1}
              stroke="#9ca3af"
            />
            {chartData.map((entry, index) => (
              <Cell
                key={index}
                fill={entry.isUp ? "#4ade80" : "#f87171"}
                stroke={entry.isUp ? "#22c55e" : "#ef4444"}
              />
            ))}
          </Bar>
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
