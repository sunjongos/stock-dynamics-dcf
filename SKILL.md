---
name: stock-dynamics-dcf
description: DCF 가치 V와 감쇠진동 운동방정식(로그가격 x″ = −c·x′ + k·(ln V − x) + ε)을 결합해 주가를 역산·진단하고, 시나리오 가중 몬테카를로로 "얼마나 오를 수 있나"를 확률(상승확률·범위·최대 가능 상승)로 답하며, 워크포워드 백테스트로 예측력을 스스로 검증하는 스킬. 사용자가 '주가 분석', 'DCF', '적정주가', '얼마나 오를까', '상승 여력', '상승확률', '운동방정식', '감쇠비', '선반영', '피크아웃', '컨센서스 역산', '역DCF', '주가 시뮬레이션', '백테스트', 'V_implied', '이 종목 더 오를까' 등을 말하거나 특정 종목·섹터의 주가 흐름 해석을 원하면 반드시 사용한다. 단순 시세 조회에는 쓰지 않는다.
---

# 주식판의 운동방정식 v2 (Stock Dynamics + DCF + 확률 + 자기검증)

v1은 "가치 V를 향해 주가 P가 고무줄처럼 끌려간다"는 설명 틀이었다. v2는 여기에 네 가지를 더한다.
1. **쉬운 말 우선 출력**: 사용자는 전문용어가 아니라 "얼마나 오르나, 얼마나 떨어질 수 있나, 언제 갈리나"를 원한다.
2. **확률로 답하기**: 점 추정이 아니라 시나리오 가중 몬테카를로로 3/6/12개월 수익률 분포·상승확률·경로 중 최대 상승을 낸다.
3. **역DCF 우선**: 진동모델 역산(V_implied)은 노이즈에 약하다. "현재가가 정당화하는 목표연도 EPS"를 1순위 역산으로 쓴다.
4. **자기검증(백테스트 게이트)**: 랜덤워크·모멘텀 기준선을 이기는지 확인하고, 못 이기면 그 사실을 보고서에 적고 기준선 범위를 쓴다.

## 핵심 원리 (변하지 않음)
| 기호 | 물리 | 시장 | 관찰 지표 |
|---|---|---|---|
| V | 고무줄 고정점 | 미래 FCF 기대의 현재가치 (DCF) | 컨센서스 EPS/영업이익 × 적정 배수 |
| k | 복원력 | 괴리(V−P)를 메우려는 저평가 매수세 | 밸류에이션 밴드 회귀 속도 |
| c | 마찰 | 빨리 오를수록 커지는 매도압력 (차익실현·손실회피·포지션 과밀) | 거래대금, 외인·기관 순매도, 회전율 |
| m | 관성 | 방향 바꾸기 어려운 정도 (m=1로 정규화, c/m·k/m만 식별) | 시가총액, 수급 전환 속도 |
| ε | 노이즈 | 뉴스, 지수 리밸런싱, 단기 수급 | — |

- 방향은 V가 정한다. 주가를 미는 것은 실적의 크기가 아니라 **실적 기대가 오르는 속도 V′**다.
- 모양은 마찰 c·복원력 k가 정한다. 감쇠비 ζ = c / 2√k : <0.7 과열형, 0.7~1.3 수렴형, >1.3 추격형, <0 마찰 소멸(버블/투매).
- 고점 신호는 실적 악화가 아니라 **컨센서스 상향 정지**다. 주가 고점은 V 고점보다 1~3개월 늦게 온다.
- 할인율은 V 안에서만 센다(마찰에 넣지 않음). "이미 많이 올랐다"는 마찰이 아니라 괴리 V−P 축소다.

