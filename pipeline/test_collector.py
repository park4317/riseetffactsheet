import json
from collector import RISECollector

c = RISECollector("44K4")
data = c.collect_all()

print("\n=== NAV 이력 (최근 3개) ===")
print(json.dumps(data["nav_history"][-3:], ensure_ascii=False, indent=2))

print("\n=== 기간별 수익률 ===")
print(json.dumps(data["performance"], ensure_ascii=False, indent=2))

print("\n=== 구성종목 TOP5 ===")
print(json.dumps(data["holdings"][:5], ensure_ascii=False, indent=2))
