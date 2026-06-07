import { useState } from "react";
import type { GoalProgress } from "../types";
import { deposit, setGoal } from "../api/client";
import ProgressRing from "./ProgressRing";

interface Props {
  progress: GoalProgress | null;
  onUpdated: (p: GoalProgress) => void;
}

export default function GoalPanel({ progress, onUpdated }: Props) {
  const goal = progress?.goal ?? null;
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  const [target, setTarget] = useState("");
  const [monthly, setMonthly] = useState("");
  const [saved, setSaved] = useState("0");
  const [depositVal, setDepositVal] = useState("");
  const [busy, setBusy] = useState(false);

  // 没有目标时强制展示表单；有目标时进入编辑会预填当前值
  const showForm = editing || !goal;

  function startEditing() {
    setName(goal?.name ?? "");
    setTarget(goal?.target_amount?.toString() ?? "");
    setMonthly(goal?.monthly_saving?.toString() ?? "");
    setSaved(goal?.saved_amount?.toString() ?? "0");
    setEditing(true);
  }

  async function submitGoal() {
    if (!name.trim() || !Number(target)) return;
    setBusy(true);
    try {
      const p = await setGoal({
        name: name.trim(),
        target_amount: Number(target),
        monthly_saving: Number(monthly) || 0,
        saved_amount: Number(saved) || 0,
      });
      onUpdated(p);
      setEditing(false);
    } finally {
      setBusy(false);
    }
  }

  async function doDeposit() {
    const amt = Number(depositVal);
    if (!amt) return;
    setBusy(true);
    try {
      const p = await deposit(amt);
      onUpdated(p);
      setDepositVal("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <aside className="goal-panel">
      <h2>🎯 我的攒钱目标</h2>

      {!showForm && goal && (
        <>
          <div className="ring-wrap">
            <ProgressRing ratio={progress?.progress_ratio ?? 0} />
          </div>
          <div className="goal-name">{goal.name}</div>
          <div className="goal-stats">
            <div>
              <span>已攒</span>
              <strong>¥{goal.saved_amount.toLocaleString()}</strong>
            </div>
            <div>
              <span>目标</span>
              <strong>¥{goal.target_amount.toLocaleString()}</strong>
            </div>
            <div>
              <span>还差</span>
              <strong>¥{(progress?.remaining ?? 0).toLocaleString()}</strong>
            </div>
          </div>
          {progress?.months_to_go != null && (
            <p className="goal-eta">按当前速度约还需 {progress.months_to_go} 个月达成 ✨</p>
          )}

          <div className="deposit-row">
            <input
              type="number"
              placeholder="存入金额"
              value={depositVal}
              onChange={(e) => setDepositVal(e.target.value)}
            />
            <button onClick={doDeposit} disabled={busy}>
              存入 💰
            </button>
          </div>
          <button className="link-btn" onClick={startEditing}>
            修改目标
          </button>
        </>
      )}

      {showForm && (
        <div className="goal-form">
          <label>
            目标名称
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="如：iPhone 16" />
          </label>
          <label>
            目标金额 (¥)
            <input type="number" value={target} onChange={(e) => setTarget(e.target.value)} placeholder="6000" />
          </label>
          <label>
            每月可攒 (¥)
            <input type="number" value={monthly} onChange={(e) => setMonthly(e.target.value)} placeholder="2000" />
          </label>
          <label>
            已攒金额 (¥)
            <input type="number" value={saved} onChange={(e) => setSaved(e.target.value)} placeholder="0" />
          </label>
          <button className="primary-btn" onClick={submitGoal} disabled={busy}>
            保存目标
          </button>
          {goal && (
            <button className="link-btn" onClick={() => setEditing(false)}>
              取消
            </button>
          )}
        </div>
      )}
    </aside>
  );
}
