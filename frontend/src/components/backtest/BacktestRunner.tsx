import { useState, useEffect } from "react";
import { useApi } from "../../hooks/useApi";
import StrategyOverrides from "./StrategyOverrides";
import BacktestResults from "./BacktestResults";

interface StrategyConfig {
  name: string;
  filename: string;
  config: Record<string, unknown>;
}

interface BacktestResultData {
  id: number | null;
  strategy_name: string;
  start_date: string;
  end_date: string;
  starting_capital: string;
  interval_minutes: number;
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
  daily_snapshots: { date: string; nav: string; daily_pnl: string; drawdown: string }[];
  trades: { date: string; strategy: string; symbol: string; spread_type: string; entry_price: string; pnl: number }[];
}

export default function BacktestRunner() {
  const { data: strategies } = useApi<StrategyConfig[]>("/api/backtest/strategies");

  const [selectedStrategy, setSelectedStrategy] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [capital, setCapital] = useState("2500");
  const [slippage, setSlippage] = useState("0");
  const [interval, setInterval] = useState("15");
  const [save, setSave] = useState(true);
  const [overrides, setOverrides] = useState<Record<string, number | string>>({});

  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<BacktestResultData | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Select first strategy when loaded
  useEffect(() => {
    if (strategies && strategies.length > 0 && !selectedStrategy) {
      setSelectedStrategy(strategies[0].name);
    }
  }, [strategies, selectedStrategy]);

  const selectedConfig = strategies?.find((s) => s.name === selectedStrategy)?.config;

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    setResult(null);

    const cleanOverrides: Record<string, number | string> = {};
    for (const [k, v] of Object.entries(overrides)) {
      if (v !== "") cleanOverrides[k] = v;
    }

    try {
      const response = await fetch("/api/backtest/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          strategy: selectedStrategy,
          start_date: startDate,
          end_date: endDate,
          starting_capital: parseFloat(capital),
          slippage_pct: parseFloat(slippage),
          interval_minutes: parseInt(interval),
          save,
          overrides: Object.keys(cleanOverrides).length > 0 ? cleanOverrides : undefined,
        }),
      });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || `Error ${response.status}`);
      }
      const data: BacktestResultData = await response.json();
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setRunning(false);
    }
  };

  const canRun = selectedStrategy && startDate && endDate && !running;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Config Form */}
      <div className="space-y-4">
        <h3 className="font-semibold text-gray-200">Configuration</h3>

        <div>
          <label className="block text-sm text-gray-400 mb-1">Strategy</label>
          <select
            value={selectedStrategy}
            onChange={(e) => {
              setSelectedStrategy(e.target.value);
              setOverrides({});
            }}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
          >
            {strategies?.map((s) => (
              <option key={s.name} value={s.name}>{s.name}</option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Capital ($)</label>
            <input
              type="number"
              value={capital}
              onChange={(e) => setCapital(e.target.value)}
              min="100"
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Slippage %</label>
            <input
              type="number"
              value={slippage}
              onChange={(e) => setSlippage(e.target.value)}
              min="0"
              max="5"
              step="0.1"
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Interval (min)</label>
            <input
              type="number"
              value={interval}
              onChange={(e) => setInterval(e.target.value)}
              min="1"
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
            />
          </div>
        </div>

        {selectedConfig && (
          <StrategyOverrides
            config={selectedConfig}
            overrides={overrides}
            onChange={setOverrides}
          />
        )}

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-400">
            <input
              type="checkbox"
              checked={save}
              onChange={(e) => setSave(e.target.checked)}
              className="rounded"
            />
            Save to history
          </label>
        </div>

        <button
          onClick={handleRun}
          disabled={!canRun}
          className={`w-full py-2 rounded font-medium ${
            canRun
              ? "bg-green-600 hover:bg-green-500 text-white"
              : "bg-gray-700 text-gray-500 cursor-not-allowed"
          }`}
        >
          {running ? "Running..." : "Run Backtest"}
        </button>

        {error && (
          <div className="bg-red-900/50 border border-red-700 rounded p-3 text-sm text-red-300">
            {error}
          </div>
        )}
      </div>

      {/* Results */}
      <div className="lg:col-span-2">
        {running && (
          <div className="flex items-center justify-center h-64 text-gray-400">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-400 mx-auto mb-3"></div>
              <p>Running backtest...</p>
            </div>
          </div>
        )}
        {!running && result && <BacktestResults result={result} />}
        {!running && !result && !error && (
          <div className="flex items-center justify-center h-64 text-gray-500">
            Configure and run a backtest to see results here.
          </div>
        )}
      </div>
    </div>
  );
}
