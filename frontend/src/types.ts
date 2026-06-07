export type Role = "caishen" | "bestie";
export type ModelId = "deepseek-v4-flash" | "deepseek-v4-pro";
export type IntentType = "purchase" | "set_goal" | "query_progress" | "resist" | "chitchat";
export type Verdict = "discourage" | "encourage" | "neutral";
export type DecisionAction = "resisted" | "bought";

export interface PriceInfo {
  item: string;
  category: string;
  user_price: number | null;
  avg_price: number;
  lowest_price: number;
  highest_price: number;
  overprice_ratio: number | null;
  save_if_lowest: number | null;
  comment: string;
}

export interface ImpulseScore {
  score: number;
  level: string;
  reasons: string[];
}

export interface ChatContext {
  last_item: string | null;
  last_price: number | null;
}

export interface ChatTurn {
  sender: "user" | "agent";
  text: string;
}

export interface Stats {
  resisted_count: number;
  bought_count: number;
  total_avoided: number;
}

export interface GoalImpact {
  has_goal: boolean;
  goal_impact_ratio: number | null;
  delay_days: number | null;
  note: string;
}

export interface CotStep {
  label: string;
  detail: string;
}

export interface ChatResponse {
  reply: string;
  role: Role;
  intent: IntentType;
  verdict: Verdict | null;
  price: PriceInfo | null;
  impact: GoalImpact | null;
  impulse: ImpulseScore | null;
  opportunity_cost: string[];
  cot_steps: CotStep[];
  suggestions: string[];
  context: ChatContext | null;
  llm_used: boolean;
}

export interface Goal {
  id: number;
  name: string;
  target_amount: number;
  saved_amount: number;
  monthly_saving: number;
  created_at: string;
}

export interface GoalProgress {
  goal: Goal | null;
  progress_ratio: number;
  remaining: number;
  months_to_go: number | null;
}

export interface ChatMessage {
  id: string;
  sender: "user" | "agent";
  text: string;
  response?: ChatResponse;
  /** 流式生成中：此期间只显示文字，分析卡等模型输出完再展示 */
  streaming?: boolean;
  decided?: DecisionAction;
  deposited?: boolean;
}
