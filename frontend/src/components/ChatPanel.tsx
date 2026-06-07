import { useEffect, useRef, useState } from "react";
import type { ChatContext, ChatMessage, ChatTurn, DecisionAction, Role } from "../types";
import { chat, recordDecision } from "../api/client";
import MessageBubble from "./MessageBubble";

interface Props {
  role: Role;
  onGoalMayChange: () => void;
  onStatsMayChange: () => void;
}

const SUGGESTIONS = [
  "我好想花 800 块买个盲盒",
  "直播间一双球鞋 1299，要不要冲？",
  "想喝杯 32 块的网红奶茶",
  "我的攒钱进度怎么样了",
];

const WELCOME: Record<Role, string> = {
  caishen:
    "我是赛博财神爷～ 想买点啥？把你的冲动告诉我，我帮你比比价、算算账，看这钱该不该花！💰",
  bestie:
    "你的毒舌闺蜜上线啦💅 又想剁手了是吧？说吧想买啥，我帮你扒拉扒拉底价，省得你交智商税！",
};

function welcomeMessage(role: Role): ChatMessage {
  return { id: `welcome-${role}`, sender: "agent", text: WELCOME[role] };
}

export default function ChatPanel({ role, onGoalMayChange, onStatsMayChange }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([welcomeMessage(role)]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [context, setContext] = useState<ChatContext | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // 切换人格时重置会话，保证一个会话只有一种人格，避免角色混淆
  useEffect(() => {
    setMessages([welcomeMessage(role)]);
    setContext(null);
  }, [role]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  async function send(text: string) {
    const content = text.trim();
    if (!content || loading) return;
    const userMsg: ChatMessage = { id: `u-${Date.now()}`, sender: "user", text: content };
    // 取最近若干轮作为多轮历史
    const history: ChatTurn[] = messages
      .filter((m) => m.id !== "welcome-caishen" && m.id !== "welcome-bestie")
      .slice(-6)
      .map((m) => ({ sender: m.sender, text: m.text }));
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const resp = await chat(content, role, history, context);
      const agentMsg: ChatMessage = {
        id: `a-${Date.now()}`,
        sender: "agent",
        text: resp.reply,
        response: resp,
      };
      setMessages((m) => [...m, agentMsg]);
      setContext(resp.context ?? null);
      if (resp.intent === "purchase" || resp.intent === "query_progress" || resp.intent === "resist")
        onGoalMayChange();
    } catch (e) {
      setMessages((m) => [
        ...m,
        { id: `e-${Date.now()}`, sender: "agent", text: `出错了：${(e as Error).message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function decide(msg: ChatMessage, action: DecisionAction) {
    const price = msg.response?.price;
    if (!price || price.user_price == null) return;
    try {
      await recordDecision({ item: price.item, price: price.user_price, action, role });
      setMessages((arr) => arr.map((m) => (m.id === msg.id ? { ...m, decided: action } : m)));
      onGoalMayChange();
      onStatsMayChange();
    } catch (e) {
      setMessages((arr) => [
        ...arr,
        { id: `e-${Date.now()}`, sender: "agent", text: `记录失败：${(e as Error).message}` },
      ]);
    }
  }

  return (
    <section className="chat-panel">
      <div className="chat-list" ref={listRef}>
        {messages.map((m) => (
          <MessageBubble key={m.id} msg={m} role={role} onDecide={decide} />
        ))}
        {loading && (
          <div className="bubble-row from-agent">
            <div className="avatar">{role === "bestie" ? "💅" : "🧧"}</div>
            <div className="bubble agent typing">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
      </div>

      <div className="suggestions">
        {SUGGESTIONS.map((s) => (
          <button key={s} onClick={() => send(s)} disabled={loading}>
            {s}
          </button>
        ))}
      </div>

      <form
        className="chat-input"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="说出你的购物冲动……"
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          发送
        </button>
      </form>
    </section>
  );
}
