#!/usr/bin/env python3
"""DCF 기업가치 V 계산 + 할인율 민감도.

예)
  python dcf.py --fcf0 100 --growth 0.08 --rate 0.10 --years 10 --terminal-growth 0.02
  python dcf.py --fcf0 100 --growth 0.03 --rate 0.10 --sensitivity
  python dcf.py --fcf0 100 --growth 0.03 --rate 0.10 --shares 1000 --net-debt 200   # 주당가치
"""
import argparse
import json
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


def dcf(fcf0, growth, rate, years=10, terminal_growth=None):
    """미래 FCF를 할인해 현재가치로 합산. 반환: dict"""
    pv_sum, rows = 0.0, []
    fcf = fcf0
    for n in range(1, years + 1):
        fcf = fcf * (1 + growth)
        pv = fcf / (1 + rate) ** n
        pv_sum += pv
        rows.append({"year": n, "fcf": round(fcf, 2), "pv": round(pv, 2)})
    tv_pv = 0.0
    if terminal_growth is not None and rate > terminal_growth:
        tv = fcf * (1 + terminal_growth) / (rate - terminal_growth)
        tv_pv = tv / (1 + rate) ** years
    value = pv_sum + tv_pv
    return {
        "value": round(value, 2),
        "pv_explicit": round(pv_sum, 2),
        "pv_terminal": round(tv_pv, 2),
        "multiple_of_fcf0": round(value / fcf0, 2) if fcf0 else None,
        "rows": rows,
    }


def gordon_multiple(growth, rate):
    """영구성장 모형의 적정 FCF 배수 1/(r-g)."""
    return None if rate <= growth else round(1.0 / (rate - growth), 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fcf0", type=float, required=True, help="현재 FCF (총액 또는 주당)")
    ap.add_argument("--growth", type=float, default=0.03, help="연 FCF 성장률 (0.03=3%)")
    ap.add_argument("--rate", type=float, default=0.10, help="할인율")
    ap.add_argument("--years", type=int, default=10)
    ap.add_argument("--terminal-growth", type=float, default=None)
    ap.add_argument("--shares", type=float, default=None, help="주식수 (주당가치 환산)")
    ap.add_argument("--net-debt", type=float, default=0.0)
    ap.add_argument("--sensitivity", action="store_true", help="할인율 ±2%p 민감도 표")
    ap.add_argument("--out", default=None, help="JSON 저장 경로")
    a = ap.parse_args()

    base = dcf(a.fcf0, a.growth, a.rate, a.years, a.terminal_growth)
    base["gordon_multiple"] = gordon_multiple(a.growth, a.rate)
    if a.shares:
        base["value_per_share"] = round((base["value"] - a.net_debt) / a.shares, 2)

    print(f"V (현재가치) = {base['value']}  | 명시구간 {base['pv_explicit']} + 터미널 {base['pv_terminal']}")
    print(f"FCF0 대비 배수 = {base['multiple_of_fcf0']}배 | 영구성장 배수 1/(r-g) = {base['gordon_multiple']}배")
    if a.shares:
        print(f"주당가치 = {base['value_per_share']}")

    if a.sensitivity:
        table = []
        for dr in (-0.02, -0.01, 0.0, 0.01, 0.02):
            r = a.rate + dr
            d = dcf(a.fcf0, a.growth, r, a.years, a.terminal_growth)
            table.append({
                "rate": round(r, 4),
                "value": d["value"],
                "chg_pct": round((d["value"] / base["value"] - 1) * 100, 1),
                "gordon_multiple": gordon_multiple(a.growth, r),
            })
        base["sensitivity"] = table
        print("\n할인율 민감도 (V, 변화율, 1/(r-g)):")
        for t in table:
            print(f"  r={t['rate']*100:5.1f}%  V={t['value']:>10}  ({t['chg_pct']:+.1f}%)  배수={t['gordon_multiple']}")

    if a.out:
        with open(a.out, "w") as f:
            json.dump(base, f, ensure_ascii=False, indent=2)
        print(f"\n저장: {a.out}")


if __name__ == "__main__":
    main()
