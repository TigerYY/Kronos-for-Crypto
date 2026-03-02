"""
Macro RAG - LLM Analyzer Service (Phase 3)

使用本地 Ollama (OpenAI 兼容接口) 分析聚合的实时头条新闻。
判断当前宏观面是否处于 "EXTREME_BEARISH", "EXTREME_BULLISH" 或 "NEUTRAL"。
"""

import os
import json
import time
import subprocess
from openai import OpenAI

import torch

# 默认使用本地 Ollama 的通用端口
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434/v1")
# 支持用户自定义模型名称 (优先使用更轻量的 1.5b 以避免 Mac GPU 拥堵)
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "deepseek-r1:1.5b")
# Ollama 推理超时时间(秒)，需覆盖冷启动加载模型的时间
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "45"))

class RAGAnalyzer:
    def __init__(self):
        # Ollama 无需真实 API Key，但 openai 库要求此字段不能为空白
        self.client = OpenAI(
            base_url=OLLAMA_API_BASE,
            api_key="ollama-local",
            timeout=OLLAMA_TIMEOUT,  # 覆盖 Ollama 冷启动加载模型的时间
        )
        self.model = OLLAMA_MODEL_NAME

    def analyze_news_sentiment(self, news_items: list) -> dict:
        """
        利用大模型研判新闻并输出严格格式的 JSON 风控指令。
        news_items 结构例如: [{'title': '...', 'summary': '...', 'source': '...'}]
        """
        if not news_items:
            return {"sentiment": "NEUTRAL", "override_signal": "NONE", "reason": "No recent news."}
            
        # 将最新的 15 条新闻拼接成紧凑的上下文 (1.5b 模型推荐更短的 context)
        context = ""
        for idx, item in enumerate(news_items[:15]):
            context += f"{(idx+1)}. [Source: {item.get('source', '')}] {item.get('title', '')} - {item.get('summary', '')}\n"

        system_prompt = """你是一个专业的对冲基金风险管理 AI。
你的唯一任务是监测可能引发系统性风险或重大机会的宏观/加密货币“黑天鹅”事件，并据此判断是否需要对此前的技术交易信号进行人工干预或熔断。

规则：
1. 必须且仅输出 JSON 格式。
2. `events` 数组必须准确包含 12 条简练的新闻摘要，用于 UI 滚动展示。
3. 所有 `text` 字段必须使用简练、专业的 **简体中文**。
4. 严禁在 `text` 中出现完整的英文句子。仅允许保留必要的专业缩写。
5. 顶层的 `sentiment` 必须从 [EXTREME_BEARISH, EXTREME_BULLISH, NEUTRAL, MIXED] 中选择（必须使用英文原词）。
6. 顶层的 `override_signal` 必须从 [SELL, BUY, NONE] 中选择（必须使用英文原词）。
7. 禁止使用占位符文本。

示例格式：
{
  "sentiment": "EXTREME_BEARISH",
  "override_signal": "SELL",
  "reason": "由于美联储加息，市场压力增大。",
  "events": [
    {"text": "美联储宣布加息，市场避险情绪升温", "sentiment": "NEGATIVE"}
  ]
}
"""
        
        user_prompt = f"分析以下过去 4 小时内发生的实时新闻，评估是否需要进行系统干预：\n\n{context}"

        raw_text = ""
        try:
            # 1. Try to get LLM response
            raw_text = self._get_llm_response(system_prompt, user_prompt)
            print(f"[RAGAnalyzer] LLM Success with model {self.model}")
            
            # 2. Parse LLM response
            if "<think>" in raw_text and "</think>" in raw_text:
                parts = raw_text.split("</think>")
                if len(parts) > 1:
                    raw_text = "</think>".join(parts[1:]).strip()

            if raw_text.startswith("```json"):
                raw_text = raw_text.replace("```json", "", 1)
            if raw_text.startswith("```"):
                raw_text = raw_text.replace("```", "", 1)
            raw_text = raw_text.rstrip("`").strip()
                
            if "{" in raw_text and "}" in raw_text:
                start_marker = raw_text.find("{")
                brace_count = 0
                end_marker = -1
                for i in range(start_marker, len(raw_text)):
                    if raw_text[i] == "{":
                        brace_count += 1
                    elif raw_text[i] == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end_marker = i + 1
                            break
                if end_marker != -1:
                    raw_text = raw_text[start_marker:end_marker]

            # Trailing comma cleanup
            raw_text = raw_text.strip()
            if raw_text.endswith(","):
                raw_text = raw_text[:-1]

            try:
                result = json.loads(raw_text, strict=False)
            except:
                raise 
            
            # --- Cleaning: Handle potential invalid control characters in extracted fields ---
            def clean_field(text):
                if not isinstance(text, str): return text
                return "".join(c for c in text if c.isprintable() or c in "\n\r\t")
            
            result["reason"] = clean_field(result.get("reason", ""))
            for e in result.get("events", []):
                e["text"] = clean_field(e.get("text", ""))

            events = result.get("events", [])
            
            # If the LLM returned no events, trigger fallback
            if not events:
                raise ValueError("LLM returned empty event list")
            
            # --- Consistency Check: Ensure sentiment matches the majority of events ---
            pos_count = sum(1 for e in events if e.get("sentiment") == "POSITIVE")
            neg_count = sum(1 for e in events if e.get("sentiment") == "NEGATIVE")
            
            # If LLM says POSITIVE but most events are NEGATIVE, force override
            if result.get("sentiment") in ["POSITIVE", "EXTREME_BULLISH"] and neg_count > pos_count + 2:
                result["sentiment"] = "NEGATIVE"
                result["override_signal"] = "NONE" # Be conservative
            elif result.get("sentiment") in ["NEGATIVE", "EXTREME_BEARISH"] and pos_count > neg_count + 2:
                result["sentiment"] = "POSITIVE"
                result["override_signal"] = "NONE"

            # --- Post-Processing: Language Enforcement ---
            for e in events:
                text = e.get("text", "")
                # If text is mostly English or contains long English phrases, force translation
                # Heuristic: If Chinese characters make up less than 30% of the string and length > 10
                chinese_chars = [char for char in text if '\u4e00' <= char <= '\u9fff']
                if text and (len(chinese_chars) / len(text) < 0.3) and len(text) > 10:
                    # Try to "translate" it using fallback keyword mapping
                    cleaned_text = self._apply_fallback_translation(text)
                    if cleaned_text:
                        e["text"] = cleaned_text
                    else:
                        e["text"] = "全球宏观局势：市场焦点"

            return {
                "sentiment": result.get("sentiment", "NEUTRAL"),
                "override_signal": result.get("override_signal", "NONE"),
                "reason": result.get("reason", ""),
                "events": events
            }

        except Exception as e:
            # Log failure but DO NOT crash
            print(f"[RAGAnalyzer] Analysis failed. Error: {e}")
            if raw_text:
                print(f"[RAGAnalyzer] Raw LLM Text was (first 500 chars): \n---\n{raw_text[:500]}...\n---")
            
            # --- Robust Fallback logic: Use concise Chinese translated titles if LLM fails ---
            fallback_events = []
            pos_count = 0
            neg_count = 0

            if news_items:
                # Basic keyword mapping for fallback Chinese descriptions
                for item in news_items[:12]:
                    title = item.get('title', '')
                    lower_title = title.lower()
                    sentiment = "NEUTRAL"
                    if any(word in lower_title for word in ['surge', 'bloomberg', 'bull', 'adoption', 'approval', 'high', 'buy', 'positive', 'gain', 'jump', 'green']):
                        sentiment = "POSITIVE"
                        pos_count += 1
                    elif any(word in lower_title for word in ['crash', 'hack', 'ban', 'war', 'plunge', 'bear', 'sold', 'negative', 'conflict', 'drop', 'slump', 'red', 'attack']):
                        sentiment = "NEGATIVE"
                        neg_count += 1
                    
                    chinese_text = self._apply_fallback_translation(title, sentiment)
                    if not chinese_text:
                        chinese_text = "宏观市场动态：请关注"
                    
                    fallback_events.append({"text": chinese_text, "sentiment": sentiment})
                
                # If no events at all, dummy
                if not fallback_events:
                    fallback_events = [{"text": "正在整理全球宏观资讯...", "sentiment": "NEUTRAL"}]
            
            # Simple majority vote for fallback
            overall_sentiment = "NEUTRAL"
            if neg_count > pos_count + 1:
                overall_sentiment = "NEGATIVE"
            elif pos_count > neg_count + 1:
                overall_sentiment = "POSITIVE"

            return {
                "sentiment": overall_sentiment, 
                "override_signal": "NONE", 
                "reason": f"分析失败 (已进入自动翻译模式): {str(e)[:50]}", 
                "events": fallback_events
            }

    def _apply_fallback_translation(self, text: str, sentiment: str = "NEUTRAL") -> str:
        """Helper to map English text to concise Chinese headlines based on keywords."""
        lower_text = text.lower()
        kw_map = {
            "fed": "美联储动态", "powell": "鲍威尔讲话", "inflation": "通胀数据", 
            "bitcoin": "比特币行情", "btc": "比特币行情", "crypto": "加密市场动态", 
            "eth": "以太坊动态", "sec": "SEC监管动向", "etf": "ETF最新进展", 
            "war": "局部冲突升级", "cpi": "CPI数据发布", "pce": "PCE数据发布",
            "rate": "利率决议相关", "binance": "币安平台动态", "hack": "安全攻击警报",
            "tesla": "特斯拉动态", "wall street": "华尔街头条", "stock": "美股盘面动态",
            "nvidia": "英伟达行情", "growth": "增长前景分析", "dividend": "分红政策更新",
            "earnings": "财报季数据", "bank": "银行板块动态", "china": "中国市场动态",
            "hk": "香港市场消息", "market": "市场整体走势", "policy": "政策解读相关",
            "bull": "牛市行情走势", "bear": "熊市风险预警", "crash": "市场崩盘预警",
            "surging": "价格大幅飙升", "plunge": "价格大幅下挫", "adoption": "机构收养进展",
            "approval": "监管审批传闻", "listing": "新币上架动态", "solana": "Solana生态焦点",
            "lng": "液化天然气动态", "energy": "能源市场动态", "project": "项目进展动态",
            "exit": "项目退出警惕", "oil": "原油市场分析", "gas": "天然气焦点",
            "japex": "日本能源企业动态", "stake": "质押/股权变动", "venture": "合资/风投动态"
        }
        
        for kw, cn in kw_map.items():
            if kw in lower_text:
                if sentiment == "POSITIVE":
                    return f"{cn}：利好向好"
                elif sentiment == "NEGATIVE":
                    return f"{cn} : 风险预警"
                else:
                    return f"{cn}：市场关注"
        return ""

    def _get_llm_response(self, system_prompt: str, user_prompt: str) -> str:
        """Helper to get response from Ollama via OpenAI API or CLI fallback."""
        if torch.backends.mps.is_available():
            try:
                torch.mps.empty_cache()
            except:
                pass

        last_err = None
        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.0,
                    max_tokens=600,
                    extra_body={"keep_alive": "15m"}
                )
                return response.choices[0].message.content.strip()
            except Exception as inner_e:
                last_err = inner_e
                err_str = str(inner_e).lower()
                # 503, Overloaded, Connection, Timeout are retryable
                if any(k in err_str for k in ["503", "overloaded", "connection", "timeout"]) and attempt < 2:
                    print(f"[RAGAnalyzer] Ollama 繁忙或响应慢 (Attempt {attempt+1}/3), 等待 5s 后重试...")
                    time.sleep(5)
                    continue
                break # Non-retryable or exhausted
        
        # CLI Fallback
        print(f"[RAGAnalyzer] API failed after retries, trying Ollama CLI fallback...")
        try:
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            cmd = ["ollama", "run", self.model, full_prompt]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                raise Exception(f"Ollama CLI failed: {result.stderr}")
        except Exception as cli_e:
            print(f"[RAGAnalyzer] CLI Fallback also failed: {cli_e}")
            raise last_err or cli_e

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