## v2에서 고친 v1의 결함 (실측으로 확인됨)
| v1 | 문제 | v2 |
|---|---|---|
| 가격 수준 회귀 | 주가가 10배 움직이면 추정이 고가 구간에 끌려감 | **로그가격**으로 추정 (스케일 무관) |
| 무제약 OLS | 불안정·폭주 파라미터 | 이산 안정영역 제약 + **랜덤워크 쪽으로 수축(ridge)** — 증거 약하면 자동으로 보수적 |
| 시뮬 초기속도 0 | 현재 모멘텀 무시 | 최근 3기 평균 로그수익률을 초기속도로 |
| 시나리오 4개 선 | "많이 올라봐야 25%"로 오해 | 확률 분포 + **경로 중 최대 상승(max_gain)** + 피크 시점 |
| 노이즈 정규분포 | 급등락 과소평가 | Student-t(df=4) 두꺼운 꼬리 |
| 할인율 임의 | 고베타 종목 과대평가 | CAPM r = rf + β·ERP 를 범위에 반드시 포함 |
| 검증 없음 | 우월성 주장 불가 | `backtest` 워크포워드: 방향적중·80%구간 적중·CRPS |

**실측 검증 결과(2026-10, 가격만으로 V를 대체한 경우)**: NVDA 월간 78구간·6개월 예측 CRPS 0.2665 vs 랜덤워크 0.2676(동률), SK하이닉스 분기 −12.5%(열위). 즉 **동역학 자체에는 가격만으로는 예측 우위가 없다. 우위가 생길 수 있는 유일한 원천은 실제 V(컨센서스 수정) 데이터다.** 그래서 v2는 V 데이터 수집을 최우선으로 하고, V 없이 낸 결과에는 반드시 그 한계를 적는다.

---

## 워크플로

### 0. 스크립트 준비
스킬 폴더의 `scripts/sdx.py`가 있으면 그것을, 없으면 이 문서 맨 끝 코드 블록을 작업 폴더(스크래치패드)에 `sdx.py`로 저장해 쓴다. (`dcf.py`, `dynamics.py`는 v1 레거시. sdx.py가 대체한다.)
의존성: numpy, scipy, matplotlib(그림). 한글 폰트: Noto Sans CJK KR.

### 1. 종목 확인
종목명이 불분명하거나 음성인식 오타 가능성이 있으면(예: "바벨"→마벨) DART/웹 검색으로 확인하고, 그래도 모호하면 **질문 하나**로 확인한다.

### 2. 데이터 수집 (조사 먼저, 계산은 나중)
| 항목 | 수단 | 비고 |
|---|---|---|
| 주가 P (월간, 24~120개월) | 미국/한국 상장: `UsStockInfo-get_historical_stock_prices`(period 2y~10y, interval 1mo; 한국은 `005930.KS` 형식) / `fetch_prices.py`(네트워크 허용 시) | 샌드박스는 yfinance 차단될 수 있음. 도구 출력값을 CSV로 옮김 |
| 현재 지표 | `UsStockInfo-get_stock_info` (forwardPE, beta, 목표주가, 시총) | |
| 최근 실적·가이던스·이벤트 | 웹검색: 회사 IR 보도자료, 인베스터데이 | "오늘 실적"이라 했는데 발표가 없으면 최근 이벤트로 대체하고 그 사실을 명시 |
| **컨센서스 수정 속도 (가장 중요)** | 웹검색: "FY EPS consensus rose from X to Y over 90 days", "upward revisions 30 days", eps trend(현재/7/30/60/90일 전) | 이것이 V′. 못 찾으면 [가정] 표기 |
| 장기 목표 | 회사 장기 가이던스 vs 컨센서스 | 두 값의 차이가 시나리오 폭 |
| 희석·특이요인 | 워런트, 대규모 유증, 자사주 | rdcf `--dilution` |

### 3. V 구성 (우선순위)
1. `values.csv`: 기간별 컨센서스 EPS(차기 회계연도 또는 NTM) × **고정** 적정배수. 수정 이력이 3점 이상이면 보간해 월별로 만든다.
2. `--v0 V --g G`: 현재 V(역DCF 컨센서스 시나리오 값)와 월 상향 속도 G(= V × 월 EPS 수정률). 예: 90일 +9.5% → 월 +3.1%.
3. 아무것도 없으면 가격 추세 프록시 — 진단·백테스트 기준선용일 뿐, **보고서에 "가치 데이터 없음" 경고 필수**.

