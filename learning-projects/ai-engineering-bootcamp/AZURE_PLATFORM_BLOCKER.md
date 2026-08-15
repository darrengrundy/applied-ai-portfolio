# Azure Platform Blocker Audit

**Audit date:** 13 August 2026  
**Affected projects:** Project 2 chat application and Project 3 tools application

## Outcome

The Python implementations are locally available and pass syntax validation, but live testing is blocked because the intended Microsoft Foundry resource rejects language-model deployments during responsible-AI policy validation.

## Verified conditions

- The intended Foundry project and parent Azure AI Services resource exist in East US 2 and report successful provisioning.
- The parent resource exposes the system-managed `Microsoft.Default` and `Microsoft.DefaultV2` responsible-AI policies.
- The Azure model catalog reports support for `gpt-5.2` and `gpt-5-mini` with the `GlobalStandard` SKU.
- The subscription reports unused quota for both models.
- No language-model deployment existed before the fresh tests.

## Deployment attempts

The following deployment paths were tested:

1. `gpt-5.2` version `2025-12-11` through Azure CLI defaults;
2. `gpt-5.2` with `Microsoft.DefaultV2` explicitly assigned through the Azure management API;
3. `gpt-5-mini` version `2025-08-07` through Azure CLI defaults; and
4. `gpt-5-mini` with `Microsoft.DefaultV2` explicitly assigned through the Azure management API.

All four attempts returned the same Azure error class:

```text
InvalidResourceProperties
Failed to validate policies for model <model>/<version>.
```

No deployment was created by any attempt.

## Assessment

The repeated result across two supported models, two deployment interfaces, and explicit use of an available system policy indicates a Foundry resource or Azure platform-policy problem rather than an application-code, quota, model-name, or endpoint error. This aligns with the instructors' warning that these exercises may be affected by a current Microsoft issue.

The portfolio therefore does not claim a successful model response, streaming demonstration, web search, file search, or vector-store workflow. Those tests remain pending until Azure accepts a compatible language-model deployment or the instructors provide a replacement resource.

## Security

Subscription IDs, tenant IDs, endpoint URLs, user identities, and policy resource IDs are intentionally excluded from this record. No keys or secrets were used or stored.

## Update — 15 August 2026

Re-ran diagnostics against Microsoft's own troubleshooting checklist for this error class before concluding it affects Homework 4-6 as well:

- **Reproduced fresh**: a clean `gpt-5-mini/2025-08-07` GlobalStandard deployment attempt (capacity 1, same resource) returned the identical `InvalidResourceProperties: Failed to validate policies for model gpt-5-mini/2025-08-07` error, confirming the issue is still live.
- **Azure Policy ruled out**: no policy assignments exist at the resource-group scope, and the only subscription-scope assignment is the default Security Center audit policy (audit-only, not a deny effect) — so a model-restriction or deployment-type-restriction policy is not the cause.
- **Quota ruled out**: `OpenAI.GlobalStandard.gpt-5-mini` usage in the resource's region sits at 250 of a 2000-unit limit — far from exhausted.
- **Corroborating external report**: this matches an actively open [Microsoft Q&A thread](https://learn.microsoft.com/en-au/answers/questions/5952608/azure-ai-foundry-deployment-fails-with-invalidreso) (August 2026) from other, unrelated users reporting the identical error on new deployments while existing deployments keep working. No Microsoft acknowledgement of root cause or fix timeline exists as of this update, and one affected user reports Microsoft Support was unable to help.

**Conclusion**: this is assessed as a genuine Azure/Foundry platform issue rather than anything fixable from the subscription side. Homework 4-6 are expected to hit the same wall on any new language-model deployment and will be documented the same way — implementation complete, live validation pending — rather than blocked on a fix with no timeline.
