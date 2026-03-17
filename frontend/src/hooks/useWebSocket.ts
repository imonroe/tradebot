import { useEffect, useRef, useState, useCallback } from "react";

interface PortfolioSnapshot {
  nav: string;
  daily_pnl: string;
  drawdown_pct: string;
  positions: number;
  mode: string;
  bot_running: boolean;
  pdt_day_trades_used: number;
}

export function useWebSocket() {
  const [data, setData] = useState<PortfolioSnapshot | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/ws`);

    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      setTimeout(connect, 3000);
    };
    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        setData(parsed);
      } catch {
        // ignore malformed messages
      }
    };

    wsRef.current = ws;
  }, []);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  return { data, connected };
}
