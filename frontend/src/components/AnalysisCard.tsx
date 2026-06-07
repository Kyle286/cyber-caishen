import type { ChatResponse } from "../types";

const VERDICT_META: Record<string, { label: string; cls: string; emoji: string }> = {
  discourage: { label: "建议劝退", cls: "v-discourage", emoji: "🛑" },
  encourage: { label: "可以鼓励", cls: "v-encourage", emoji: "✅" },
  neutral: { label: "理性提醒", cls: "v-neutral", emoji: "⚖️" },
};

export default function AnalysisCard({ resp }: { resp: ChatResponse }) {
  const { price, impact, verdict, cot_steps } = resp;
  const hasContent = price || impact?.has_goal || cot_steps.length > 0;
  if (!hasContent) return null;

  return (
    <div className="analysis-card">
      {verdict && (
        <div className={`verdict-badge ${VERDICT_META[verdict].cls}`}>
          {VERDICT_META[verdict].emoji} {VERDICT_META[verdict].label}
        </div>
      )}

      {price && price.user_price != null && (
        <div className="price-block">
          <div className="price-head">
            🔍 同类比价 · {price.item}
            <span className="cat-tag">{price.category}</span>
          </div>
          <div className="price-bars">
            <PriceBar label="底价" value={price.lowest_price} max={price.highest_price} tone="low" />
            <PriceBar label="均价" value={price.avg_price} max={price.highest_price} tone="avg" />
            {price.user_price != null && (
              <PriceBar label="你的价" value={price.user_price} max={price.highest_price} tone="user" />
            )}
          </div>
          {price.overprice_ratio != null && (
            <div className={`overprice ${price.overprice_ratio > 0.5 ? "bad" : "ok"}`}>
              相对底价溢价 {(price.overprice_ratio * 100).toFixed(0)}%
            </div>
          )}
          <p className="price-comment">{price.comment}</p>
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
        <details className="cot-block" open>
          <summary>🧠 推理链 (CoT)</summary>
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
