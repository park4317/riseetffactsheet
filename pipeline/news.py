# ============================================================
#  뉴스 수집기
#  Primary: Google News RSS (안정적, API키 불필요)
#  Fallback: 네이버 뉴스 검색
# ============================================================

import re
import time
import xml.etree.ElementTree as ET
import urllib.parse
import requests
from datetime import datetime
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup

from config import HEADERS, NEWS_COUNT

# 매크로 뉴스 기본 키워드
# ─ "코스피"로 서킷브레이커·급락·급등 같은 당일 이슈 캡처
# ─ "미국 증시"로 Fed·달러·해외 이벤트 캡처
MACRO_KEYWORDS = [
    "코스피",
    "미국 증시",
]

# 타 운용사 브랜드 - 제목에 있으면 제외
COMPETITOR_BRANDS = [
    "KODEX", "TIGER", "ACE", "HANARO", "KoAct", "ARIRANG",
    "PLUS ETF", "SOL ETF", "KBSTAR",
    "삼성자산", "미래에셋", "한국투자", "신한자산", "NH아문디",
    "키움투자", "한화자산", "배재규",
]

# 종목 뉴스 노이즈 패턴
STOCK_NOISE_PATTERNS = [
    r'지분',
    r'담은',
    r'비중',
    r'따라잡',
    r'쫓지',
    r'올라탔',
    r'사세요',
    r'매수 추천',
    r'버려',
    r'팔자',
    r'편입',       # "삼성전자 편입 ETF"
    r'ETF',        # 종목 뉴스에서 ETF 언급이면 ETF 광고성 기사
    r'담아야',
    r'주목',       # "삼성전자 주목하는 이유" = 추천 기사
]

# RISE ETF 파생상품 접미어 — 이게 붙으면 다른 ETF
_RISE_VARIANT_SUFFIXES = [
    "위클리커버드콜", "커버드콜", "위클리", "레버리지", "인버스",
    "TR", "200TR", "고배당", "밸류업", "바이오", "반도체",
    "소부장", "AI전력", "2차전지", "클라우드", "로봇", "플랫폼",
    "단일종목", "액티브", "헬스케어", "방산", "게임", "K엔터",
]


