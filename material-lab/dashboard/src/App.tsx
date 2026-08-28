import { LockKey } from "@phosphor-icons/react/LockKey";
import { FormEvent, useEffect, useState } from "react";
import { InventoryDashboard } from "./inventory/InventoryDashboard";
import { dashboardApi, userMessage, type SessionInfo } from "./inventory/api";

function LoginScreen({ onLogin }: { onLogin: (session: SessionInfo) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await dashboardApi.login(username, password);
      onLogin({ authenticated: true, mode: result.mode, username: result.username });
    } catch (caught) {
      setError(userMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="auth-screen min-h-[100dvh]">
      <section className="auth-card" aria-labelledby="login-title">
        <div className="auth-mark"><LockKey size={24} weight="duotone" /></div>
        <p className="eyebrow">PrintPilot</p>
        <h1 id="login-title">登录耗材看板</h1>
        <p className="auth-intro">查看耗材档案并维护当前库存。</p>
        {error && <div className="auth-error" role="alert">{error}</div>}
        <form className="auth-form" onSubmit={submit}>
          <label>
            <span>用户名</span>
            <input autoComplete="username" autoFocus required maxLength={64} value={username} onChange={(event) => setUsername(event.target.value)} />
          </label>
          <label>
            <span>密码</span>
            <input autoComplete="current-password" required type="password" maxLength={256} value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>
          <button className="primary-button auth-submit" type="submit" disabled={busy}>
            {busy ? "正在登录" : "登录"}
          </button>
        </form>
      </section>
    </main>
  );
}

export function App() {
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    dashboardApi.session().then(setSession).catch((caught) => setError(userMessage(caught)));
  }, []);

  if (error) {
    return <main className="auth-screen min-h-[100dvh]"><section className="auth-card"><p className="eyebrow">PrintPilot</p><h1>看板暂时不可用</h1><div className="auth-error">{error}</div></section></main>;
  }
  if (session === null) {
    return <main className="auth-screen min-h-[100dvh]"><section className="auth-card"><p className="eyebrow">PrintPilot</p><h1>正在连接耗材库</h1></section></main>;
  }
  if (!session.authenticated) {
    return <LoginScreen onLogin={setSession} />;
  }
  return <InventoryDashboard session={session} onSessionEnded={() => setSession({ ...session, authenticated: false, username: null })} />;
}
