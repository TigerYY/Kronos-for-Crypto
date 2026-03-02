"""
Macro RAG - News Scanner Service (Phase 3)

该模块负责从公开免费的 Crypto 垂直媒体或宏观经济 RSS 源中提取最新的头条新闻与摘要。
提取出的文本将送入本地 Ollama 大语言模型进行语义情感研判（风控熔断）。
"""

import feedparser
import time
import calendar
from typing import List, Dict
from datetime import datetime, timezone

# 推荐的知名高频 Crypto 新闻与全球宏观 RSS 源
CRYPTO_RSS_FEEDS = [
    # 纯 Crypto 垂直
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cryptoslate.com/feed/",
    # 全球宏观经济 (可叠加雅虎财经等)
    "https://finance.yahoo.com/news/rssindex",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?profile=120000000&id=10000664" # CNBC Finance
]

class NewsScanner:
    def __init__(self, feeds: List[str] = None):
        self.feeds = feeds or CRYPTO_RSS_FEEDS
        
    def fetch_latest_news(self, hours_lookback: int = 4) -> List[Dict[str, str]]:
        """
        并发拉取各大 RSS 源中，过去 `hours_lookback` 小时内的重大新闻。
        返回格式: [{'title': '...', 'summary': '...', 'published': '...', 'source': '...'}]
        """
        import concurrent.futures
        
        recent_news = []
        now = datetime.now(timezone.utc).timestamp()
        cutoff_time = now - (hours_lookback * 3600)
        
        def fetch_single_feed(feed_url):
            try:
                # 设置全局 User-Agent 避免某些源屏蔽默认标识
                feedparser.USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                
                # feedparser.parse 在底层使用 urllib，设置 timeout 有点麻烦，
                # 但并发环境下我们可以给整个 future 设置 timeout
                parsed_feed = feedparser.parse(feed_url)
                
                feed_items = []
                for entry in parsed_feed.entries:
                    published_ts = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published_ts = calendar.timegm(entry.published_parsed)
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        published_ts = calendar.timegm(entry.updated_parsed)
                    
                    if published_ts and published_ts >= cutoff_time:
                        title = entry.get('title', '')
                        summary = entry.get('summary', '')
                        summary = self._clean_html(summary)
                        
                        feed_items.append({
                            'title': title,
                            'summary': summary,
                            'published_ts': published_ts,
                            'source': feed_url.split('/')[2]
                        })
                return feed_items
            except Exception as e:
                print(f"[NewsScanner] Error fetching feed {feed_url}: {e}")
                return []

        # 使用线程池并发抓取
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.feeds)) as executor:
            # 设置每条抓取的超时时间为 15 秒
            future_to_url = {executor.submit(fetch_single_feed, url): url for url in self.feeds}
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    data = future.result(timeout=15)
                    recent_news.extend(data)
                except Exception as exc:
                    print(f"[NewsScanner] {url} generated an exception: {exc}")

        # 按时间倒序排序 (最新的在前)
                
        # 按时间倒序排序 (最新的在前)
        recent_news.sort(key=lambda x: x['published_ts'], reverse=True)
        
        # 如果 4h 内没有新闻，自动放宽到 12h 再试一次（避免因偶发无新闻导致空屏）
        if not recent_news and hours_lookback <= 4:
            print("[NewsScanner] No articles in 4h window, retrying with 12h lookback...")
            return self.fetch_latest_news(hours_lookback=12)
            
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
