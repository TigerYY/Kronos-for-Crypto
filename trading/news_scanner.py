"""
Macro RAG - News Scanner Service (Phase 3)

该模块负责从公开免费的 Crypto 垂直媒体或宏观经济 RSS 源中提取最新的头条新闻与摘要。
提取出的文本将送入本地 Ollama 大语言模型进行语义情感研判（风控熔断）。
"""

import feedparser
import time
from typing import List, Dict
from datetime import datetime, timezone

# 推荐的知名高频 Crypto 新闻 RSS 源
CRYPTO_RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
]

class NewsScanner:
    def __init__(self, feeds: List[str] = None):
        self.feeds = feeds or CRYPTO_RSS_FEEDS
        
    def fetch_latest_news(self, hours_lookback: int = 4) -> List[Dict[str, str]]:
        """
        拉取各大 RSS 源中，过去 `hours_lookback` 小时内的重大新闻。
        返回格式: [{'title': '...', 'summary': '...', 'published': '...', 'source': '...'}]
        """
        recent_news = []
        now = datetime.now(timezone.utc).timestamp()
        cutoff_time = now - (hours_lookback * 3600)
        
        for feed_url in self.feeds:
            try:
                # print(f"[NewsScanner] Fetching from {feed_url}...")
                parsed_feed = feedparser.parse(feed_url)
                
                for entry in parsed_feed.entries:
                    # 解析发布时间 (兼容多种格式)
                    published_ts = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published_ts = time.mktime(entry.published_parsed)
                    
                    if published_ts and published_ts >= cutoff_time:
                        title = entry.get('title', '')
                        summary = entry.get('summary', '')
                        # 去除一些冗长的 HTML 标签或无意义的图注
                        summary = self._clean_html(summary)
                        
                        recent_news.append({
                            'title': title,
                            'summary': summary,
                            'published_ts': published_ts,
                            'source': feed_url.split('/')[2]
                        })
            except Exception as e:
                print(f"[NewsScanner] Error fetching feed {feed_url}: {e}")
                
        # 按时间倒序排序 (最新的在前)
        recent_news.sort(key=lambda x: x['published_ts'], reverse=True)
        return recent_news
        
    def _clean_html(self, text: str) -> str:
        """简单清理 RSS Summary 中的基础 HTML 标签"""
        import re
        clean = re.compile('<.*?>')
        text = re.sub(clean, '', text)
        return text.strip()

if __name__ == "__main__":
    scanner = NewsScanner()
    print("Testing News Scanner...")
    news = scanner.fetch_latest_news(hours_lookback=24) # 测试时拉长一点时间
    print(f"Found {len(news)} recent articles.")
    for n in news[:3]: # 展示前3条
        print(f"[{n['source']}] {n['title']}")
        print(f"  > {n['summary'][:100]}...\n")
