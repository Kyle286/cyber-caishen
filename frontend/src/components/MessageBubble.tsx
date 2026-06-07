import type { ChatMessage, Role } from "../types";
import AnalysisCard from "./AnalysisCard";

const ROLE_AVATAR: Record<Role, string> = { caishen: "🧧", bestie: "💅" };

export default function MessageBubble({ msg, role }: { msg: ChatMessage; role: Role }) {
  const isUser = msg.sender === "user";
  return (
    <div className={`bubble-row ${isUser ? "from-user" : "from-agent"}`}>
      {!isUser && <div className="avatar">{ROLE_AVATAR[msg.response?.role ?? role]}</div>}
      <div className="bubble-content">
        <div className={`bubble ${isUser ? "user" : "agent"}`}>{msg.text}</div>
        {msg.response && !isUser && (
          <>
            {msg.response.llm_used ? (
              <span className="src-tag llm">DeepSeek 生成</span>
            ) : (
              <span className="src-tag local">本地规则兜底</span>
            )}
            <AnalysisCard resp={msg.response} />
          </>
        )}
      </div>
      {isUser && <div className="avatar user-avatar">🙋</div>}
    </div>
  );
}
