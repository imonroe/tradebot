import { useApi } from "../hooks/useApi";

interface Strategy {
  name: string;
  symbol: string;
  type: string;
  has_position: boolean;
}

export default function Strategies() {
  const { data: strategies, loading } = useApi<Strategy[]>(
    "/api/strategies",
    10000
  );

  if (loading)
    return <div className="text-gray-400">Loading strategies...</div>;

  return (
    <div>
      <h2 className="text-lg font-semibold mb-3">Loaded Strategies</h2>
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
