#!/usr/bin/env python3
"""sdx.py — Stock Dynamics eXtended (v2)
로그가격 감쇠진동 모델  x=ln P, u=ln V :  x'' = -(c/m)·x' + (k/m)·(u - x) + ε

서브커맨드
  fit       파라미터 추정(제약 최소제곱) + 부트스트랩 신뢰구간 + 롤링 안정성 + 현재 진단
  mc        몬테카를로: 시나리오(확률 가중) → 3/6/12개월 수익률 분포, 상승확률, 기대수익
  rdcf      역DCF: 현재가가 정당화하는 목표연도 EPS / 성장률 (2단계 모델)
  backtest  워크포워드 검증: 모델 vs 랜덤워크 vs 모멘텀 (방향적중·80%구간 적중·CRPS)

V 입력 (fit/mc/backtest 공통, 우선순위)
  --values v.csv          date,value  (컨센서스 EPS×배수, DCF 등 실제 가치 시계열)
  --v0 V --g G            현재 가치 V와 월 상향 속도 g(가격단위) → 과거로 선형 근사 [가정]
  (둘 다 없으면) 가격추세(EMA --span) 프록시 — 기술적 기준선일 뿐, 가치가 아님 [경고]
CSV: 첫 열 date, 둘째 열 수치. 한 행 = 한 기간(월 권장). 분기 데이터면 --span·--h 등을 기간 단위로 넣는다.
"""
import argparse, csv, json, math, sys, zlib
import numpy as np
from scipy.optimize import lsq_linear, brentq

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

# ------------------------------------------------------------------ IO
def read_series(path):
    d, v = [], []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.reader(f):
            if len(r) < 2: continue
            try: x = float(str(r[1]).replace(",", ""))
            except ValueError: continue
            d.append(r[0].strip()); v.append(x)
    return d, np.array(v, float)

def ema(x, span):
    a, out = 2 / (span + 1), np.empty_like(x); out[0] = x[0]
    for i in range(1, len(x)): out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out

def build_u(args, P, dates=None):
    """로그 가치 경로 u_t 와 출처 라벨."""
    n = len(P)
    if getattr(args, "values", None):
        vd, vv = read_series(args.values)
        m = dict(zip(vd, vv))
        if dates is not None and all(d in m for d in dates):
            V = np.array([m[d] for d in dates])
        else:
            V = np.interp(np.arange(n), np.linspace(0, n - 1, len(vv)), vv)
        return np.log(V), "실측/추정 V 시계열"
    if getattr(args, "v0", None) is not None:
        t = np.arange(n) - (n - 1)
        V = np.maximum(args.v0 + args.g * t, 1e-9)
        return np.log(V), f"선형근사 V={args.v0}+{args.g}·t [가정]"
    x = np.log(P)
    return ema(x, args.span), f"가격추세 프록시(EMA{args.span}) [경고: 가치 아님 — 백테스트 기준선용]"

# ------------------------------------------------------------------ 추정
BOUNDS = ([-0.5, 0.0], [1.9, 1.0])   # 이산 안정영역. c/m<0 허용(마찰 소멸=버블 탐지)
PRIOR = np.array([1.0, 0.0])         # c=1,k=0 → 랜덤워크. 증거가 약하면 여기로 수축
RIDGE = 0.15                         # 수축 강도(표본수 대비). 0이면 순수 OLS

def fit_core(x, u, ridge=None):
    ridge = RIDGE if ridge is None else ridge
    dx = x[1:-1] - x[:-2]; ddx = x[2:] - 2 * x[1:-1] + x[:-2]; gap = u[1:-1] - x[1:-1]
    X = np.column_stack([-dx, gap])
    sx = X.std(0) + 1e-12; lam = math.sqrt(ridge * len(ddx))
    Xa = np.vstack([X, np.diag(lam * sx)]); ya = np.r_[ddx, lam * sx * PRIOR]
    r = lsq_linear(Xa, ya, bounds=BOUNDS)
    c, k = r.x; res = ddx - X @ r.x
    sst = np.sum((ddx - ddx.mean()) ** 2) or 1e-12
    return float(c), float(k), 1 - np.sum(res ** 2) / sst, res

def zeta(c, k): return c / (2 * math.sqrt(k)) if k > 1e-9 else float("inf")

