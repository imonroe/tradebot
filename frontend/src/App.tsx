import { Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Trades from "./pages/Trades";
import Strategies from "./pages/Strategies";

function App() {
  return (
    <div className="min-h-screen">
      <nav className="bg-gray-900 border-b border-gray-800 px-6 py-3">
        <div className="flex items-center gap-8">
          <h1 className="text-xl font-bold text-green-400">Tradebot</h1>
          <div className="flex gap-4">
            <NavLink
              to="/"
              className={({ isActive }) =>
                `px-3 py-1 rounded ${isActive ? "bg-gray-700 text-white" : "text-gray-400 hover:text-white"}`
              }
            >
              Dashboard
            </NavLink>
            <NavLink
              to="/trades"
              className={({ isActive }) =>
                `px-3 py-1 rounded ${isActive ? "bg-gray-700 text-white" : "text-gray-400 hover:text-white"}`
              }
            >
              Trades
            </NavLink>
            <NavLink
              to="/strategies"
              className={({ isActive }) =>
                `px-3 py-1 rounded ${isActive ? "bg-gray-700 text-white" : "text-gray-400 hover:text-white"}`
              }
            >
              Strategies
            </NavLink>
          </div>
        </div>
      </nav>
      <main className="p-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/trades" element={<Trades />} />
          <Route path="/strategies" element={<Strategies />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
