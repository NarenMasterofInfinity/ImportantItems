# 1. Overall Task Implementation Architecture

## Executive Position

TerraFlux is designed as an on-orbit land surface temperature intelligence pipeline, not as a simple file-in/file-out inference script. The current Track 3 package already contains the core flight-suitable inference pattern: a compact `final_artifact.pkl` model, deterministic point-level processing, physics-guided feature extraction, autonomous quality reporting, and standardized `result.json` output. The proposed on-orbit architecture wraps that core with spacecraft-grade ingestion, cache control, heterogeneous scheduling, health monitoring, and prioritized downlink.

The design is complete across the full process: data injection, scene discovery, distributed cache registration, calibration parsing, thermal preprocessing, feature generation, scene-aware inference, quality gating, result encapsulation, and downlink packaging.

## End-to-End Mission Flow

1. Data injection
   - Inputs arrive from payload storage, real-time acquisition, or ground uplink.
   - The ingestion controller registers each GeoTIFF scene, calibration XML, metadata XML, and target point table.
   - Each input is assigned a content hash, timestamp, scene ID, and priority class.

2. Distributed onboard cache
   - Hot cache keeps active point tables, scene metadata, calibration coefficients, and recently accessed raster tiles.
   - Warm cache stores compressed scene fingerprints, quality masks, and reusable thermal statistics.
   - Cold cache stores archived tiles and completed result packages until downlink windows open.
   - Cache records are checksum-protected and can be invalidated per scene, per tile, or per model version.

3. On-orbit preprocessing
   - The scene loader scans KX10 thermal files, parses georeferencing tags, loads gain and bias calibration, and converts latitude and longitude into raster row and column.
   - Invalid scene IDs or out-of-bounds point references are repaired by selecting the containing scene when possible.
   - Thermal radiance is converted to brightness temperature, then compact point features, physics features, and scene-level fingerprints are generated.

4. Multi-task parallel computing
   - CPU cores handle metadata parsing, coordinate projection, file validation, cache indexing, and result serialization.
   - GPU or NPU resources are reserved for optional dense neural models, large tile screening, or future batch residual engines.
   - The lightweight leaderboard_v2 artifact remains CPU-first, allowing the mission to operate even when accelerators are powered down.
   - Tasks are scheduled by priority: safety alerts first, high-value observation windows second, routine analytics third.

5. Scene-aware inference
   - The primary model uses physics-guided thermal features as an anchor.
   - Scene-local affine calibration corrects per-scene bias.
   - Local residual memory interpolates remaining errors using spatial position and thermal similarity.
   - For uncertain or damaged inputs, the system switches to conservative degraded-mode prediction based on scene-level thermal statistics.

6. Result encapsulation
   - Predictions are written to `result.json` using the competition-required schema.
   - Diagnostic rows are written to `quality_report.csv` with scene repair status, fallback distance, quality flags, component corrections, and prediction values.
   - Each result bundle includes model ID, input hash, timestamp, confidence class, and execution summary for traceability.

7. Downlink mechanism
   - Primary downlink sends compact analytics first: `result.json`, quality summaries, urgent alert packets, and anomaly thumbnails.
   - Secondary downlink sends selected diagnostic CSV rows and compressed scene fingerprints.
   - Full raster products are downlinked only when ground operators request audit or retraining data.

## Modular Architecture

The architecture is separated into flight modules with narrow responsibilities:

| Module | Role | Fault Boundary |
| --- | --- | --- |
| Ingestion Controller | Validates incoming files and registers scenes | Rejects corrupted or incomplete scene packets |
| Cache Manager | Controls hot, warm, and cold storage | Evicts by priority and recomputes missing derived products |
| Calibration Engine | Parses georeferencing, gain, bias, and metadata | Falls back to preloaded mission calibration tables |
| Feature Engine | Produces physics, compact, and scene features | Reuses cached features or switches to reduced feature mode |
| Inference Router | Selects normal, local-scene, global, or degraded prediction path | Uses model checksum and schema validation before execution |
| Quality Governor | Assigns quality flags and confidence classes | Blocks unsafe high-confidence claims |
| Downlink Packager | Compresses and prioritizes output bundles | Preserves essential alerts under low-bandwidth windows |

This modularity makes the system adaptable to new payloads. A new thermal imager needs only a sensor adapter for calibration and geolocation; the cache, scheduler, inference router, quality governor, and downlink logic remain reusable.

## Heterogeneous Scheduling

The scheduler uses a resource-aware execution policy:

| Workload | Preferred Resource | Reason |
| --- | --- | --- |
| File discovery, XML parsing, coordinate projection | CPU | Branch-heavy and I/O-bound |
| Point-level leaderboard_v2 inference | CPU | Small model, low memory, deterministic latency |
| Batch tile screening or future dense maps | GPU/NPU | Parallel raster operations and neural inference |
| Compression and checksum tasks | CPU or hardware crypto block | Power-efficient packet preparation |
| Watchdog, health monitor, and task ledger | Radiation-tolerant control CPU | Must remain available during accelerator resets |

This route is suitable for resource-constrained spacecraft because the critical path is not dependent on high-power acceleration. Accelerators improve throughput but are not required for mission continuity.

## Fault-Tolerant Processing

Fault tolerance is built into every stage:

| Failure Mode | Response |
| --- | --- |
| Missing scene ID | Infer containing scene from geolocation |
| Out-of-bounds point | Reassign to valid containing scene or mark unrecoverable |
| Invalid center pixel | Search nearest valid pixel and record fallback distance |
| Low valid-pixel fraction | Switch to conservative prediction and low-confidence flag |
| Cache corruption | Recompute feature products from raw scene and calibration |
| Model checksum mismatch | Revert to last verified model bundle |
| Accelerator reset | Continue CPU-first inference path |
| Downlink interruption | Store signed result bundle and resume by packet sequence |

The design avoids a single point of failure. If the full feature stack is unavailable, TerraFlux can still produce lower-confidence but useful thermal estimates and explicitly report the degradation.

## Answers To Scoring Questions

**Is the full-process logic clear and complete, covering all stages from data injection to result downlink?**

Yes. The pipeline is defined from onboard data injection through cache registration, thermal preprocessing, model inference, quality packaging, and prioritized downlink. The required outputs remain `result.json` for predictions and `quality_report.csv` for auditability.

**Does the technical route incorporate key designs such as modularity, heterogeneous scheduling, and fault tolerance?**

Yes. The architecture uses modular flight services, CPU/GPU/NPU-aware scheduling, cache-backed execution, model and data checksums, watchdog recovery, degraded-mode prediction, and resumable downlink.

**Is the architecture design reasonable and adaptable to resource-constrained space environments?**

Yes. The current inference artifact is compact at approximately 3.0 MB and can run CPU-first. The architecture reserves accelerators for optional high-throughput tasks while preserving a deterministic low-power path for essential LST inference.
