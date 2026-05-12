# 5. Future Planning

## Executive Position

The future direction of TerraFlux is to evolve from point-level onboard LST inference into a reusable space-grade thermal intelligence platform. The current solution proves the most important principle: a compact, physics-guided model can generate useful LST products with low uplink burden and autonomous quality control. The next steps are to harden the runtime, reduce compute cost further, expand from points to tiles, and close the satellite-terrestrial learning loop.

## Application Prospects

TerraFlux can support multiple mission types:

| Mission Type | Application Prospect |
| --- | --- |
| Agricultural monitoring | Frequent crop-stress and irrigation intelligence |
| Urban observation | Heat-island monitoring and public health warning |
| Disaster response | Thermal anomaly triage for fire, industry, and infrastructure |
| Climate services | Long-term quality-aware LST observation streams |
| Multi-payload satellites | Reusable onboard analytics layer for thermal and optical instruments |
| Constellations | Cross-satellite task sharing and low-latency regional monitoring |

The strongest prospect is a hybrid product model: onboard systems generate fast compact intelligence, while ground systems perform deeper fusion, retraining, validation, and customer delivery.

## Technical Improvement Path

1. Model compression and runtime optimization
   - Quantize residual tables and tree parameters where accuracy permits.
   - Convert selected components into a lightweight inference runtime format.
   - Add artifact-level manifests, hashes, and compatibility checks.

2. Flight-grade resource control
   - Add strict memory ceilings, batch-size governors, and cache eviction policies.
   - Implement power-aware execution modes: safe, economy, nominal, and burst.
   - Profile CPU-only and accelerator-assisted routes on representative embedded hardware.

3. Robust autonomy
   - Expand quality classification beyond valid fraction into cloud, edge, saturation, and out-of-distribution indicators.
   - Add task-ledger restart, partial result commits, and packet-level downlink resume.
   - Maintain a verified emergency fallback model.

4. Tile-level expansion
   - Extend point inference into sparse grid inference for selected high-value tiles.
   - Use onboard screening to decide where dense computation is worth the power cost.
   - Downlink compact thermal summaries and anomaly patches before full raster products.

5. Satellite-terrestrial learning
   - Use onboard uncertainty and error signatures to select training samples for ground audit.
   - Uplink model deltas, not full retraining packages, when only thresholds or residual tables change.
   - Build mission-specific calibration profiles for new sensors and seasons.

## Key Milestones

| Phase | Milestone | Success Criterion |
| --- | --- | --- |
| Phase 1: Ground-hardened package | Freeze model manifest, schema checks, and reproducible docs | Artifact and output format are fully traceable |
| Phase 2: Embedded runtime validation | Run CPU-only inference under memory and time limits | Bounded latency with no accelerator dependency |
| Phase 3: Fault-tolerant execution | Add task ledger, watchdog restart, and resumable downlink package | No result loss after simulated restart |
| Phase 4: Power-aware scheduling | Implement safe, economy, nominal, and burst modes | Compute route adapts to power budget |
| Phase 5: Tile intelligence | Add selected sparse-grid or anomaly-tile products | Produces useful regional summaries without full-scene downlink |
| Phase 6: Constellation reuse | Generalize adapters for new payloads and missions | Same architecture supports multiple sensors |
| Phase 7: Onboard learning support | Add ground-audited delta update loop | Model improves without frequent full uploads |

## Development Priorities

The next engineering focus should be:

- make the artifact manifest explicit and signed,
- convert diagnostic confidence into a stable product field,
- benchmark memory and latency on embedded-class hardware,
- add a restartable task ledger around inference batches,
- define compact downlink packet formats for prediction, alert, and audit modes,
- build a sensor-adapter interface so the architecture can support new payloads.

These priorities strengthen innovation while remaining realistic. They improve the existing solution instead of replacing it with an oversized model that would be harder to fly.

## Long-Term Vision

The long-term TerraFlux vision is an autonomous thermal intelligence layer for satellites. It will not only predict LST; it will decide which observations matter, which packets deserve downlink, which scenes need ground audit, and which mission areas require follow-up imaging.

In a mature constellation, each satellite can run local inference, exchange compact scene summaries through mission control, and receive targeted model updates from ground retraining. This creates a closed loop:

1. observe thermal data onboard,
2. infer and rank value onboard,
3. downlink compact results first,
4. validate and retrain on the ground,
5. uplink small model or policy deltas,
6. repeat with better mission-specific intelligence.

## Answers To Scoring Questions

**Does it clearly articulate the application prospects?**

Yes. The plan identifies prospects in agriculture, urban heat, disaster response, climate services, multi-payload satellites, and constellation-scale thermal monitoring.

**Are there proposed paths for technical improvement?**

Yes. The roadmap covers compression, runtime hardening, quality autonomy, tile expansion, satellite-terrestrial learning, and reusable sensor adapters.

**Does it identify key development milestones for on-orbit computing in this field?**

Yes. The milestones move from ground-hardened packaging to embedded validation, fault tolerance, power-aware scheduling, tile intelligence, constellation reuse, and onboard learning support.
