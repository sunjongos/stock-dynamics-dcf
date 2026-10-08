#!/usr/bin/env python3
"""주식판의 운동방정식  m·P'' + c·P' = k·(V - P) + ε

서브커맨드
  analyze   : 주가 P, 가치 V 시계열로 c/m, k/m, ζ, V_implied, 격차, 피크아웃 시차 추정
  simulate  : 주어진 c, k, V 경로로 주가 궤적 시뮬레이션 (+PNG)

예)
  python dynamics.py analyze --prices prices.csv --values values.csv --out result.json
  python dynamics.py analyze --prices prices.csv --v0 110 --g 2
  python dynamics.py simulate --c 0.6 --k 0.5 --p0 100 --v-path step:150@5 --months 40 --plot sim.png
  python dynamics.py simulate --c 2 --k 1 --p0 100 --v-path linear:2 --months 40
  python dynamics.py simulate --c 1 --k 0.5 --p0 100 --v-path peak:160@25,130@45 --months 50
  python dynamics.py simulate --c 0.8 --k 0.4 --p0 143 --v-path rate:143->111@5 --months 40

CSV 형식: 첫 열 date, 둘째 열 수치 (헤더 있어도 됨). 월 단위 권장.
"""
import argparse
import csv
import json
import math
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

import numpy as np


# ---------------------------------------------------------------- IO
def read_series(path):
    dates, vals = [], []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            try:
                v = float(str(row[1]).replace(",", ""))
            except ValueError:
                continue  # header
            dates.append(row[0].strip())
            vals.append(v)
    return dates, np.array(vals, dtype=float)


# ---------------------------------------------------------------- 추정
def estimate(P, V):
    """m=1 정규화 후  P''_t = -(c/m) P'_t + (k/m)(V_t - P_t) 를 OLS로 추정.
    t = 1..N-2 (중앙차분)."""
    N = len(P)
    if N < 6:
        raise ValueError("표본이 너무 적습니다 (최소 6개, 권장 12개 이상).")
    dP = P[1:-1] - P[:-2]                      # P'_t  (backward)
    ddP = P[2:] - 2 * P[1:-1] + P[:-2]         # P''_t
    gap = V[1:-1] - P[1:-1]
    X = np.column_stack([-dP, gap])
    beta, *_ = np.linalg.lstsq(X, ddP, rcond=None)
    c_m, k_m = float(beta[0]), float(beta[1])
    resid = ddP - X @ beta
    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((ddP - ddP.mean()) ** 2)) or 1e-12
    r2 = 1 - ss_res / ss_tot
    return c_m, k_m, r2, float(resid.std(ddof=2)) if len(resid) > 2 else float("nan")


def zeta_from(c_m, k_m):
    if k_m <= 0:
        return None
    return c_m / (2 * math.sqrt(k_m))


def classify(z):
    if z is None:
        return "식별불가"
    if z < 0.8:
        return "과열 후 조정형 (ζ<1)"
    if z <= 1.25:
        return "균형 수렴형 (ζ≈1)"
    return "느린 추격형 (ζ>1)"


def v_implied(P, c_m, k_m, window=3):
    """최근 window 구간 평균 속도/가속도로 V_implied = P + (P'' + c/m·P')/(k/m)."""
    if k_m <= 0:
        return None, None, None
    dP = np.diff(P)
    v1 = float(dP[-window:].mean())
    a1 = float(np.diff(dP)[-window:].mean()) if len(dP) > window else 0.0
    vi = float(P[-1] + (a1 + c_m * v1) / k_m)
    return vi, v1, a1


def peak_lag(P, V):
    """V 고점과 P 고점의 시차(개월). V가 단조이면 None."""
    iv, ip = int(np.argmax(V)), int(np.argmax(P))
    if iv in (0, len(V) - 1):
        return None
    return ip - iv


