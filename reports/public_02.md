# Grade report — public_02_incidents

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.358 | +51.9% | 0.237 | +30.6% | 0.517 | +10.6% | 56% | 69 (348) |
| nw_kyc | 0.361 | -3.4% | 0.241 | +2.8% | 0.575 | -5.4% | -33% | 19 (29) |
| nw_renewal | 0.439 | +1.4% | 0.275 | +4.9% | 0.531 | -4.3% | -20% | 63 (54) |
| ALL | 0.385 | +16.6% | 0.251 | +14.3% | 0.533 | +0.1% | 22% | 151 (431) |

## Changes applied by the controller

76 applied — beneficial: 20, neutral: 51, harmful: 5

- ks_cancel v2 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.017 didΔ=+0.000 → **beneficial**
- nw_renewal v2 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.034 didΔ=+0.000 → **beneficial**
- nw_renewal v3 (controller_auto) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- ks_cancel v3 (controller_auto) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- nw_kyc v2 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=-0.014 didΔ=+0.000 → **harmful**
- ks_cancel v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.003 → **neutral**
- ks_cancel v5 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.003 → **neutral**
- ks_cancel v6 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.002 → **neutral**
- nw_renewal v4 (controller_auto) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- ks_cancel v7 (controller_auto) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- nw_renewal v5 (controller_auto) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- ks_cancel v8 (controller_auto) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- nw_kyc v3 (controller_approved) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- ks_cancel v9 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.054 → **beneficial**
- ks_cancel v10 (controller_auto) dims=['welcome_message', 'caller_id'] engageΔ=+0.000 didΔ=+0.052 → **beneficial**
- ks_cancel v11 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.049 → **beneficial**
- ks_cancel v12 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=-0.010 → **neutral**
- ks_cancel v13 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=-0.006 → **neutral**
- ks_cancel v14 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.220 → **beneficial**
- ks_cancel v15 (controller_auto) dims=['welcome_message', 'schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- ks_cancel v16 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.180 → **beneficial**
- ks_cancel v17 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.076 → **beneficial**
- nw_renewal v6 (controller_approved) dims=['welcome_message', 'schedule'] engageΔ=+0.041 didΔ=+0.000 → **beneficial**
- nw_kyc v4 (controller_approved) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- nw_renewal v7 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.011 → **neutral**
- nw_renewal v8 (controller_auto) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- ks_cancel v18 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- nw_kyc v5 (controller_approved) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- nw_renewal v9 (controller_auto) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- ks_cancel v19 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=-0.002 didΔ=+0.000 → **neutral**
- ks_cancel v21 (controller_approved) dims=['prompt_version'] engageΔ=+0.136 didΔ=+0.000 → **beneficial**
- ks_cancel v22 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.003 didΔ=+0.000 → **neutral**
- nw_renewal v10 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.280 → **beneficial**
- ks_cancel v23 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.005 didΔ=+0.000 → **neutral**
- nw_renewal v11 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.020 → **neutral**
- nw_kyc v6 (controller_approved) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- nw_renewal v12 (controller_approved) dims=['welcome_message', 'schedule'] engageΔ=-0.038 didΔ=+0.000 → **harmful**
- ks_cancel v24 (controller_auto) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.006 didΔ=+0.000 → **neutral**
- nw_renewal v13 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.020 didΔ=+0.000 → **beneficial**
- ks_cancel v25 (controller_auto) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- ks_cancel v26 (controller_auto) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- ks_cancel v27 (controller_auto) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- ks_cancel v28 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- ks_cancel v29 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.005 didΔ=+0.000 → **neutral**
- nw_renewal v14 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=-0.008 didΔ=+0.000 → **neutral**
- ks_cancel v30 (controller_auto) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.005 didΔ=+0.000 → **neutral**
- ks_cancel v31 (controller_auto) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=-0.006 didΔ=+0.000 → **neutral**
- nw_renewal v15 (controller_approved) dims=['voice', 'schedule'] engageΔ=-0.060 didΔ=+0.000 → **harmful**
- nw_renewal v16 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.089 didΔ=+0.000 → **beneficial**
- ks_cancel v32 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=-0.006 didΔ=+0.000 → **neutral**
- ks_cancel v33 (controller_auto) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.004 didΔ=+0.000 → **neutral**
- nw_renewal v18 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=-0.002 didΔ=+0.000 → **neutral**
- ks_cancel v34 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- nw_kyc v7 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=-0.025 didΔ=+0.000 → **harmful**
- ks_cancel v35 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- nw_kyc v8 (controller_approved) dims=['voice', 'schedule'] engageΔ=-0.020 didΔ=+0.000 → **harmful**
- nw_renewal v19 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.035 didΔ=+0.000 → **beneficial**
- ks_cancel v36 (controller_auto) dims=['welcome_message', 'voice', 'caller_id'] engageΔ=+0.000 didΔ=+0.111 → **beneficial**
- ks_cancel v37 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.003 didΔ=+0.000 → **neutral**
- ks_cancel v38 (controller_auto) dims=['welcome_message', 'voice', 'caller_id'] engageΔ=+0.000 didΔ=+0.073 → **beneficial**
- ks_cancel v39 (controller_auto) dims=['welcome_message', 'voice', 'caller_id'] engageΔ=+0.000 didΔ=+0.068 → **beneficial**
- nw_renewal v20 (controller_approved) dims=['voice', 'schedule'] engageΔ=+0.002 didΔ=+0.000 → **neutral**
- ks_cancel v40 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.003 didΔ=+0.000 → **neutral**
- ks_cancel v41 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.058 → **beneficial**
- ks_cancel v42 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.041 → **beneficial**
- nw_renewal v21 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.006 didΔ=+0.000 → **neutral**
- nw_renewal v22 (controller_auto) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- ks_cancel v43 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- nw_kyc v9 (controller_approved) dims=['voice', 'schedule'] engageΔ=-0.004 didΔ=+0.000 → **neutral**
- ks_cancel v44 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.002 didΔ=+0.000 → **neutral**
- nw_renewal v23 (controller_approved) dims=['welcome_message', 'schedule'] engageΔ=-0.003 didΔ=+0.000 → **neutral**
- ks_cancel v45 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- nw_kyc v10 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.059 didΔ=+0.000 → **beneficial**
- nw_renewal v24 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.007 didΔ=+0.000 → **neutral**
- ks_cancel v46 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- nw_renewal v25 (controller_approved) dims=['welcome_message', 'schedule'] engageΔ=+0.001 didΔ=+0.000 → **neutral**

## Governance

```
{
  "approval_requests": 32,
  "decisions": {
    "approved": 26,
    "rejected": 5,
    "expired": 0
  },
  "rejection_reasons": {
    "approver declined (judgement call)": 5
  },
  "applied_via_approval": 26,
  "auto_applied": 50,
  "auto_apply_rejected": 2,
  "apply_conflicts": 0,
  "lapsed": 0,
  "peak_requests_per_24h": {
    "nw_renewal": 3,
    "nw_kyc": 2,
    "ks_cancel": 1
  }
}
```

## Incidents

```
[
  {
    "type": "did_flagged",
    "workflow": "ks_cancel",
    "at": "D2 10:00",
    "flagged_did_share_by_day": {
      "2": 0.088,
      "3": 0.0,
      "4": 0.0,
      "5": 0.0,
      "6": 0.0,
      "7": 0.0,
      "8": 0.0,
      "9": 0.0
    }
  },
  {
    "type": "supervisor_edit",
    "workflow": "ks_cancel",
    "at": "D3 11:30",
    "mttr_minutes": 180,
    "fixed_by": "controller_approved"
  },
  {
    "type": "supervisor_edit",
    "workflow": "nw_renewal",
    "at": "D5 15:00"
  }
]
```

## Decaying variants — share of in-population calls still on the variant, by day after onset

```
{
  "nw_renewal:welcome_message=W3": {
    "2": 0.509,
    "3": 0.505,
    "4": 0.729,
    "5": 0.529,
    "6": 0.453,
    "7": 0.295,
    "8": 0.269,
    "9": 0.259
  }
}
```

Credits used: 18 · validation runs: 6 · LLM fix calls: 2