"""
Macro RAG - LLM Analyzer Service (Phase 3)

使用本地 Ollama (OpenAI 兼容接口) 分析聚合的实时头条新闻。
判断当前宏观面是否处于 "EXTREME_BEARISH", "EXTREME_BULLISH" 或 "NEUTRAL"。
"""

import os
import json
from openai import OpenAI

# 默认使用本地 Ollama 的通用端口
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434/v1")
# 支持用户自定义模型名称 (qwen2.5, qwen2.5-coder, deepseek-coder 等)
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "deepseek-coder:6.7b")

class RAGAnalyzer:
    def __init__(self):
        # Ollama 无需真实 API Key，但 openai 库要求此字段不能为空白
        self.client = OpenAI(
            base_url=OLLAMA_API_BASE,
            api_key="ollama-local" 
        )
        self.model = OLLAMA_MODEL_NAME

    def analyze_news_sentiment(self, news_items: list) -> dict:
        """
        利用大模型研判新闻并输出严格格式的 JSON 风控指令。
        news_items 结构例如: [{'title': '...', 'summary': '...', 'source': '...'}]
        """
        if not news_items:
            return {"sentiment": "NEUTRAL", "override_signal": "NONE", "reason": "No recent news."}
            
        # 将最新的 10 条新闻拼接成紧凑的上下文
        context = ""
        for idx, item in enumerate(news_items[:10]):
            context += f"{(idx+1)}. [Source: {item.get('source', '')}] {item.get('title', '')} - {item.get('summary', '')}\n"

        system_prompt = """You are a strictly logical hedge fund risk-management AI.
Your ONLY job is to detect Black Swan macro/crypto events that justify overriding an active technical trading system, AND summarize the headlines into short, punchy 3-8 word phrases in CHINESE (e.g., "美联储加息", "币安被黑", "中东局部冲突", "ETF获批").

You MUST reply IN JSON FORMAT exactly matching this structure, and NOTHING ELSE:
{
  "sentiment": "EXTREME_BEARISH" | "EXTREME_BULLISH" | "NEUTRAL" | "MIXED", 
  "override_signal": "SELL" | "BUY" | "NONE",
  "reason": "Brief english reason if not neutral, else Empty",
  "events": [
    {"text": "Short Chinese summary of event", "sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL"}
  ]
}

RULES:
- Respond ONLY with JSON. No markdown backticks, no extra text.
- Be extremely conservative on overrides. 99% of news is NEUTRAL/MIXED with NONE. 
- EXTREME_BEARISH is ONLY for market crashes, bans, hacks, war breaks out. override_signal -> SELL.
- EXTREME_BULLISH is ONLY for massive ETF approvals, sovereign adoption. override_signal -> BUY.
- For mixed, uncertain, or normal news, choose NEUTRAL or MIXED and NONE.
- `events` should be a concise list of major themes found in the context, translate them to Chinese. If no news, return an empty list.
"""
        
        user_prompt = f"Analyze the following immediate news breaking in the last 4 hours and evaluate the macro necessity for a system override:\n\n{context}"

        try:
            # print(f"[RAGAnalyzer] Sending prompt to local Ollama ({self.model})...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0, # We want deterministic logic
                max_tokens=400
            )
            
            # 兼容不同模型的输出习惯，清理可能附带的 ```json 标签
            raw_text = response.choices[0].message.content.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.replace("```", "").strip()
                
            result = json.loads(raw_text)
            
            # 格式硬防呆保证系统不崩
            return {
                "sentiment": result.get("sentiment", "NEUTRAL"),
                "override_signal": result.get("override_signal", "NONE"),
                "reason": result.get("reason", ""),
                "events": result.get("events", [])
            }
            
        except Exception as e:
            print(f"[RAGAnalyzer] Ollama inference failed: {e}")
            return {"sentiment": "NEUTRAL", "override_signal": "NONE", "reason": f"LLM Error: {str(e)}"}

if __name__ == "__main__":
    import sys
    ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    
    from trading.news_scanner import NewsScanner
    import pprint
    
    print("--- 1. Fetching News ---")
    scanner = NewsScanner()
    news = scanner.fetch_latest_news(hours_lookback=24)
    print(f"Found {len(news)} articles.")
    
    print("\n--- 2. Injecting into Local Ollama RAG ---")
    rag = RAGAnalyzer()
    decision = rag.analyze_news_sentiment(news)
    
    print("\n--- 3. LLM Risk Management Decision ---")
    pprint.pprint(decision)
