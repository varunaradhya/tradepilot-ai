import DashboardPage from "./pages/DashboardPage";
import { useEffect, useState } from "react";

import AuthPage from "./pages/AuthPage";
import { isAuthenticated, logout } from "./services/auth";

export default function App() {
  const [authenticated, setAuthenticated] = useState(isAuthenticated);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");

  useEffect(() => {
    const syncAuth = () => setAuthenticated(isAuthenticated());
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

  return <DashboardPage onLogout={logout} />;
}
