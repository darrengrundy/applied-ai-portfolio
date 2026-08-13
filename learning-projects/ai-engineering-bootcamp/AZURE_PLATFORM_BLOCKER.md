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
