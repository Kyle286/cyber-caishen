import { useEffect, useRef, useState } from "react";
import type {
  ChatContext,
  ChatMessage,
  ChatResponse,
  ChatTurn,
  DecisionAction,
  ModelId,
  Role,
} from "../types";
import { chatStream, deposit, recordDecision } from "../api/client";
import MessageBubble from "./MessageBubble";

interface Props {
  role: Role;
  model: ModelId;
  hasGoal: boolean;
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

export default function ChatPanel({ role, model, hasGoal, onGoalMayChange, onStatsMayChange }: Props) {
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

    const agentId = `a-${Date.now()}`;
    try {
      await chatStream(
        { message: content, role, history, context, model },
        {
          onMeta: (meta) => {
            const resp = { ...meta, reply: "", llm_used: false } as ChatResponse;
            setMessages((m) => [
              ...m,
              { id: agentId, sender: "agent", text: "", response: resp, streaming: true },
            ]);
            setContext(resp.context ?? null);
            if (["purchase", "query_progress", "resist"].includes(resp.intent)) onGoalMayChange();
          },
          onDelta: (t) => {
            setMessages((m) => m.map((x) => (x.id === agentId ? { ...x, text: x.text + t } : x)));
          },
          onDone: (llmUsed) => {
            setMessages((m) =>
              m.map((x) =>
                x.id === agentId && x.response
                  ? { ...x, streaming: false, response: { ...x.response, llm_used: llmUsed } }
                  : x
              )
            );
          },
        }
      );
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
      onStatsMayChange();
    } catch (e) {
      setMessages((arr) => [
        ...arr,
        { id: `e-${Date.now()}`, sender: "agent", text: `记录失败：${(e as Error).message}` },
      ]);
    }
  }

  // 用户明确把省下的钱存进目标（对应现实中真去转一笔账）
  async function depositSaved(msg: ChatMessage) {
    const price = msg.response?.price;
    if (!price || price.user_price == null) return;
    try {
      await deposit(price.user_price);
      setMessages((arr) => arr.map((m) => (m.id === msg.id ? { ...m, deposited: true } : m)));
      onGoalMayChange();
    } catch (e) {
      setMessages((arr) => [
        ...arr,
        { id: `e-${Date.now()}`, sender: "agent", text: `存入失败：${(e as Error).message}` },
      ]);
    }
  }

  return (
    <section className="chat-panel">
      <div className="chat-list" ref={listRef}>
        {messages.map((m) => (
          <MessageBubble
            key={m.id}
            msg={m}
            role={role}
            hasGoal={hasGoal}
            onDecide={decide}
            onDepositSaved={depositSaved}
          />
        ))}
        {loading && messages[messages.length - 1]?.sender === "user" && (
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