def analyze(args):
    dates, P = read_series(args.prices)
    if args.values:
        _, V = read_series(args.values)
        if len(V) != len(P):
            n = min(len(V), len(P))
            P, V, dates = P[-n:], V[-n:], dates[-n:]
            print(f"[주의] P/V 길이 불일치 → 최근 {n}개로 맞춤", file=sys.stderr)
        v_source = "실측/제공 시계열"
    elif args.v0 is not None:
        t = np.arange(len(P))
        g = args.g or 0.0
        V = args.v0 + g * (t - t[-1])  # 마지막 시점이 v0가 되도록
        v_source = f"선형 근사 V = {args.v0} + {g}·(t−T) [가정]"
    else:
        sys.exit("--values 또는 --v0 (+--g) 가 필요합니다.")

    c_m, k_m, r2, eps_sd = estimate(P, V)
    z = zeta_from(c_m, k_m)
    vi, v1, a1 = v_implied(P, c_m, k_m)
    g_hat = float(np.diff(V)[-3:].mean())  # 최근 기대 상향 속도
    gap_ss = (c_m * g_hat / k_m) if k_m > 0 else None

    warnings = []
    if len(P) < 12:
        warnings.append("표본 부족(<12): 추정치 신뢰 낮음")
    if r2 < 0.3:
        warnings.append(f"R²={r2:.2f} < 0.3: 노이즈(ε) 지배 구간, 해석 주의")
    if k_m <= 0:
        warnings.append("k/m ≤ 0: 복원력 미식별 — V 시계열이 부적절하거나 표본 부족")
    if c_m < 0:
        warnings.append("c/m < 0: 음의 마찰(추격매수 국면?) — 모델 가정 밖")
    # 안정성: 전/후반 분할
    half = len(P) // 2
    if half >= 6 and len(P) - half >= 6:
        try:
            c1, k1, *_ = estimate(P[:half + 1], V[:half + 1])
            c2, k2, *_ = estimate(P[half:], V[half:])
            if k1 > 0 and k2 > 0:
                drift = abs(math.log(max(k2, 1e-9) / max(k1, 1e-9)))
                if drift > math.log(3):
                    warnings.append(f"파라미터 불안정: 전반 k/m={k1:.3f} vs 후반 k/m={k2:.3f}")
        except ValueError:
            pass

    res = {
        "n_obs": int(len(P)),
        "period": [dates[0], dates[-1]] if dates else None,
        "v_source": v_source,
        "c_over_m": round(c_m, 4),
        "k_over_m": round(k_m, 4),
        "zeta": None if z is None else round(z, 3),
        "regime": classify(z),
        "natural_period_months": None if k_m <= 0 else round(2 * math.pi / math.sqrt(k_m), 1),
        "fit_r2": round(r2, 3),
        "residual_std": None if math.isnan(eps_sd) else round(eps_sd, 3),
        "latest_price": float(P[-1]),
        "latest_velocity": None if v1 is None else round(v1, 3),
        "latest_accel": None if a1 is None else round(a1, 3),
        "v_consensus": float(V[-1]),
        "v_implied": None if vi is None else round(vi, 2),
        "premium_pct": None if vi is None else round((vi / V[-1] - 1) * 100, 1),
        "judgement": None,
        "g_recent": round(g_hat, 3),
        "steady_gap": None if gap_ss is None else round(gap_ss, 2),
        "peak_lag_months": peak_lag(P, V),
        "warnings": warnings,
    }
    if vi is not None:
        prem = res["premium_pct"]
        res["judgement"] = ("선반영(경계)" if prem > 5 else
                            "덜 반영(상승 여력)" if prem < -5 else "대체로 반영")

    print(json.dumps(res, ensure_ascii=False, indent=2))
    if args.out:
        with open(args.out, "w") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
    return res


# ---------------------------------------------------------------- 시뮬레이션
def parse_vpath(spec, p0, months):
    t = np.arange(months + 1, dtype=float)
    V = np.full(months + 1, p0, dtype=float)
    kind, _, body = spec.partition(":")
    if kind == "step":                       # step:150@5
        v, at = body.split("@")
        V[int(at):] = float(v)
    elif kind == "linear":                   # linear:2
        V = p0 + float(body) * t
    elif kind == "peak":                     # peak:160@25,130@45
        pts = [(int(a), float(v)) for v, a in (s.split("@") for s in body.split(","))]
        xs = [0] + [a for a, _ in pts]
        ys = [p0] + [v for _, v in pts]
        V = np.interp(t, xs, ys)
    elif kind == "rate":                     # rate:143->111@5
        lvl, at = body.split("@")
        v0, v1 = (float(x) for x in lvl.split("->"))
        V[:] = v0
        V[int(at):] = v1
    else:
        raise ValueError("v-path 형식: step:V@t | linear:g | peak:V1@t1,V2@t2 | rate:V0->V1@t")
    return V


