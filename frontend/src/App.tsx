import { useCallback, useEffect, useState } from "react";
import type { GoalProgress, ModelId, Role, Stats } from "./types";
import { getGoal, getHealth, getStats } from "./api/client";
import RoleSwitch from "./components/RoleSwitch";
import ModelSwitch from "./components/ModelSwitch";
import GoalPanel from "./components/GoalPanel";
import ChatPanel from "./components/ChatPanel";

export default function App() {
  const [role, setRole] = useState<Role>("caishen");
  const [model, setModel] = useState<ModelId>("deepseek-v4-flash");
  const [progress, setProgress] = useState<GoalProgress | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [llmEnabled, setLlmEnabled] = useState<boolean | null>(null);

  const refreshGoal = useCallback(async () => {
    try {
      setProgress(await getGoal());
    } catch {
      /* 后端未启动时静默 */
    }
  }, []);

  const refreshStats = useCallback(async () => {
    try {
      setStats(await getStats());
    } catch {
      /* 静默 */
    }
  }, []);

  useEffect(() => {
    refreshGoal();
    refreshStats();
    getHealth()
      .then((h) => setLlmEnabled(h.llm_enabled))
      .catch(() => setLlmEnabled(null));
  }, [refreshGoal, refreshStats]);

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
        <div className="topbar-right">
          {stats && (stats.resisted_count > 0 || stats.bought_count > 0) && (
            <div className="stats-badge" title="忍住的金额，可一键存进攒钱目标">
              💪 已劝退 {stats.resisted_count} 次 · 免于冲动 ¥{stats.total_avoided.toLocaleString()}
            </div>
          )}
          {llmEnabled && <ModelSwitch model={model} onChange={setModel} />}
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
        </div>
      </header>

      <main className="layout">
        <GoalPanel progress={progress} onUpdated={setProgress} />
        <ChatPanel
          role={role}
          model={model}
          hasGoal={progress?.goal != null}
          onGoalMayChange={refreshGoal}
          onStatsMayChange={refreshStats}
        />
      </main>
    </div>
  );
}
