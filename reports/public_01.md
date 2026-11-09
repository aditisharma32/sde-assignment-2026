# Grade report — public_01_dev

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.369 | +8.0% | 0.252 | +3.1% | 0.507 | +3.0% | 15% | 61 (57) |
| nw_kyc | 0.400 | +9.1% | 0.248 | +2.5% | 0.629 | +5.3% | 29% | 22 (21) |
| nw_renewal | 0.464 | +11.5% | 0.278 | +5.1% | 0.565 | +4.3% | 19% | 52 (54) |
| ALL | 0.407 | +9.5% | 0.260 | +3.7% | 0.551 | +4.0% | 20% | 135 (132) |

## Changes applied by the controller

61 applied — neutral: 43, beneficial: 17, harmful: 1

- ks_cancel v2 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=-0.000 didΔ=+0.000 → **neutral**
- nw_renewal v2 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.008 → **neutral**
- nw_kyc v2 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.059 didΔ=+0.000 → **beneficial**
- ks_cancel v3 (controller_auto) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- nw_renewal v3 (controller_approved) dims=['cohorts', 'welcome_message', 'voice', 'schedule'] engageΔ=+0.053 didΔ=+0.000 → **beneficial**
- nw_kyc v3 (controller_approved) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- nw_renewal v4 (controller_auto) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- ks_cancel v4 (controller_auto) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- ks_cancel v5 (controller_auto) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- nw_kyc v4 (controller_approved) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- nw_renewal v5 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.153 → **beneficial**
- nw_renewal v6 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.156 → **beneficial**
- nw_renewal v7 (controller_auto) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- ks_cancel v6 (controller_auto) dims=['welcome_message', 'schedule'] engageΔ=+0.002 didΔ=+0.000 → **neutral**
- nw_renewal v8 (controller_auto) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- ks_cancel v7 (controller_auto) dims=['welcome_message', 'schedule'] engageΔ=+0.002 didΔ=+0.000 → **neutral**
- nw_kyc v5 (controller_approved) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- ks_cancel v8 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.004 → **neutral**
- ks_cancel v9 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.004 → **neutral**
- ks_cancel v10 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.002 → **neutral**
- ks_cancel v11 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.019 didΔ=+0.000 → **beneficial**
- ks_cancel v12 (controller_auto) dims=['welcome_message', 'voice'] engageΔ=-0.001 didΔ=+0.000 → **neutral**
- ks_cancel v13 (controller_auto) dims=['welcome_message', 'voice', 'caller_id'] engageΔ=-0.001 didΔ=+0.000 → **neutral**
- nw_renewal v9 (controller_approved) dims=['welcome_message', 'schedule'] engageΔ=+0.045 didΔ=+0.000 → **beneficial**
- ks_cancel v14 (controller_auto) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.003 didΔ=+0.000 → **neutral**
- ks_cancel v15 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.002 didΔ=+0.000 → **neutral**
- ks_cancel v16 (controller_auto) dims=['welcome_message', 'voice'] engageΔ=+0.002 didΔ=+0.000 → **neutral**
- ks_cancel v17 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.011 didΔ=+0.000 → **beneficial**
- nw_kyc v6 (controller_approved) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- ks_cancel v18 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=-0.006 didΔ=+0.000 → **neutral**
- nw_renewal v10 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.045 didΔ=+0.000 → **beneficial**
- nw_renewal v11 (controller_auto) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- ks_cancel v19 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=-0.003 didΔ=+0.000 → **neutral**
- ks_cancel v20 (controller_auto) dims=['welcome_message', 'voice', 'caller_id'] engageΔ=+0.000 didΔ=+0.061 → **beneficial**
- nw_kyc v7 (controller_approved) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- ks_cancel v21 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=-0.001 didΔ=+0.000 → **neutral**
- nw_renewal v12 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- nw_kyc v8 (controller_approved) dims=['schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- ks_cancel v22 (controller_auto) dims=['welcome_message', 'voice', 'caller_id'] engageΔ=+0.000 didΔ=+0.056 → **beneficial**
- ks_cancel v23 (controller_auto) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.005 didΔ=+0.000 → **neutral**
- ks_cancel v24 (controller_auto) dims=['welcome_message', 'voice', 'caller_id'] engageΔ=+0.000 didΔ=+0.053 → **beneficial**
- ks_cancel v25 (controller_auto) dims=['voice', 'caller_id'] engageΔ=+0.000 didΔ=+0.050 → **beneficial**
- ks_cancel v26 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.034 → **beneficial**
- nw_renewal v13 (controller_approved) dims=['voice', 'schedule'] engageΔ=-0.005 didΔ=+0.000 → **neutral**
- ks_cancel v27 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.002 didΔ=+0.000 → **neutral**
- nw_renewal v14 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.027 didΔ=+0.000 → **beneficial**
- ks_cancel v28 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.004 didΔ=+0.000 → **neutral**
- nw_kyc v9 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.085 didΔ=+0.000 → **beneficial**
- nw_renewal v15 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=-0.002 didΔ=+0.000 → **neutral**
- nw_renewal v16 (controller_approved) dims=['voice', 'schedule'] engageΔ=+0.006 didΔ=+0.000 → **neutral**
- nw_kyc v10 (controller_approved) dims=['voice', 'schedule'] engageΔ=-0.026 didΔ=+0.000 → **harmful**
- ks_cancel v29 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=-0.001 didΔ=+0.000 → **neutral**
- nw_renewal v17 (controller_approved) dims=['voice', 'schedule'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- ks_cancel v30 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=-0.001 didΔ=+0.000 → **neutral**
- nw_renewal v18 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.009 didΔ=+0.000 → **neutral**
- nw_kyc v11 (controller_approved) dims=['voice', 'schedule'] engageΔ=-0.007 didΔ=+0.000 → **neutral**
- ks_cancel v31 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=-0.002 didΔ=+0.000 → **neutral**
- nw_renewal v19 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.018 didΔ=+0.000 → **beneficial**
- ks_cancel v32 (controller_auto) dims=['welcome_message', 'voice', 'schedule'] engageΔ=-0.002 didΔ=+0.000 → **neutral**
- nw_kyc v12 (controller_approved) dims=['voice', 'schedule'] engageΔ=+0.014 didΔ=+0.000 → **beneficial**
- nw_renewal v20 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.008 didΔ=+0.000 → **neutral**

## Governance

```
{
  "approval_requests": 27,
  "decisions": {
    "approved": 26,
    "rejected": 1,
    "expired": 0
  },
  "rejection_reasons": {
    "approver declined (judgement call)": 1
  },
  "applied_via_approval": 25,
  "auto_applied": 36,
  "auto_apply_rejected": 5,
  "apply_conflicts": 1,
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
[]
```

## Decaying variants — share of in-population calls still on the variant, by day after onset

```
{
  "nw_renewal:welcome_message=W3": {
    "3": 1.0,
    "4": 0.853,
    "5": 0.663,
    "6": 0.482,
    "7": 0.334
  }
}
```

Credits used: 0 · validation runs: 0 · LLM fix calls: 0