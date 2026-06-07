import type { Role } from "../types";

interface Props {
  role: Role;
  onChange: (role: Role) => void;
}

const ROLES: { id: Role; label: string; emoji: string; desc: string }[] = [
  { id: "caishen", label: "赛博财神", emoji: "🧧", desc: "温暖鼓励·理性引导" },
  { id: "bestie", label: "毒舌闺蜜", emoji: "💅", desc: "犀利劝退·拒绝智商税" },
];

export default function RoleSwitch({ role, onChange }: Props) {
  return (
    <div className="role-switch">
      {ROLES.map((r) => (
        <button
          key={r.id}
          className={`role-chip ${role === r.id ? "active" : ""}`}
          onClick={() => onChange(r.id)}
          aria-pressed={role === r.id}
          title={r.desc}
        >
          <span className="role-emoji">{r.emoji}</span>
          <span className="role-text">
            <strong>{r.label}</strong>
            <small>{r.desc}</small>
          </span>
        </button>
      ))}
    </div>
  );
}
