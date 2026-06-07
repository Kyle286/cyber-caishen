import type { ChatResponse, DecisionAction } from "../types";

const VERDICT_META: Record<string, { label: string; cls: string; emoji: string }> = {
  discourage: { label: "建议劝退", cls: "v-discourage", emoji: "🛑" },
  encourage: { label: "可以鼓励", cls: "v-encourage", emoji: "✅" },
  neutral: { label: "理性提醒", cls: "v-neutral", emoji: "⚖️" },
};

interface Props {
  resp: ChatResponse;
  decided?: DecisionAction;
  deposited?: boolean;
  hasGoal: boolean;
  onDecide: (action: DecisionAction) => void;
  onDepositSaved: () => void;
}

export default function AnalysisCard({ resp, decided, deposited, hasGoal, onDecide, onDepositSaved }: Props) {
  const { price, impact, verdict, impulse, opportunity_cost, cot_steps } = resp;
  const hasContent = price || impact?.has_goal || cot_steps.length > 0;
  if (!hasContent) return null;

  const showActions = resp.intent === "purchase" && price?.user_price != null;

  return (
    <div className="analysis-card">
      {verdict && (
        <div className={`verdict-badge ${VERDICT_META[verdict].cls}`}>
          {VERDICT_META[verdict].emoji} {VERDICT_META[verdict].label}
        </div>
      )}

      {impulse && <ImpulseGauge score={impulse.score} level={impulse.level} reasons={impulse.reasons} />}

      {price && price.user_price != null && (
        <div className="price-block">
          <div className="price-head">
            🔍 同类比价 · {price.item}
            <span className="cat-tag">{price.category}</span>
          </div>
          <div className="price-bars">
            <PriceBar label="底价" value={price.lowest_price} max={price.highest_price} tone="low" />
            <PriceBar label="均价" value={price.avg_price} max={price.highest_price} tone="avg" />
            <PriceBar label="你的价" value={price.user_price} max={price.highest_price} tone="user" />
          </div>
          {price.overprice_ratio != null && (
            <div className={`overprice ${price.overprice_ratio > 0.5 ? "bad" : "ok"}`}>
              相对底价溢价 {(price.overprice_ratio * 100).toFixed(0)}%
              {price.save_if_lowest ? ` · 买到底价可省 ¥${price.save_if_lowest.toLocaleString()}` : ""}
            </div>
          )}
          <p className="price-comment">{price.comment}</p>
        </div>
      )}

      {opportunity_cost.length > 0 && (
        <div className="oc-block">
          <span className="oc-head">💡 这笔钱</span>
          {opportunity_cost.map((o, i) => (
            <span key={i} className="oc-chip">{o}</span>
          ))}
        </div>
      )}

      {impact && impact.has_goal && (impact.goal_impact_ratio != null || impact.delay_days != null) && (
        <div className="impact-block">
          <div className="impact-head">📉 对攒钱目标的影响</div>
          <div className="impact-metrics">
            {impact.goal_impact_ratio != null && (
              <div className="metric">
                <strong>{(impact.goal_impact_ratio * 100).toFixed(1)}%</strong>
                <span>占目标比例</span>
              </div>
            )}
            {impact.delay_days != null && (
              <div className="metric">
                <strong>{impact.delay_days} 天</strong>
                <span>目标延后</span>
              </div>
            )}
          </div>
        </div>
      )}

      {cot_steps.length > 0 && (
        <details className="cot-block">
          <summary>🧠 推理链 (CoT) · {cot_steps.length} 步</summary>
          <ol>
            {cot_steps.map((s, i) => (
              <li key={i}>
                <span className="cot-label">{s.label}</span>
                <span className="cot-detail">{s.detail}</span>
              </li>
            ))}
          </ol>
        </details>
      )}

      {showActions && (
        <div className="decision-row">
          {!decided && (
            <>
              <button className="resist-btn" onClick={() => onDecide("resisted")}>
                💪 我忍住了
              </button>
              <button className="bought-btn" onClick={() => onDecide("bought")}>
                🛍️ 还是买了
              </button>
            </>
          )}
          {decided === "bought" && <span className="decided-chip bought">🛍️ 已记录这笔消费</span>}
          {decided === "resisted" && (
            <>
              <span className="decided-chip resisted">
                💪 已忍住，免于冲动消费 ¥{price!.user_price!.toLocaleString()}
              </span>
              {hasGoal && !deposited && (
                <button className="deposit-saved-btn" onClick={onDepositSaved}>
                  把省下的 ¥{price!.user_price!.toLocaleString()} 存进目标 💰
                </button>
              )}
              {deposited && <span className="decided-chip resisted">✅ 已存进攒钱目标</span>}
            </>
          )}
        </div>
      )}
    </div>
  );
}

function ImpulseGauge({ score, level, reasons }: { score: number; level: string; reasons: string[] }) {
  const tone = score < 30 ? "calm" : score < 55 ? "mild" : score < 80 ? "high" : "max";
  return (
    <div className={`impulse-gauge tone-${tone}`}>
      <div className="impulse-top">
        <span className="impulse-title">🔥 冲动指数</span>
        <span className="impulse-score">
          {score}
          <small>/100 · {level}</small>
        </span>
      </div>
      <div className="impulse-track">
        <div className="impulse-fill" style={{ width: `${score}%` }} />
      </div>
      <div className="impulse-reasons">{reasons.join(" · ")}</div>
    </div>
  );
}

function PriceBar({ label, value, max, tone }: { label: string; value: number; max: number; tone: string }) {
  const pct = Math.max(4, Math.min(100, (value / (max || 1)) * 100));
  return (
    <div className={`price-bar-row tone-${tone}`}>
      <span className="bar-label">{label}</span>
      <div className="bar-track">
        <div className="bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="bar-value">¥{value.toLocaleString()}</span>
    </div>
  );
}
