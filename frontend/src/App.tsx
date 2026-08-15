import { useEffect, useState } from "react";

import AuthPage from "./pages/AuthPage";
import DashboardPage from "./pages/DashboardPage";
import TransactionsPage from "./pages/TransactionsPage";
import { isAuthenticated, logout } from "./services/auth";

export default function App() {
  const [authenticated, setAuthenticated] = useState(isAuthenticated);
  const [page, setPage] = useState<"dashboard" | "transactions">("dashboard");
  const [authMode, setAuthMode] = useState<"login" | "register">("login");

  useEffect(() => {
    const syncAuth = () => {
      setAuthenticated(isAuthenticated());
      setPage("dashboard");
    };
    window.addEventListener("tradepilot:login", syncAuth);
    window.addEventListener("tradepilot:logout", syncAuth);
    return () => {
      window.removeEventListener("tradepilot:login", syncAuth);
      window.removeEventListener("tradepilot:logout", syncAuth);
    };
  }, []);

  if (!authenticated) {
    return <AuthPage mode={authMode} onModeChange={setAuthMode} onAuthenticated={() => setAuthenticated(true)} />;
  }

  if (page === "transactions") {
    return <TransactionsPage onBack={() => setPage("dashboard")} />;
  }

  return <DashboardPage onLogout={logout} onTransactions={() => setPage("transactions")} />;
}
