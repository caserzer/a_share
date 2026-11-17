# 冻结实验口径

冻结时间：2026-11-17T07:50:24.774613+00:00

{
  "run": "e1_engineered_ablation_20261117",
  "at": "2026-11-17T07:50:24.774613+00:00",
  "old_results_seen": true,
  "new_outcomes_seen": false,
  "model": "original 2021Q4 full78 Ridge bundle fixed throughout; no new fit",
  "sample": "same C universe as past-style-copy; 2021-10-08 signals through 2025-02-28; terminal2025-03-03",
  "scores": "y global-standardized fixed78 then industry demean; p/v are original feature-group contributions after same13style projection. NONE=y-p-v;POS=y-v;RISK=y-p;BOTH=y; STYLE=projection13(y); E1=original changing reference",
  "groups": [
    "range_position",
    "volatility_drawdown"
  ],
  "selection": "same original phase1 dates, proportional industry quotas, ceil(n/5) equal weights, score tie by instrument; no ranking/weight tuning",
  "costs": {
    "main": [
      0.001,
      0.002
    ],
    "zero": [
      0,
      0
    ],
    "stress": [
      0.003,
      0.008
    ]
  },
  "primary": {
    "metric": "annualized mean paired daily net-return contrast, not CAGR difference",
    "contrasts": {
      "position": {
        "BOTH": 0.5,
        "RISK": -0.5,
        "POS": 0.5,
        "NONE": -0.5
      },
      "risk": {
        "BOTH": 0.5,
        "POS": -0.5,
        "RISK": 0.5,
        "NONE": -0.5
      },
      "interaction": {
        "BOTH": 1,
        "POS": -1,
        "RISK": -1,
        "NONE": 1
      }
    },
    "inference": "65day circular block5000 fixedseed; Holm3 two-sided approximate bootstrap p, intervals ordinary descriptive95%"
  },
  "auxiliary": "joint/full-vs-style/simple conditional differences; same-date H10 monthly3block5000; weekly H10 RankIC13block5000; no winner promotion",
  "boundary": "score residualization does not neutralize selected holdings; exact industry quotas only, report style exposure gaps; interaction is nonlinear selection/holding pathway not learned Ridge interaction; Historical-proxy and repeatedly used history, not blind confirmation",
  "attribution": "FULL versus NONE log-linked stock and calendar contributions, accounting not causality",
  "forward": "FORWARD_PENDING"
}
