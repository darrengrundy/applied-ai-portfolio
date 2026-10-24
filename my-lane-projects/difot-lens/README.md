# DIFOT Lens — freight service and cost, made visible

> A data pipeline and interactive map that turn a carrier's raw consignment export into DIFOT (delivered in full, on time), cost-to-serve and root-cause signals. Every consignment can be watched moving across Australia, and every number traces back to deterministic code. It's the visual and metrics foundation for a multi-agent root-cause analysis system.

**Demo:** open [`demo/index.html`](demo/index.html) in a browser.
**Data:** fully synthetic. *Banksia Trade Supply Co.* is a fictitious wholesaler; only the geography (Australian suburbs and postcodes) is real.

![Freight flow](docs/screenshot-flow.png)

## Project status

**Status:** Working prototype (visual layer and metrics engine). The agent layer is designed but not built yet; see [Roadmap](#roadmap).
**Context:** My Lane AI. The prototype was built on a real national distribution network's carrier data, then re-created here with synthetic data at double the volume so it can be shared.

## Problem

Most transport teams get a monthly DIFOT number and a spreadsheet of carrier invoices. Neither tells you *where* service is breaking, *when* it started, or *why*. The carrier's consignment export already holds the answer for most of it: dispatch date, promised ETA, delivered date, origin, destination, weight and charge. It's just 300,000 rows nobody has time to read.

## What it shows

| View | What you see |
|---|---|
| **States** | 3D state map, weekly time-lapse. Height = consignment volume; colour = DIFOT, cost per shipment or cost per kg. Click a state to drill in. |
| **Freight flow** | One glowing trail per consignment, moving from dispatch to its *actual* delivery date. Blue on time, red late, white not yet delivered. Daily counters for in transit, delivered and % late. |
| **Postcodes** | 1 sphere = 1 consignment, piled at its delivery postcode, week by week. The glow under each pile shows that postcode's DIFOT; the side panel lists the worst postcodes. |
| **Trends** | National and per-state DIFOT; cost per shipment, per kg and per km; average distance. |
| **Root-cause signals** | How late failures are, DIFOT by promised transit time, origin site, remoteness, ETA weekday, and volume vs DIFOT, with auto-written callouts. |
| **Agent design** | The planned multi-agent RCA architecture. |

![Postcode piles](docs/screenshot-points.png)

## What the demo data contains

The generator builds a year (5 Jan – 23 Oct 2026) of 318k consignments from three east-coast DCs (Larapinta QLD, Eastern Creek NSW, Truganina VIC) to about 1,450 delivery suburbs. Five storylines are built in, so the root-cause views have something real to find:

1. **Truganina capacity crunch** (Apr–Jul): VIC DIFOT falls from the mid-80s into the 60s, then recovers when a second shift starts on 3 Aug.
2. **North Queensland wet season** (Feb–Mar): late deliveries north of Gladstone.
3. **Melbourne → Perth linehaul disruption** (7–27 Sep): a sharp WA dip.
4. **Friday cut-off**: next-day freight dispatched on Friday misses more often (Monday ETAs are the weakest weekday).
5. **Cost creep**: the fuel levy rises all year and a 4.5% rate review lands on 1 Jul, so cost per kg rises about 12%.

The pipeline doesn't know any of this. It recovers these patterns from the CSVs alone.

## How it works

```mermaid
flowchart LR
  A[Carrier connote CSVs] --> P[pipeline.py - load, clean, geocode, business-day lateness]
  P --> M[Metrics - DIFOT, cost per shipment, per kg, per km]
  M --> J[Aggregates - weekly by state, postcode piles, per-consignment trips]
  J --> T[template.html - deck.gl + Chart.js]
  T --> H[Single self-contained page]
```

- **Input** is the carrier's standard `ConnoteList` export: ConnoteDate, Connote, Sender/Receiver suburb, postcode and state, Items, Pallets, Kgs, ChargedKgs, Cubic, TotalCharge, ETADate, DelvDate, DelvItems.
- **On time** means delivered on or before the carrier ETA, counted in business days (weekends and national holidays excluded). **In full** means delivered items ≥ items + pallets consigned.
- **Distance** is estimated as the straight line between suburb-level coordinates × 1.25 (road factor). Shared-coordinate postcodes such as the Torres Strait islands are pinned manually.
- **Output** is one HTML file with the data embedded, so it can be hosted anywhere or opened locally.

## Run it

```bash
pip install -r requirements.txt
python ref/get_reference.py                  # postcode table + state boundaries
python synthetic/generate.py --out data      # 318k synthetic consignments (seeded, reproducible)
python src/pipeline.py --csv "data/ConnoteList*.csv" --config synthetic/config_demo.json --out build
```

Open `build/index.html`. With the default seed it is byte-identical to `demo/index.html`.

To run on your own carrier export, point `--csv` at the files and copy `config_demo.json` (title, banner text and map label positions).

## Roadmap

The visuals and metrics engine are phase 1 of a multi-agent root-cause system. It follows the same pattern as my [delivery exception agent](../delivery-exception-agent): deterministic code owns every number and routing decision, and LLM agents only segment, explain and draft.

1. **Metrics + visuals** (this repo): deterministic, no LLM.
2. **Failure segmentation + critic**: rank the clusters that explain most failures; a critic rejects any claim that doesn't cite a metric.
3. **RCA agent with carrier scan events**: RAG over SLA, rate card and ops notes; evaluated against hand-labelled failures.
4. **Ask the map + carrier packs**: plain-English questions ("show QLD in September") become validated view specs; weekly carrier review and draft claims, with a human approving them.

## Known limitations

- Root cause is inferred from patterns (where, when, which lane). A true cause needs the carrier's scan or exception events, which this export doesn't contain.
- ETA is the carrier's promise, not a contracted SLA.
- Distance is estimated, not routed. The freight-flow trails are stylised arcs, not road paths.
- The page embeds about 5 MB of data. It runs smoothly on a laptop GPU; very old devices may stutter in Freight flow.

## Credits

Postcode coordinates and remoteness: [matthewproctor/australianpostcodes](https://github.com/matthewproctor/australianpostcodes). State boundaries: [rowanhogan/australian-states](https://github.com/rowanhogan/australian-states). Rendering: [deck.gl](https://deck.gl) and [Chart.js](https://www.chartjs.org). Visual inspiration: Aurecon's *Marine Traffic* shipping visualisation, and Craig Taylor's (Ito World) "1 sphere = 1 person" transit work.

## Licence

No project-specific licence has been granted. Unless stated otherwise, this documentation and the implementation are all rights reserved.
