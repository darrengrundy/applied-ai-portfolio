# Transport CoR Assistant (AU) — design

Working name: **Before the Keys** (alt: CoR Lens, Next Movement).
Rebuild of the UT Austin capstone `transport-cor-multi-agent`, in the pattern of Where's My Stuff?: seeded synthetic data → deterministic engine → Haiku agents + critic → scored evaluation → static demo.

## The question it answers
At 05:30 on a Monday, before the keys change hands: which of the next 48 hours of movements should not leave as planned, why, who in the chain owns the fix, and what patterns in the last four weeks keep producing these problems?

## Fictional operator
Wattlebark Haulage (name searched 2 Nov 2026: no Australian transport business found). Base: Laverton North VIC, base time zone Australia/Melbourne. General freight, steel, building products and palletised retail.
- 36 drivers: 32 standard-hours solo, 2 two-up pairs on Melbourne–Sydney linehaul.
- 30 power units (prime movers + rigids), 34 trailers; GML configurations only (6-axle semi at 43.5/44.0 t; 3-axle rigid).
- 6 customers/consignors (fictional), 4 regular lanes plus local metro work.
- History window: Mon 5 Oct – Sun 1 Nov 2026 (28 days). Snapshot: Mon 2 Nov 2026 05:30 AEDT. Planned movements: Mon 2 – Tue 3 Nov.

## Feeds (synthetic, contracts from the earlier README)
EWD events · telematics (trips, speed events, ignition) · dispatch plan · manifests + weighbridge tickets + JSEA/load plans · restraint (plan, lashing count, equipment inspections, driver competency) · fleet (odometer, service due, defects, workshop bookings) · action register (prior follow-ups).

## Deterministic engine (sole source of facts and numbers)
| Area | Checks | Source |
|---|---|---|
| Fatigue | Standard hours solo: 5.5 h/8 h/11 h/24 h/7 d/14 d windows, night rests; two-up: + 52 h, 60/120 h; projects the planned shift onto history; EWD minute counting, rests <15 min ignored | F1, F2, F4 |
| Mass/dimension | measured vs declared mass, axle-group and combination limits; missing weighbridge/JSEA for heavy or over-dimension loads | M1 + demo procedure |
| Load restraint | lashing count vs LRG table for the load; competency expiry; failed equipment reissued; audit overdue | L1 + demo procedure |
| Speed | events per driver/lane, max over, duration; mapped-limit confidence; follow-up recorded? | demo procedure |
| Maintenance | service due date/km before or during trip; open defects by severity; workshop booking vs dispatch | demo procedure |
| Integrity | vehicle moving while assigned driver on EWD rest; stale feeds; diary edits | demo procedure |

Output: one `FindingPacket` per (movement, rule) with facts, evidence record IDs, rule ID, source ID and severity. Missing evidence produces `INCOMPLETE`, never a pass.

## Traffic-light status (control tower)
Every planned movement, driver and vehicle gets one status. The worst finding wins.
- **Red — stop**: a breach has occurred or the plan would cause one, or the risk is high. Fatigue breach involving the planned shift; mass over limit or declared mass materially under measured; restraint below the LRG table, failed equipment on the load, or no valid competency; service overdue or open major defect; speed 10 km/h or more over, or a repeat pattern with no follow-up; driver identity unresolved (vehicle moved while assigned driver on rest).
- **Amber — watch**: no breach yet, but close or uncertain. Planned shift leaves under 60 min headroom on any fatigue limit; speed under 10 km/h over, especially entering a lower zone (e.g. 80 → 60 transition); service due within 2 days or 1,000 km; competency or audit expiring within 14 days; evidence still to come before departure (weighbridge ticket pending); telematics feed stale.
- **Green — good to go**: all checks run with complete evidence and nothing to watch.
Colour is set by code from the rules; agents explain and assign, they never change the colour. Missing evidence is never green.

## Agents (Claude Haiku 5.5)
1. **Movement analyst** — per flagged movement: decision (HOLD / RESCHEDULE / RELEASE_WITH_CONDITIONS / MONITOR), root cause (fixed taxonomy), accountable CoR party (scheduler, loader/packer, consignor, operator/fleet, driver, executive), next action, plain explanation. May only cite packet facts.
2. **Pattern agent** — over 28 days of findings: systemic issues (e.g. one customer's delivery windows driving speed and fatigue across several drivers). This is the CoR point: the fix is upstream of the driver.
3. **Critic** — checks every claim against packet facts; must name a concrete error to send work back; max 2 revisions (lesson from WISMO run 2).
4. **Briefing writer** — the 05:30 dispatch briefing and executive due-diligence summary.

Rules stay in code (thresholds, legal limits, severity → decision floor). The model does judgement: cause, owner, action, wording.

## Ground truth and storylines
Every storyline is labelled at generation time with expected decision, root cause and accountable party. Negatives and decoys are seeded so precision is measured, not just recall.
1. Fatigue — planned 06:00 start after 23:30 finish (24 h rest short); 7-day 72 h breach if Tuesday shift runs; two-up pair missing 10 h rest in 52 h; root cause: Sydney customer's 06:00 dock window.
2. Mass — one consignor's declared steel weights run 6–9% light against weighbridge; one planned load has no weighbridge ticket.
3. Restraint — competency expired; a webbing strap failed inspection then reissued; a coil load planned with too few lashings for its weight.
4. Speed — driver with repeat events; Geelong lane where five drivers speed on the same stretch (schedule pressure); one false positive from a wrong mapped limit.
5. Maintenance — service due 400 km before a Ballarat run; open brake defect on a planned trailer; workshop booking clashes with dispatch.
6. Integrity — vehicle moves while assigned driver is on rest (undeclared driver swap); telematics feed stale for one unit.
Decoys: legitimate long days within limits, speed event on a correctly mapped road change, heavy load with valid ticket, etc.

## Evaluation
Engine: unit tests per rule including boundary cases (06:29 vs 06:30). Agents: decision accuracy, root-cause accuracy, accountable-party accuracy, HOLD recall (must be 100%), false-hold rate on decoys, critic grounding (unsupported claims), pattern recall, cost and latency. Report run-over-run like WISMO.

## Demo
Keep the current UI shell (briefing, movements, action register, sources). Add: fatigue timeline per driver (work/rest bars, windows, projected shift), evidence trace (packet → analyst → critic), patterns view, eval page. Static HTML, data embedded, no API key needed to view.

## Reference library (for retrieval later)
- `ref/sources.md`: NHVR extracts with retrieval dates (public).
- A third-party Transport JSEA is kept as a private local reference for pre-start and JSEA practice. It is not in this repository and is not quoted or reproduced.
- Planned use: retrieval for explanations and checklists, while hard stops stay in code. Example: on a driver's pre-start vehicle check, a failed horn, headlights, brake lights or indicators is a hard fail (RED) set by a rule; retrieval only supplies the wording and the control ("do not drive until repaired; report the defect").

## Non-goals and limits
Not legal advice; no exemptions, ACH/AFM/BFM, or state-specific rules; no route/access permits beyond GML; synthetic data only; driver identity never inferred from vehicle movement alone.