### 4. 역DCF — 시장이 믿는 미래
```bash
python sdx.py rdcf --price 284.68 --eps1 6.76 --years 4 --eps-cases 12 18 30 --beta 2.26 --rates 0.10 0.11 0.12 0.14 --dilution 0.0
```
- `implied_target_eps`: 현재가가 정당화하는 목표연도 EPS. 컨센서스·회사 목표와 비교 → "회사 목표를 몇 % 믿는 가격인가".
- `value_by_eps`: 시나리오별 주당가치 (V 후보). 할인율 ±1%p 민감도를 함께 보고.
- `capm_rate`: 고베타 종목은 CAPM 할인율에서의 결과를 반드시 한 줄 언급(예: β 2.26 → r≈14% → 현재가는 회사 목표를 거의 전부 믿어야 정당화).

### 5. 동역학 진단
```bash
python sdx.py fit --prices prices.csv --v0 232 --g 7.5          # 또는 --values values.csv
```
출력: c, k, ζ, 유형, 고유주기, 오버슈트%, R², 월변동성, 모멘텀, 가치 괴리%, **부트스트랩 10/50/90% 구간**, 롤링 ζ, 경고(표본·노이즈·국면변화).
ζ 부트스트랩 구간이 0.7~1.3을 가로지르면 유형 판정을 "불확실"로 쓴다.

### 6. 확률 시뮬레이션 — "얼마나 오를까"의 답
```bash
python sdx.py mc --prices prices.csv --v0 232 --g 7.5 --v-now 285 \
  --scenario "회사목표 신뢰|0.45|to:377@12" --scenario "컨센서스 수렴|0.40|to:232@6" --scenario "약세|0.15|to:160@9" \
  --plot fan.png --title "종목 12개월 주가 확률 범위"
```
- 경로 문법: `flat`, `to:V@t`(t개월에 걸쳐 V로), `peak:V1@t1,V2@t2`(피크아웃), `step:V@t`(충격), `lin:g`(월 로그성장).
- 시나리오 확률은 근거와 함께 [가정]으로 명시(애널리스트 의견 분포, 가이던스 달성 이력 등).
- 출력: 기간별 p10/p25/중앙/p75/p90, 기대수익, P(>0%), P(>+20%), P(>+50%), P(<−20%은 100−P(>−20%)), 시나리오별 12개월 중앙값·**경로 중 최대 상승 중앙값**·피크 시점.

### 7. 백테스트 게이트 (가능하면 매번)
```bash
python sdx.py backtest --prices prices_long.csv --h 6 --min-train 36 [--values values.csv]
```
- 60개월 이상 데이터가 있을 때 실행. 결과 `verdict`에 따라 보고서의 확신도를 정한다.
  - **모델 우위**: 확률 범위를 그대로 사용.
  - **동률**: "이 범위는 단순 변동성 수준과 같다 — 방향성 근거는 V(실적 기대)뿐"이라고 쓴다.
  - **열위**: 동역학 결과는 설명용으로만 쓰고, 범위는 랜덤워크/모멘텀 기준선으로 제시.
- 데이터가 짧으면(예: 24개월) "검증 불가"라고 명시한다. 우월성은 **V 데이터로 한 백테스트에서 CRPS가 기준선보다 3% 이상 좋을 때만** 주장한다.

---

## 보고서 형식 (반드시 이 순서)

### ① 쉬운 결론 (전문용어 금지, 5줄 이내)
- "지금 $X. 1년 뒤 가장 그럴듯한 범위는 $A~$B, 중앙값 $M."
- "오를 확률 약 N%, 20% 이상 오를 확률 N%, 20% 이상 떨어질 확률 N%."
- "잘 풀리면 중간에 최고 +N%까지도 가능(경로 중 최대 상승)." ← 12개월 뒤 위치와 **반드시 구분**해서 말한다.
- "방향을 가를 이벤트: (날짜) (무엇이 얼마 이상이면 상승 쪽)."
- "지금 가격은 회사 목표를 약 N% 믿는 가격."