class NewsCollector:
    """
    Google News RSS 기반 뉴스 수집기
    ETF 뉴스 + 구성종목 뉴스 + 매크로 뉴스 통합 제공
    """

    GOOGLE_RSS    = "https://news.google.com/rss/search"
    NAVER_SEARCH  = "https://search.naver.com/search.naver"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            **HEADERS,
            "Accept": "application/rss+xml,text/html,*/*",
        })

    # ── Google News RSS ────────────────────────────────────
    def search_rss(self, keyword: str, count: int = 5) -> list[dict]:
        params = {
            "q":    keyword,
            "hl":   "ko",
            "gl":   "KR",
            "ceid": "KR:ko",
        }
        try:
            resp = self.session.get(self.GOOGLE_RSS, params=params, timeout=10)
            resp.raise_for_status()
            return self._parse_rss(resp.content, count)
        except Exception as e:
            print(f"  [Google RSS 실패] '{keyword}': {e}")
            return self._search_naver(keyword, count)

    def _is_recent(self, date_str: str, days: int = 7) -> bool:
        if not date_str:
            return True
        try:
            pub = datetime.strptime(date_str, "%Y.%m.%d")
            return (datetime.now() - pub).days <= days
        except Exception:
            return True

    @staticmethod
    def _is_competitor(title: str) -> bool:
        t_upper = title.upper()
        for brand in COMPETITOR_BRANDS:
            if brand.upper() in t_upper:
                return True
        return False

    @staticmethod
    def _is_other_rise_etf(title: str, etf_name: str) -> bool:
        """
        제목이 현재 ETF가 아닌 다른 변형 ETF 제품의 기사인지 확인.
        전략:
          1) etf_name 바로 뒤에 변형 접미어 → 다른 ETF
          2) 제목 어디에든 변형 접미어 존재 → 다른 ETF (현 ETF 이름에 없는 경우)
        """
        # 현재 ETF 이름에 포함된 접미어는 필터에서 제외
        own_suffixes = {s for s in _RISE_VARIANT_SUFFIXES if s.lower() in etf_name.lower()}

        for suffix in _RISE_VARIANT_SUFFIXES:
            if suffix in own_suffixes:
                continue  # 이 ETF 자체의 특성어 → 필터 안 함
            if suffix in title:
                return True  # 다른 ETF 제품어가 제목에 있음

        return False

    @staticmethod
    def _is_relevant_stock_news(title: str, stock_name: str) -> bool:
        """
        종목 뉴스가 해당 종목이 주체인 기사인지 확인.
        1) 종목명이 제목의 앞 50% 이내에 있어야 함 (뒤에만 있으면 부수적 언급)
        2) 노이즈 패턴 없어야 함
        """
        if stock_name not in title:
            return False
        # 제목 앞쪽에 있어야 주체 종목
        idx = title.find(stock_name)
        if idx > len(title) * 0.5:
            return False
        for pat in STOCK_NOISE_PATTERNS:
            if re.search(pat, title):
                return False
        return True

    def _is_url_alive(self, url: str, timeout: int = 3) -> bool:
        """URL이 유효한지 HEAD 요청으로 빠르게 확인"""
        if not url or url.startswith("https://news.google.com"):
            return True  # Google redirect URL은 항상 허용 (검증 불가)
        try:
            r = self.session.head(url, timeout=timeout, allow_redirects=True)
            return r.status_code < 400
        except Exception:
            return False  # 타임아웃/에러 → 제외

    def _parse_rss(self, content: bytes, count: int) -> list[dict]:
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            return []

        channel = root.find("channel")
        if channel is None:
            return []

        articles = []
        for item in channel.findall("item")[:count * 3]:
            title = item.findtext("title", "").strip()
            if " - " in title:
                headline, press = title.rsplit(" - ", 1)
            else:
                headline, press = title, ""

            link = item.findtext("link", "").strip()
            pub  = item.findtext("pubDate", "")
            date = ""
            if pub:
                try:
                    date = parsedate_to_datetime(pub).strftime("%Y.%m.%d")
                except Exception:
                    date = pub[:10]

            src = item.find("source")
            if src is not None and src.text:
                press = src.text.strip()

            if headline and not self._is_competitor(headline):
                articles.append({
                    "title": headline,
                    "url":   link,
                    "press": press,
                    "date":  date,
                    "stock": "",
                })
            if len(articles) >= count:
                break
        return articles

    # ── Naver 검색 (fallback) ────────────────────────────
    def _search_naver(self, keyword: str, count: int) -> list[dict]:
        params = {"where": "news", "query": keyword, "sort": "1"}
        try:
            resp = self.session.get(self.NAVER_SEARCH, params=params, timeout=10)
            soup = BeautifulSoup(resp.text, "lxml")
            articles = []
            for item in soup.select("ul.list_news li.bx")[:count]:
                a = (item.select_one("a.news_tit") or
                     item.select_one("a.api_txt_lines"))
                if not a:
                    continue
                title = a.get_text(strip=True)
                url   = a.get("href", "")
                press_el = item.select_one("a.info.press")
                press = press_el.get_text(strip=True) if press_el else ""
                date  = ""
                for sel in ["span.info", "span.date"]:
                    d = item.select_one(sel)
                    if d:
                        m = re.search(r'\d{4}\.\d{2}\.\d{2}|\d+[시간분일]+ 전',
                                      d.get_text())
                        if m:
                            date = m.group(); break
                if title:
                    articles.append({"title": title, "url": url,
                                     "press": press, "date": date, "stock": ""})
            return articles
        except Exception:
            return []

    # 통합 수집
    def collect_for_etf(self, etf_config: dict,
                        holdings: list[dict] | None = None,
                        include_macro: bool = True) -> dict:
        seen = set()
        etf_name = etf_config.get("name", "")

        def dedup(articles, stock=""):
            out = []
            for a in articles:
                key = a["title"][:30]
                if key not in seen:
                    seen.add(key)
                    a["stock"] = stock
                    out.append(a)
            return out

        # ETF 자체 뉴스 (7일 이내, 최대 3개)
        kw0 = etf_config.get("news_keywords", [""])[0]
        raw_etf = self.search_rss(kw0, count=10)
        etf_news = dedup([
            a for a in raw_etf
            if self._is_recent(a.get("date", ""), days=7)
            and not self._is_other_rise_etf(a["title"], etf_name)
        ])[:2]

        for kw in etf_config.get("news_keywords", [])[1:]:
            if len(etf_news) >= 3:
                break
            raw = self.search_rss(kw, count=5)
            etf_news += dedup([
                a for a in raw
                if self._is_recent(a.get("date", ""), days=7)
                and not self._is_other_rise_etf(a["title"], etf_name)
            ])[:1]
            import time; time.sleep(0.3)

        # 구성종목 뉴스 (상위 3종목, 각 1개)
        stock_news = []
        if holdings:
            import time
            for h in [h for h in holdings[:5]
                      if "현금" not in h.get("name", "")][:3]:
                name = h.get("name", "")
                kw = f'"{name}" 주가 OR "{name}" 실적'
                arts = self.search_rss(kw, count=8)
                relevant = [
                    a for a in arts
                    if self._is_relevant_stock_news(a["title"], name)
                    and self._is_recent(a.get("date", ""), days=7)
                    and not self._is_competitor(a["title"])
                ]
                valid = []
                for a in relevant[:3]:
                    if self._is_url_alive(a["url"]):
                        valid.append(a)
                    if valid:
                        break
                stock_news += dedup(valid, stock=name)[:1]
                time.sleep(0.3)

        # 매크로 뉴스 (3일 이내 당일 이슈 우선)
        macro_news = []
        if include_macro:
            import time
            macro_kws = etf_config.get("macro_keywords", MACRO_KEYWORDS)
            for kw in macro_kws[:3]:
                arts = self.search_rss(kw, count=8)
                recent3 = [a for a in arts if self._is_recent(a.get("date", ""), days=3)]
                recent7 = [a for a in arts if self._is_recent(a.get("date", ""), days=7)]
                pool = recent3 if recent3 else recent7
                macro_news += dedup(pool)[:1]
                time.sleep(0.3)

        return {
            "etf":    etf_news[:3],
            "stocks": stock_news[:3],
            "macro":  macro_news[:2],
        }


# 하위 호환 alias
NaverNewsCollector = NewsCollector
