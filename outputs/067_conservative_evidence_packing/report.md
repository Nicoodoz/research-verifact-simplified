# 067：Conservative Requirement-Preserving Evidence Packing

## 主结果

| Method | Correct | PA | MCC | false-S | S / NS / NA recall |
|---|---:|---:|---:|---:|---|
| Baseline T-S+PriorG | 198/236 | 83.90% | 0.5946 | 6 | 89.30% / 38.89% / 77.42% |
| 067 Conservative Pack + T-S+PriorG | 199/236 | 84.32% | 0.5819 | 10 | 90.91% / 50.00% / 64.52% |

- Paired rescue / harm / net: **14 / 13 / +1**.
- Patient wins / losses / ties: **6 / 6 / 12**.
- Changed packs: 226/236; additions=424, drops=0; invalid final Judge fallback=0.
- Mean character increase among changed packs: 1277.7.
- API: 705 attempts, 705 HTTP200, cost about ¥20.7336.

## Preregistered criteria

{
  "net_correct_ge_3": false,
  "delta_MCC_ge_0.015": false,
  "falseS_nonincrease": false,
  "NS_drop_le_0.02": true,
  "NA_drop_le_0.02": false,
  "rescue_patients_ge_3": true,
  "patient_wins_gt_losses": false
}

**Advance = False.**

## Bootstrap

{
  "B": 1000,
  "delta_PA_mean": 0.004343949600196322,
  "delta_PA_ci": [
    -0.03797870628620477,
    0.042923079769128396
  ],
  "delta_MCC_mean": -0.010501735112034699,
  "delta_MCC_ci": [
    -0.10122834501725139,
    0.09357524147215852
  ],
  "delta_falseS_mean": 3.976,
  "delta_falseS_ci": [
    0.0,
    9.0
  ]
}

## Addition roles

{
  "all": {
    "direct_support": 246,
    "event_state": 41,
    "temporal": 46,
    "scope": 32,
    "direct_contradiction": 24,
    "numeric_or_trend": 26,
    "negation": 4,
    "certainty": 5
  },
  "rescue": {
    "direct_contradiction": 6,
    "scope": 3,
    "direct_support": 14,
    "event_state": 2,
    "temporal": 2
  },
  "harm": {
    "direct_support": 11,
    "temporal": 3,
    "numeric_or_trend": 4,
    "event_state": 7,
    "scope": 1
  }
}

## Boundary

- 067 decisions are GT-blind and evaluated on 052, a different claim batch from the 066 oracle diagnosis.
- 052 is still development, not an external confirmation set.
- No retrieval outside frozen C48 is introduced; Frozen PriorG is unchanged.
