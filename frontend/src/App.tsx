import { useCallback, useEffect, useState } from "react";
import type { GoalProgress, Role } from "./types";
import { getGoal, getHealth } from "./api/client";
import RoleSwitch from "./components/RoleSwitch";
import GoalPanel from "./components/GoalPanel";
import ChatPanel from "./components/ChatPanel";

export default function App() {
  const [role, setRole] = useState<Role>("caishen");
  const [progress, setProgress] = useState<GoalProgress | null>(null);
  const [llmEnabled, setLlmEnabled] = useState<boolean | null>(null);

  const refreshGoal = useCallback(async () => {
    try {
      setProgress(await getGoal());
    } catch {
      /* 后端未启动时静默 */
    }
  }, []);

  useEffect(() => {
    refreshGoal();
    getHealth()
      .then((h) => setLlmEnabled(h.llm_enabled))
      .catch(() => setLlmEnabled(null));
  }, [refreshGoal]);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-logo">💰</span>
          <div>
            <h1>赛博财神爷</h1>
            <p>反冲动消费 · 攒钱陪伴 Agent</p>
          </div>
        </div>
        <RoleSwitch role={role} onChange={setRole} />
        <div className="llm-status">
          {llmEnabled === null && <span className="dot gray" />}
          {llmEnabled === true && (
            <>
              <span className="dot green" /> DeepSeek 已接入
            </>
          )}
          {llmEnabled === false && (
            <>
              <span className="dot amber" /> 本地兜底模式
            </>
          )}
        </div>
      </header>

      <main className="layout">
        <GoalPanel progress={progress} onUpdated={setProgress} />
        <ChatPanel role={role} onGoalMayChange={refreshGoal} />
      </main>
    </div>
  );
}
