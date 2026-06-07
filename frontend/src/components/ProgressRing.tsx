interface Props {
  ratio: number; // 0..1
  size?: number;
  stroke?: number;
}

export default function ProgressRing({ ratio, size = 140, stroke = 12 }: Props) {
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(1, ratio));
  const offset = circumference * (1 - clamped);
  const pct = Math.round(clamped * 100);

  return (
    <svg width={size} height={size} className="progress-ring">
      <defs>
        <linearGradient id="ringGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#ffd36b" />
          <stop offset="100%" stopColor="#ff7e5f" />
        </linearGradient>
      </defs>
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="rgba(255,255,255,0.12)"
        strokeWidth={stroke}
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="url(#ringGrad)"
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
        style={{ transition: "stroke-dashoffset 0.8s ease" }}
      />
      <text x="50%" y="48%" textAnchor="middle" className="ring-pct">
        {pct}%
      </text>
      <text x="50%" y="64%" textAnchor="middle" className="ring-label">
        已攒进度
      </text>
    </svg>
  );
}
