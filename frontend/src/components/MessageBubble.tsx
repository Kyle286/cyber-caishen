import type { ChatMessage, DecisionAction, Role } from "../types";
import AnalysisCard from "./AnalysisCard";

const ROLE_AVATAR: Record<Role, string> = { caishen: "🧧", bestie: "💅" };

interface Props {
  msg: ChatMessage;
  role: Role;
  hasGoal: boolean;
  onDecide: (msg: ChatMessage, action: DecisionAction) => void;
  onDepositSaved: (msg: ChatMessage) => void;
}

export default function MessageBubble({ msg, role, hasGoal, onDecide, onDepositSaved }: Props) {
  const isUser = msg.sender === "user";
  return (
    <div className={`bubble-row ${isUser ? "from-user" : "from-agent"}`}>
      {!isUser && <div className="avatar">{ROLE_AVATAR[msg.response?.role ?? role]}</div>}
      <div className="bubble-content">
        <div className={`bubble ${isUser ? "user" : "agent"}`}>{msg.text}</div>
        {!isUser && msg.streaming && (
          <span className="src-tag streaming">DeepSeek 生成中…</span>
        )}
        {msg.response && !isUser && !msg.streaming && (
          <>
            {msg.response.llm_used ? (
              <span className="src-tag llm">DeepSeek 生成</span>
            ) : (
              <span className="src-tag local">本地规则兜底</span>
            )}
            <AnalysisCard
              resp={msg.response}
              decided={msg.decided}
              deposited={msg.deposited}
              hasGoal={hasGoal}
              onDecide={(action) => onDecide(msg, action)}
              onDepositSaved={() => onDepositSaved(msg)}
            />
          </>
        )}
      </div>
      {isUser && <div className="avatar user-avatar">🙋</div>}
    </div>
  );
}