def regime(z):
    if z < 0: return "마찰 소멸(버블/투매) — 추세가 스스로 가속"
    if z < 0.7: return "과열형 — 가치보다 크게 넘쳤다 되돌아옴"
    if z <= 1.3: return "균형 수렴형 — 약간 출렁이며 가치로 수렴"
    return "느린 추격형 — 호재에도 천천히 따라감"

def bootstrap(x, u, B=400, block=3, seed=0):
    c, k, _, res = fit_core(x, u)
    rng = np.random.default_rng(seed); n = len(res); out = []
    for _ in range(B):
        idx = np.concatenate([np.arange(s, s + block) % n for s in rng.integers(0, n, n // block + 1)])[:n]
        e = res[idx]; xs = x.copy()
        for t in range(2, len(x)):
            v = xs[t - 1] - xs[t - 2]
            xs[t] = xs[t - 1] + v + (-c * v + k * (u[t - 1] - xs[t - 1]) + e[t - 2])
        cb, kb, _, _ = fit_core(xs, u); out.append((cb, kb, zeta(cb, kb)))
    a = np.array(out); q = lambda j: [round(float(np.percentile(a[:, j], p)), 3) for p in (10, 50, 90)]
    return {"c_p10_50_90": q(0), "k_p10_50_90": q(1), "zeta_p10_50_90": q(2)}

def rolling(x, u, win):
    out = []
    for s in range(0, len(x) - win + 1, max(1, win // 4)):
        c, k, r2, _ = fit_core(x[s:s + win], u[s:s + win]); out.append(round(zeta(c, k), 2))
    return out

def diagnose(P, u, args):
    x = np.log(P); c, k, r2, res = fit_core(x, u)
    sig = float(res.std(ddof=2)); z = zeta(c, k)
    v_now = float(x[-1] - x[-2]); v_avg = float(np.mean(np.diff(x)[-3:]))
    a_now = float(x[-1] - 2 * x[-2] + x[-3])
    u_impl = x[-1] + (a_now + c * v_now) / k if k > 1e-6 else float("nan")
    warn = []
    if len(P) < 24: warn.append(f"표본 {len(P)}개 — 24개 이상 권장")
    if r2 < 0.3: warn.append(f"R²={r2:.2f} — 노이즈 지배, 방향 판단만 참고")
    if k < 1e-3: warn.append("복원력 k≈0 — V 시계열이 가격을 설명 못함(V 재구성 필요)")
    h = len(x) // 2; c1, k1, _, _ = fit_core(x[:h], u[:h]); c2, k2, _, _ = fit_core(x[h:], u[h:])
    if abs(zeta(c1, k1) - zeta(c2, k2)) > 0.5: warn.append(f"국면 변화: 전반 ζ={zeta(c1,k1):.2f} → 후반 ζ={zeta(c2,k2):.2f} (후반 값 우선)")
    gap_now = float(math.exp(u[-1] - x[-1]) - 1)
    return {
        "c_over_m": round(c, 3), "k_over_m": round(k, 3), "zeta": round(z, 3), "regime": regime(z),
        "natural_period": round(2 * math.pi / math.sqrt(k), 1) if k > 1e-6 else None,
        "overshoot_pct": round(100 * math.exp(-math.pi * z / math.sqrt(1 - z * z)), 1) if 0 <= z < 1 else 0.0,
        "r2": round(r2, 3), "noise_sigma_logpp": round(sig, 4),
        "monthly_vol_pct": round(100 * float(np.diff(x).std()), 1),
        "momentum_logpp": round(v_avg, 4),
        "value_gap_pct": round(100 * gap_now, 1),
        "v_implied_dynamic": round(float(math.exp(u_impl)), 2) if k > 1e-6 else None,
        "price": float(P[-1]), "V_now": round(float(math.exp(u[-1])), 2),
        "warnings": warn,
    }

# ------------------------------------------------------------------ 시뮬레이션
def parse_path(spec, v_now, H):
    """'flat' | 'to:377@12' | 'lin:0.02'(월 로그성장) | 'peak:330@6,260@15' | 'step:203@1'"""
    t = np.arange(H + 1, dtype=float)
    kind, _, body = spec.partition(":")
    if kind == "flat": return np.full(H + 1, v_now)
    if kind == "lin": return v_now * np.exp(float(body) * t)
    if kind in ("to", "peak"):
        pts = [(0, v_now)] + [(int(a), float(v)) for v, a in (p.split("@") for p in body.split(","))]
        xs, ys = zip(*pts); return np.interp(t, xs, ys)
    if kind == "step":
        v, a = body.split("@"); V = np.full(H + 1, v_now); V[int(a):] = float(v); return V
    raise ValueError(spec)

TAIL_DF = 4   # 두꺼운 꼬리(Student-t). 실제 주가 급등락 반영. 0이면 정규분포

def shocks(rng, n):
    if TAIL_DF and TAIL_DF > 2:
        return rng.standard_t(TAIL_DF, n) * math.sqrt((TAIL_DF - 2) / TAIL_DF)
    return rng.standard_normal(n)

def simulate(x0, v0, Vpath, c, k, sig, n, seed=1):
    rng = np.random.default_rng(seed); H = len(Vpath) - 1
    u = np.log(Vpath); X = np.empty((n, H + 1)); X[:, 0] = x0
    xp, vel = np.full(n, x0), np.full(n, v0)
    for t in range(1, H + 1):
        acc = -c * vel + k * (u[t - 1] - xp) + sig * shocks(rng, n)
        vel = vel + acc; xp = xp + vel; X[:, t] = xp
    return X

def mc(args):
    d, P = read_series(args.prices); u, src = build_u(args, P, d)
    dg = diagnose(P, u, args)
    c, k, sig = dg["c_over_m"], dg["k_over_m"], dg["noise_sigma_logpp"]
    if args.c is not None: c = args.c
    if args.k is not None: k = args.k
    x0 = math.log(P[-1]); v0 = dg["momentum_logpp"] * args.momentum_weight
    scen = []
    for s in args.scenario:            # "이름|확률|경로"
        name, p, path = s.split("|"); scen.append((name, float(p), path))
    tot = sum(p for _, p, _ in scen); scen = [(a, p / tot, b) for a, p, b in scen]
    H = max(args.horizons); allr = {h: [] for h in args.horizons}; table = []
    for name, p, path in scen:
        V = parse_path(path, args.v_now or math.exp(u[-1]), H)
        X = simulate(x0, v0, V, c, k, sig, max(200, int(args.n * p)), seed=zlib.crc32(name.encode()) % 9999)
        row = {"scenario": name, "prob": round(p, 3), "V_end": round(float(V[-1]), 1)}
        for h in args.horizons:
            r = np.exp(X[:, h] - x0) - 1; allr[h].append(r)
            row[f"{h}m_median_pct"] = round(100 * float(np.median(r)), 1)
        pk = np.exp(X.max(1) - x0) - 1; row["max_gain_median_pct"] = round(100 * float(np.median(pk)), 1)
        row["peak_month_median"] = int(np.median(X.argmax(1)))
        table.append(row)
    summ = {}
    for h in args.horizons:
        w = np.concatenate([np.repeat(r, 1) for r in allr[h]])
        wt = np.concatenate([np.full(len(r), p / len(r)) for r, (_, p, _) in zip(allr[h], scen)])
        o = np.argsort(w); cw = np.cumsum(wt[o]) / wt.sum()
        pct = lambda q: round(100 * float(w[o][np.searchsorted(cw, q)]), 1)
        summ[f"{h}m"] = {"p10": pct(.10), "p25": pct(.25), "median": pct(.5), "p75": pct(.75), "p90": pct(.9),
                         "expected": round(100 * float(np.sum(w * wt) / wt.sum()), 1),
                         **{f"P(>{t:+d}%)": round(100 * float(wt[w > t / 100].sum() / wt.sum()), 1) for t in args.thresholds}}
    out = {"v_source": src, "diagnosis": dg, "params_used": {"c": c, "k": k, "sigma": sig, "v0": round(v0, 4)},
           "scenarios": table, "distribution": summ}
    if args.plot: fan_plot(x0, scen, args, c, k, sig, v0, u, H, P)
    return out

def fan_plot(x0, scen, args, c, k, sig, v0, u, H, P):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = ["Malgun Gothic", "NanumGothic", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    Xs = []
    for name, p, path in scen:
        V = parse_path(path, args.v_now or math.exp(u[-1]), H)
        Xs.append(simulate(x0, v0, V, c, k, sig, max(200, int(args.n * p)), seed=zlib.crc32(name.encode()) % 9999))
    X = np.vstack(Xs); Pm = np.exp(X); t = np.arange(H + 1)
    fig, ax = plt.subplots(figsize=(10, 5.2))
    hist = P[-min(len(P), 24):]; th = np.arange(-len(hist) + 1, 1)
    ax.plot(th, hist, color="#333", lw=1.8, label="실제 주가")
    for lo, hi, a in ((10, 90, .15), (25, 75, .3)):
        ax.fill_between(t, np.percentile(Pm, lo, 0), np.percentile(Pm, hi, 0), color="#2563eb", alpha=a,
                        label=f"{lo}~{hi}% 범위")
    ax.plot(t, np.median(Pm, 0), color="#2563eb", lw=2, label="중앙값")
    ax.axhline(P[-1], color="gray", lw=.8, ls="--")
    ax.set_xlabel("개월 (0 = 현재)"); ax.set_ylabel("주가"); ax.grid(alpha=.3); ax.legend(fontsize=8, loc="upper left")
    ax.set_title(args.title or "주가 확률 범위 (시나리오 가중 몬테카를로)")
    plt.tight_layout(); plt.savefig(args.plot, dpi=130)

# ------------------------------------------------------------------ 역DCF
def two_stage(eps_target, eps1, yrs, r, tg, fade, g_cap, dil):
    g1 = (eps_target / eps1) ** (1 / max(yrs - 1, 1)) - 1
    path = [eps1 * (1 + g1) ** i for i in range(yrs)]; e = path[-1]; g0 = min(g1, g_cap)
    for j in range(1, fade + 1): e *= 1 + g0 + (tg - g0) * j / fade; path.append(e)
    pv = sum(v / (1 + r) ** (i + 1) for i, v in enumerate(path))
    tv = path[-1] * (1 + tg) / (r - tg) / (1 + r) ** len(path)
    return (pv + tv) * (1 - dil)

def rdcf(a):
    f = lambda e, r: two_stage(e, a.eps1, a.years, r, a.tg, a.fade, a.g_cap, a.dilution)
    out = {"price": a.price, "implied_target_eps": {}, "value_by_eps": {}}
    for r in a.rates:
        try: out["implied_target_eps"][f"r={r:.0%}"] = round(brentq(lambda e: f(e, r) - a.price, a.eps1 * 0.2, a.eps1 * 200), 2)
        except ValueError: out["implied_target_eps"][f"r={r:.0%}"] = None
    for e in a.eps_cases:
        out["value_by_eps"][f"EPS {e}"] = {f"r={r:.0%}": round(f(e, r), 1) for r in a.rates}
    if a.beta is not None:
        out["capm_rate"] = round(a.rf + a.beta * a.erp, 4)
    return out

# ------------------------------------------------------------------ 백테스트
def crps_sample(samples, y):
    s = np.sort(samples); n = len(s)
    return float(np.mean(np.abs(s - y)) - np.sum((2 * np.arange(1, n + 1) - n - 1) * s) / (n * n))

def backtest(a):
    d, P = read_series(a.prices); x = np.log(P); n = len(x); h = a.h
    rows = {"model": [], "rw": [], "mom": []}
    for t in range(a.min_train, n - h):
        Ptr = P[:t + 1]; u, _ = build_u(a, Ptr, d[:t + 1])
        c, k, r2, res = fit_core(x[:t + 1], u); sig = float(res.std(ddof=2))
        v0 = float(np.mean(np.diff(x[:t + 1])[-3:])) * a.momentum_weight
        slope = (u[-1] - u[-1 - min(6, len(u) - 1)]) / min(6, len(u) - 1) if a.v_extrap else 0.0
        V = np.exp(u[-1] + slope * np.arange(h + 1))
        S = simulate(x[t], v0, V, c, k, sig, 600, seed=t)[:, h] - x[t]
        dr = np.diff(x[:t + 1]); vol = dr[-a.vol_win:].std()
        RW = np.random.default_rng(t).normal(0, vol * math.sqrt(h), 600)
        mu = dr[-12:].mean() * h
        MOM = np.random.default_rng(t + 1).normal(mu, vol * math.sqrt(h), 600)
        y = x[t + h] - x[t]
        for key, s in (("model", S), ("rw", RW), ("mom", MOM)):
            lo, hi = np.percentile(s, [10, 90])
            rows[key].append((np.sign(np.median(s)) == np.sign(y), lo <= y <= hi, crps_sample(s, y), abs(np.median(s) - y)))
    rep = {}
    for key, r in rows.items():
        r = np.array(r, float)
        rep[key] = {"n": len(r), "direction_hit_pct": round(100 * r[:, 0].mean(), 1),
                    "coverage80_pct": round(100 * r[:, 1].mean(), 1), "crps": round(r[:, 2].mean(), 4),
                    "mae_logret": round(r[:, 3].mean(), 4)}
    best = min(rep["rw"]["crps"], rep["mom"]["crps"]); edge = 100 * (best - rep["model"]["crps"]) / best
    rep["crps_edge_vs_best_baseline_pct"] = round(edge, 1)
    rep["verdict"] = ("모델 우위(CRPS 3%↑ 개선)" if edge > 3 else
                      "사실상 동률 — 기준선과 구분 불가" if edge > -3 else "모델 열위 — 이 종목/V로는 쓰지 말 것")
    return rep

# ------------------------------------------------------------------ CLI
def add_v(p):
    p.add_argument("--values"); p.add_argument("--v0", type=float); p.add_argument("--g", type=float, default=0.0)
    p.add_argument("--span", type=int, default=12)

def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    f = sp.add_parser("fit"); f.add_argument("--prices", required=True); add_v(f)
    f.add_argument("--boot", type=int, default=300); f.add_argument("--win", type=int, default=18)
    m = sp.add_parser("mc"); m.add_argument("--prices", required=True); add_v(m)
    m.add_argument("--scenario", action="append", required=True, help="'이름|확률|경로' 예: '강세|0.45|to:377@12'")
    m.add_argument("--v-now", type=float, help="시나리오 시작 V (기본: 추정 V 최신값)")
    m.add_argument("--horizons", type=int, nargs="+", default=[3, 6, 12])
    m.add_argument("--thresholds", type=int, nargs="+", default=[0, 20, 50, -20])
    m.add_argument("--n", type=int, default=6000); m.add_argument("--c", type=float); m.add_argument("--k", type=float)
    m.add_argument("--momentum-weight", type=float, default=1.0); m.add_argument("--plot"); m.add_argument("--title")
    r = sp.add_parser("rdcf"); r.add_argument("--price", type=float, required=True)
    r.add_argument("--eps1", type=float, required=True, help="다음 회계연도 컨센서스 EPS")
    r.add_argument("--years", type=int, default=4, help="eps1 해부터 목표연도까지 연수(포함)")
    r.add_argument("--rates", type=float, nargs="+", default=[0.09, 0.10, 0.11, 0.12, 0.13])
    r.add_argument("--eps-cases", type=float, nargs="*", default=[])
    r.add_argument("--tg", type=float, default=0.03); r.add_argument("--fade", type=int, default=6)
    r.add_argument("--g-cap", type=float, default=0.15); r.add_argument("--dilution", type=float, default=0.0)
    r.add_argument("--beta", type=float); r.add_argument("--rf", type=float, default=0.042); r.add_argument("--erp", type=float, default=0.045)
    b = sp.add_parser("backtest"); b.add_argument("--prices", required=True); add_v(b)
    b.add_argument("--h", type=int, default=6); b.add_argument("--min-train", type=int, default=36)
    b.add_argument("--vol-win", type=int, default=24); b.add_argument("--momentum-weight", type=float, default=1.0)
    b.add_argument("--v-extrap", action="store_true", help="V의 최근 6기 기울기를 앞으로 연장")
    b.add_argument("--ridge", type=float, default=None); b.add_argument("--tail-df", type=float, default=None)
    a = ap.parse_args()
    global RIDGE
    if getattr(a, "ridge", None) is not None: RIDGE = a.ridge
    global TAIL_DF
    if getattr(a, "tail_df", None) is not None: TAIL_DF = a.tail_df
    if a.cmd == "fit":
        d, P = read_series(a.prices); u, src = build_u(a, P, d); x = np.log(P)
        out = {"v_source": src, "diagnosis": diagnose(P, u, a), "bootstrap": bootstrap(x, u, a.boot),
               "rolling_zeta": rolling(x, u, min(a.win, len(x) - 2))}
    elif a.cmd == "mc": out = mc(a)
    elif a.cmd == "rdcf": out = rdcf(a)
    else: out = backtest(a)
    print(json.dumps(out, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
