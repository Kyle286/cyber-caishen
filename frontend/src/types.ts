export type Role = "caishen" | "bestie";
export type IntentType = "purchase" | "set_goal" | "query_progress" | "chitchat";
export type Verdict = "discourage" | "encourage" | "neutral";

export interface PriceInfo {
  item: string;
  category: string;
  user_price: number | null;
  avg_price: number;
  lowest_price: number;
  highest_price: number;
  overprice_ratio: number | null;
  comment: string;
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
  cot_steps: CotStep[];
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
}
