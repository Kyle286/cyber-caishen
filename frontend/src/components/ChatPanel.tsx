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
import { sanitizeReply } from "../utils/reply";
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

interface RoleSession {
  messages: ChatMessage[];
  context: ChatContext | null;
}

function welcomeMessage(role: Role): ChatMessage {
  return { id: `welcome-${role}`, sender: "agent", text: WELCOME[role] };
}

function freshSession(role: Role): RoleSession {
  return { messages: [welcomeMessage(role)], context: null };
}

export default function ChatPanel({ role, model, hasGoal, onGoalMayChange, onStatsMayChange }: Props) {
  const [sessions, setSessions] = useState<Record<Role, RoleSession>>({
    caishen: freshSession("caishen"),
    bestie: freshSession("bestie"),
  });
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  const { messages } = sessions[role];

  const patchSession = (r: Role, patch: Partial<RoleSession>) => {
    setSessions((s) => ({ ...s, [r]: { ...s[r], ...patch } }));
  };

  const setMessages = (r: Role, updater: (m: ChatMessage[]) => ChatMessage[]) => {
    setSessions((s) => ({ ...s, [r]: { ...s[r], messages: updater(s[r].messages) } }));
  };

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading, role]);

  async function send(text: string) {
    const content = text.trim();
    if (!content || loading) return;
    const activeRole = role;
    const userMsg: ChatMessage = { id: `u-${Date.now()}`, sender: "user", text: content };
    const history: ChatTurn[] = sessions[activeRole].messages
      .filter((m) => m.id !== "welcome-caishen" && m.id !== "welcome-bestie")
      .slice(-6)
      .map((m) => ({ sender: m.sender, text: m.text }));
    setMessages(activeRole, (m) => [...m, userMsg]);
    setInput("");
    setLoading(true);

    const agentId = `a-${Date.now()}`;
    const streamContext = sessions[activeRole].context;
    try {
      await chatStream(
        { message: content, role: activeRole, history, context: streamContext, model },
        {
          onDelta: (t) => {
            setMessages(activeRole, (m) => {
              const exists = m.some((x) => x.id === agentId);
              if (!exists) {
                return [...m, { id: agentId, sender: "agent", text: t, streaming: true }];
              }
              return m.map((x) => (x.id === agentId ? { ...x, text: x.text + t } : x));
            });
          },
          onDone: (data, llmUsed) => {
            setMessages(activeRole, (m) =>
              m.map((x) => {
                if (x.id !== agentId) return x;
                const reply = sanitizeReply(x.text);
                return {
                  ...x,
                  text: reply,
                  streaming: false,
                  response: data
                    ? ({ ...data, reply, llm_used: llmUsed } as ChatResponse)
                    : undefined,
                };
              })
            );
            if (!data) return;
            patchSession(activeRole, { context: data.context ?? null });
            if (["purchase", "query_progress", "resist"].includes(data.intent)) onGoalMayChange();
          },
        }
      );
    } catch (e) {
      setMessages(activeRole, (m) => [
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
      setMessages(role, (arr) => arr.map((m) => (m.id === msg.id ? { ...m, decided: action } : m)));
      onStatsMayChange();
    } catch (e) {
      setMessages(role, (arr) => [
        ...arr,
        { id: `e-${Date.now()}`, sender: "agent", text: `记录失败：${(e as Error).message}` },
      ]);
    }
  }

  async function depositSaved(msg: ChatMessage) {
    const price = msg.response?.price;
    if (!price || price.user_price == null) return;
    try {
      await deposit(price.user_price);
      setMessages(role, (arr) => arr.map((m) => (m.id === msg.id ? { ...m, deposited: true } : m)));
      onGoalMayChange();
    } catch (e) {
      setMessages(role, (arr) => [
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