def simulate_path(V, c, k, p0, m=1.0, dt=0.1, noise=0.0, seed=0):
    """반음함수(semi-implicit) 오일러로 ODE 적분. V는 월 단위 배열. dt는 월 분수."""
    rng = np.random.default_rng(seed)
    months = len(V) - 1
    steps = int(months / dt)
    P, vel = p0, 0.0
    out = np.empty(months + 1)
    out[0] = p0
    for i in range(1, steps + 1):
        tm = i * dt
        Vt = np.interp(tm, np.arange(months + 1), V)
        acc = (k * (Vt - P) - c * vel + noise * rng.standard_normal()) / m
        vel += acc * dt
        P += vel * dt
        if abs(tm - round(tm)) < 1e-9 and round(tm) <= months:
            out[int(round(tm))] = P
    return out


def simulate(args):
    V = parse_vpath(args.v_path, args.p0, args.months)
    P = simulate_path(V, args.c, args.k, args.p0, m=args.m, noise=args.noise)
    z = zeta_from(args.c / args.m, args.k / args.m)
    peak = peak_lag(P, V)
    summary = {
        "zeta": round(z, 3) if z else None,
        "regime": classify(z),
        "max_overshoot_pct": round(float((P - V).max() / V.max() * 100), 2),
        "final_gap": round(float(V[-1] - P[-1]), 2),
        "peak_lag_months": peak,
        "P": [round(float(x), 2) for x in P],
        "V": [round(float(x), 2) for x in V],
    }
    print(json.dumps({k_: v_ for k_, v_ in summary.items() if k_ not in ("P", "V")},
                     ensure_ascii=False, indent=2))
    if args.out:
        with open(args.out, "w") as f:
            json.dump(summary, f, ensure_ascii=False)
    if args.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib import font_manager
        _names = {f.name for f in font_manager.fontManager.ttflist}
        for _f in ("NanumGothic", "Noto Sans CJK KR", "Noto Sans CJK JP", "Noto Sans CJK SC", "Malgun Gothic", "AppleGothic"):
            if _f in _names:
                plt.rcParams["font.family"] = _f
                break
        plt.rcParams["axes.unicode_minus"] = False
        t = np.arange(args.months + 1)
        fig, ax = plt.subplots(figsize=(8, 4.2), dpi=130)
        ax.plot(t, V, "--", color="#475569", label="기업가치 V")
        ax.plot(t, P, color="#ea580c", lw=2, label=f"주가 P (c={args.c}, k={args.k}, ζ={summary['zeta']})")
        if peak is not None:
            ax.axvline(int(np.argmax(V)), color="#94a3b8", lw=0.8)
            ax.axvline(int(np.argmax(P)), color="#f97316", lw=0.8)
        ax.set_xlabel("개월"); ax.set_ylabel("가격"); ax.grid(alpha=.3); ax.legend()
        ax.set_title(summary["regime"])
        fig.tight_layout(); fig.savefig(args.plot); print(f"그림 저장: {args.plot}")
    return summary


# ---------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("analyze")
    a.add_argument("--prices", required=True)
    a.add_argument("--values", default=None)
    a.add_argument("--v0", type=float, default=None, help="현재 컨센서스 가치 (values 없을 때)")
    a.add_argument("--g", type=float, default=0.0, help="월별 기대 상향 속도 (values 없을 때)")
    a.add_argument("--out", default=None)
    a.set_defaults(func=analyze)

    s = sub.add_parser("simulate")
    s.add_argument("--c", type=float, required=True)
    s.add_argument("--k", type=float, required=True)
    s.add_argument("--m", type=float, default=1.0)
    s.add_argument("--p0", type=float, required=True)
    s.add_argument("--v-path", required=True)
    s.add_argument("--months", type=int, default=40)
    s.add_argument("--noise", type=float, default=0.0, help="ε 표준편차")
    s.add_argument("--plot", default=None)
    s.add_argument("--out", default=None)
    s.set_defaults(func=simulate)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
