import type {
  ChatContext,
  ChatResponse,
  ChatTurn,
  DecisionAction,
  GoalProgress,
  ModelId,
  Role,
  Stats,
} from "../types";

const BASE = "/api";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`请求失败 ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function getHealth(): Promise<{ status: string; llm_enabled: boolean; model: string }> {
  return handle(await fetch(`${BASE}/health`));
}

export async function getGoal(): Promise<GoalProgress> {
  return handle(await fetch(`${BASE}/goal`));
}

export async function setGoal(payload: {
  name: string;
  target_amount: number;
  monthly_saving: number;
  saved_amount: number;
}): Promise<GoalProgress> {
  return handle(
    await fetch(`${BASE}/goal`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  );
}

export async function deposit(amount: number): Promise<GoalProgress> {
  return handle(
    await fetch(`${BASE}/goal/deposit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount }),
    })
  );
}

export async function chat(
  message: string,
  role: Role,
  history: ChatTurn[] = [],
  context: ChatContext | null = null,
  model?: ModelId
): Promise<ChatResponse> {
  return handle(
    await fetch(`${BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, role, history, context, model }),
    })
  );
}

export interface StreamHandlers {
  onMeta: (meta: Omit<ChatResponse, "reply" | "llm_used">) => void;
  onDelta: (text: string) => void;
  onDone: (llmUsed: boolean) => void;
}

export async function chatStream(
  payload: { message: string; role: Role; history: ChatTurn[]; context: ChatContext | null; model?: ModelId },
  handlers: StreamHandlers
): Promise<void> {
  const res = await fetch(`${BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok || !res.body) throw new Error(`流式请求失败 ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      const evt = JSON.parse(line.slice(5).trim());
      if (evt.type === "meta") handlers.onMeta(evt.data);
      else if (evt.type === "delta") handlers.onDelta(evt.text);
      else if (evt.type === "done") handlers.onDone(evt.llm_used);
    }
  }
}

export async function getStats(): Promise<Stats> {
  return handle(await fetch(`${BASE}/stats`));
}

export async function recordDecision(payload: {
  item: string | null;
  price: number;
  action: DecisionAction;
  role: Role;
}): Promise<{ stats: Stats; progress: GoalProgress }> {
  return handle(
    await fetch(`${BASE}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  );
}
