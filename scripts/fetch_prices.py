#!/usr/bin/env python3
"""월간 주가 CSV 수집 (yfinance). 네트워크가 열린 환경(Claude Code 등) 전용.
샌드박스에서는 실패하므로 그 경우 사용자에게 CSV를 요청하거나 수치를 직접 입력받는다.

  python fetch_prices.py 005930.KS --months 36 --out prices.csv
  python fetch_prices.py 000660.KS --months 24 --out hynix.csv
"""
import argparse
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker", help="예: 005930.KS(삼성전자), 000660.KS(SK하이닉스), NVDA")
    ap.add_argument("--months", type=int, default=36)
    ap.add_argument("--out", default="prices.csv")
    a = ap.parse_args()
    try:
        import yfinance as yf
    except ImportError:
        sys.exit("pip install yfinance --break-system-packages 후 재실행")
    try:
        df = yf.Ticker(a.ticker).history(period=f"{a.months}mo", interval="1mo")
    except Exception as e:  # noqa
        sys.exit(f"수집 실패(네트워크 차단 가능): {e}")
    if df.empty:
        sys.exit("데이터 없음")
    df = df[["Close"]].dropna()
    df.index = df.index.strftime("%Y-%m")
    df.rename(columns={"Close": "price"}).to_csv(a.out, index_label="date")
    print(f"{len(df)}개월 저장: {a.out}")


if __name__ == "__main__":
    main()
