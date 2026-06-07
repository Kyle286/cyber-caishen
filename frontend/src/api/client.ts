import type {
  ChatContext,
  ChatResponse,
  ChatTurn,
  DecisionAction,
  GoalProgress,
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
  context: ChatContext | null = null
): Promise<ChatResponse> {
  return handle(
    await fetch(`${BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, role, history, context }),
    })
  );
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