### ② 근거 표 (실측/추정/가정 태그 필수)
최근 실적·가이던스·이벤트 / 컨센서스 수정 속도 / 역DCF 표 / 시나리오·확률.

### ③ 그림
`fan.png`(확률 범위). 필요하면 시나리오별 궤적.

### ④ 전문가용 부록
c, k, ζ(부트스트랩 구간), R², 백테스트 결과, 경고. 그리고 4가지 체크리스트에 순서대로 답한다.
1. **속도 V′**: 컨센서스 월별 수정 폭이 얼마나 가파른가? (양이면 상승 여력, 0이면 격차 소멸)
2. **가속도 V″**: 수정 폭이 커지는가 줄어드는가? (줄어들면 피크아웃 경계)
3. **마찰 c**: 거래대금·순매수가 마찰을 이기고 있나? (c 상승 = 기울기 완만)
4. **괴리**: 역DCF 내재 EPS가 컨센서스보다 높으면 **선반영(경계)**, 낮으면 **덜 반영(상승 여력)**.

### ⑤ 한계 (한 문단)
파라미터는 국면마다 변함 / V는 추정치 / 단기는 노이즈 / 백테스트 결과 / 투자 권유 아님.

**톤 규칙**: 사용자가 "쉽게"를 요구하면 ①만 다시 쓰고 숫자는 반올림한다. "많이 올라봐야 N%?" 같은 반응에는 12개월 중앙값·낙관 범위(p90)·경로 중 최대 상승을 구분해 다시 설명한다. 확률·범위를 말할 때 과장도 축소도 하지 않는다.

## 해석 규칙 (틀리기 쉬운 지점)
- 원래 식 mP″ + cP′ = F_FCF − Friction 은 쓰지 않는다(호재만 있으면 끝없이 오름). 반드시 k(V−P) 복원력 형태.
- "이게 2028년까지 가나?" 같은 지속성 불신은 마찰이 아니라 V 하락 요인(FCF 지속기간 단축)이다.
- 포물선 급등은 마찰이 일시적으로 사라진 짧은 시기(숏스퀴즈·추격매수)다. 추정 c<0이면 이 구간으로 판정하고 "지속 불가, 되돌림 위험"을 쓴다.
- 몇 주 단위 질문에는 "노이즈 지배 구간"임을 먼저 말한다.
- 후향적 적합은 무엇이든 설명한다. 예측은 범위와 확률로만.
- 진동모델의 V_implied(`v_implied_dynamic`)는 부분월 데이터·급변 구간에서 크게 흔들린다. 역DCF와 방향이 다르면 역DCF를 따른다.
- 진행 중인 달(부분월)은 진단에서 빼고 한 번 더 돌려 결과가 뒤집히는지 확인한다.
- 특정 종목 매수·매도 권유가 아니며 투자 판단은 사용자 몫임을 한 문장으로 명시한다.

## 파일 구성
```
stock-dynamics-dcf/
├── SKILL.md              # 이 문서 (v2, 맨 끝에 sdx.py 전체 코드 포함)
├── scripts/
│   ├── sdx.py            # v2 엔진: fit / mc / rdcf / backtest  (없으면 부록 코드로 생성)
│   ├── dcf.py            # v1 레거시: 단일 성장률 DCF·민감도
│   ├── dynamics.py       # v1 레거시: 가격수준 analyze/simulate
│   └── fetch_prices.py   # yfinance 수집 (네트워크 허용 환경 전용)
├── references/
│   ├── theory.md         # 모델 유도, ζ 유형, 종단속도, 격차 c·g/k, 피크아웃, 용어 (이론 질문 시 읽음)
│   └── report-template.md  # v1 템플릿 — v2에서는 위 '보고서 형식'이 우선
└── assets/ sample_prices.csv, sample_values.csv
```

---

## 부록: sdx.py (scripts/sdx.py가 없을 때 이 코드를 저장해 사용)

```python
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
    plt.rcParams["font.family"] = ["Noto Sans CJK KR", "NanumGothic", "DejaVu Sans"]
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
```
