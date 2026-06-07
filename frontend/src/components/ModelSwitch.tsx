import type { ModelId } from "../types";

interface Props {
  model: ModelId;
  onChange: (m: ModelId) => void;
  disabled?: boolean;
}

const MODELS: { id: ModelId; label: string; desc: string }[] = [
  { id: "deepseek-v4-flash", label: "Flash", desc: "响应快·默认" },
  { id: "deepseek-v4-pro", label: "Pro", desc: "推理更强" },
];

export default function ModelSwitch({ model, onChange, disabled }: Props) {
  return (
    <div className="model-switch" title="切换 DeepSeek 模型">
      {MODELS.map((m) => (
        <button
          key={m.id}
          className={`model-chip ${model === m.id ? "active" : ""}`}
          onClick={() => onChange(m.id)}
          aria-pressed={model === m.id}
          disabled={disabled}
          title={m.desc}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}
