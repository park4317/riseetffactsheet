"""
전체 데이터 수집 테스트
실행: python test_full_collect.py
"""
import json
from collector import RISECollector
from news import NaverNewsCollector
from config import ETF_LIST

ETF_NAME = "RISE 현대차고정피지컬AI"
cfg = ETF_LIST[ETF_NAME]

print("=" * 60)
print(f"  {ETF_NAME} 전체 데이터 수집 테스트")
print("=" * 60)

# ── 1. RISE 사이트 수집
collector = RISECollector(cfg["site_id"])
data = collector.collect_all()

# ── 결과 출력
print("\n[1] NAV 이력 (최근 5일)")
for r in data["nav_history"][-5:]:
    print(f"  {r['date']}  NAV:{r['nav']:>10,.2f}  가격:{str(r['price']):>8}  거래량:{str(r['volume']):>12}")

print(f"\n[2] BM: {data['bm_name']} ({len(data['bm_history'])}일치)")
for r in data["bm_history"][-3:]:
    print(f"  {r['date']}  종가:{r['close']:>10,.2f}")

print("\n[3] 기간별 수익률")
perf = data["performance"]
for k, v in perf.items():
    val = f"{v:+.2f}%" if v is not None else "—"
    print(f"  {k:>15}: {val}")

print(f"\n[4] 구성종목 ({len(data['holdings'])}개)")
for h in data["holdings"]:
    mkt = h.get("market", "?")
    sec = h.get("sector", "?")
    print(f"  {h['rank']:>2}. {h['name']:<12} {mkt:<8} {sec:<15} {h['weight']:.2f}%")

print(f"\n[5] 업종별 비중 ({len(data['sector_data'])}개 업종)")
for s in data["sector_data"]:
    bar = "█" * int(s["weight"] / 3)
    print(f"  {s['sector']:<15} {s['weight']:5.1f}%  {bar}")

print(f"\n[6] 20일 평균 거래량: {data['avg_volume_20d']:,}주" if data['avg_volume_20d'] else "\n[6] 거래량 데이터 없음")

# ── 2. 뉴스 수집
print("\n[7] 뉴스 수집 중...")
nc = NaverNewsCollector()
news = nc.collect_for_etf(cfg, holdings=data["holdings"])
data["news"] = news
for i, n in enumerate(news, 1):
    stock = f"[{n['stock']}] " if n.get("stock") else ""
    print(f"  {i}. {stock}{n['title'][:45]}...")
    print(f"     {n['press']} · {n['date']}")

print("\n" + "=" * 60)
print("  ✅ 수집 완료!")
print(f"  표시 수익률: {data['display_return_label']} {data['display_return']}%")
print("=" * 60)
