/** 去掉模型偶发输出的小节标题（与后端 prompts.sanitize_reply 对齐） */
export function sanitizeReply(text: string): string {
  return text
    .replace(/\*{0,2}(?:裁决理由|人格化收尾|财神爷叨叨|闺蜜开怼|理性分析)[：:]*\*{0,2}\s*/g, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
