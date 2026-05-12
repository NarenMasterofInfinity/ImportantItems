# 2. On-Orbit Implementation Feasibility

## Executive Position

TerraFlux is feasible for on-orbit deployment because its core inference package is small, deterministic, and dominated by local thermal feature extraction rather than heavy neural-network execution. The deployed `final_artifact.pkl` is 3,004,088 bytes, and the runtime dependency stack is limited to numerical processing, geospatial projection, raster I/O, and classical machine learning libraries.

The flight design minimizes uplink bandwidth by separating model artifacts, calibration tables, mission profiles, and data products. Only small deltas need to be uplinked after the first deployment.

## Uplink Package And Compression Strategy

The baseline uplink bundle is split into independently updateable parts:

| Bundle | Content | Update Method | Compression Strategy |
| --- | --- | --- | --- |
| Core inference artifact | `final_artifact.pkl`, schema hash, model manifest | Rare full update or binary delta | Zstandard or gzip with checksum |
| Mission config | thresholds, priority policies, scene filters | Small text patch | Plain JSON plus package-level compression |
| Calibration reference | preloaded sensor tables, Planck constants, valid ranges | Mission phase update | Dictionary-compressed table archive |
| Runtime code | inference package and adapters | Controlled software load | Container layer or signed tarball delta |
| Emergency fallback | minimal physics-only model and static coefficients | Preloaded before mission | Stored redundantly, rarely uplinked |

The current model artifact size gives a strong feasibility margin. A full model refresh is about 3.0 MB before additional package compression. Smaller configuration and threshold changes are expected to be kilobyte-scale.

## Runtime Resource Estimate

The current point-level inference path is suitable for CPU-first execution:

| Resource | Expected Use | Feasibility Notes |
| --- | --- | --- |
| CPU | Moderate during scene scan, projection, patch extraction, and model prediction | Can run on a radiation-tolerant control processor without GPU dependency |
| GPU/NPU | Optional | Reserved for future dense-tile screening, neural residuals, or batch acceleration |
| Memory | Bounded by active raster patch, metadata, feature arrays, and model artifact | Avoids loading complete scenes into RAM; reads local windows around target points |
| Storage | Model package, scene files, calibration XML, cache, result bundles | Cache can be size-capped and evicted by scene priority |
| Downlink bandwidth | Low for standard inference | `result.json` and quality summaries are much smaller than raster scenes |

For a typical point table, peak memory should be governed by raster I/O buffers and patch windows, not model size. The architecture keeps only active patches and scene summaries in memory, so it remains practical for embedded flight computers.

## Dependent Data Sources

TerraFlux separates dependencies by whether they must be onboard, uplinked, or optional:

| Data Source | Management Method | On-Orbit Dependency Risk |
| --- | --- | --- |
| Thermal GeoTIFF scene | Produced by onboard payload or stored mission data | Required for inference |
| Calibration XML and metadata XML | Stored next to scene or preloaded as reference table | Required; fallback table available |
| Test point table | Uplinked tasking file or generated onboard from event detector | Required for point output |
| Model artifact | Preloaded, signed, versioned, and checksummed | Required; previous verified version retained |
| Scene fingerprints | Generated onboard and cached | Optional acceleration |
| External satellite feeds | Used only for cross-satellite context or validation | Not required for core inference |
| Ground commands | Used for task priorities and update policies | Not required during autonomous mode |

The critical design choice is autonomy: core LST inference does not require continuous ground contact or external satellite feeds.

## Single-Run Latency Analysis

Latency is split into deterministic stages:

| Stage | Nominal Driver | Worst-Case Driver |
| --- | --- | --- |
| Scene discovery | Number of files and directory depth | Large storage volume or fragmented packets |
| Metadata parsing | XML and TIFF tag parsing | Missing metadata requiring fallback lookup |
| Point loading | CSV size | Malformed rows requiring validation and repair |
| Geolocation | Coordinate projection per point | Multiple candidate scene checks |
| Patch extraction | Raster window reads | Slow storage or many invalid pixels requiring nearest-valid search |
| Feature generation | Brightness temperature and statistics | Large point count and cache miss |
| Inference | Small classical model prediction | Degraded-mode branching and diagnostics |
| Packaging | JSON and CSV writing | Downlink packet fragmentation |

For normal point-level inference, expected latency is seconds to low minutes depending mainly on storage speed, number of points, and raster access pattern. Worst-case latency is bounded by configured scene count, point count, fallback search radius, cache size, and watchdog timeout. The flight implementation should enforce maximum point batch size per task and split oversized requests into resumable micro-batches.

## Resource Control Policies

1. Batch limiter
   - Split large point tables by scene and by maximum point count.
   - Commit partial result bundles after each micro-batch.

2. Cache limiter
   - Keep active scene metadata and thermal summaries.
   - Evict raw derived products before model artifacts or emergency fallback tables.

3. Power-aware scheduler
   - Use CPU-only mode during low-power periods.
   - Enable GPU/NPU only for dense products or urgent high-volume requests.

4. Watchdog timeout
   - Restart failed stage from last committed task ledger entry.
   - Preserve completed predictions and quality rows.

5. Downlink throttle
   - Send prediction and alert packets first.
   - Defer full diagnostics until bandwidth is available.

## Answers To Scoring Questions

**Are the uplink file sizes and compression strategies clearly defined?**

Yes. The primary model artifact is 3,004,088 bytes. The proposed uplink strategy uses compressed, signed, independently updateable bundles with binary deltas for model changes and small JSON patches for thresholds and mission policies.

**Are there reasonable estimates for resource consumption, including CPU/GPU, memory, and storage?**

Yes. The core route is CPU-first, uses optional GPU/NPU acceleration only for future dense workloads, keeps memory bounded by local raster windows and feature arrays, and controls storage through hot, warm, and cold cache tiers.

**Are the types of dependent data sources and their management methods specified?**

Yes. Required dependencies are onboard scene data, calibration metadata, point tasking data, and the signed model artifact. External feeds and ground commands are optional enhancements, not hard runtime dependencies.

**Is there an analysis of single-execution time and worst-case latency?**

Yes. Latency is decomposed by stage, with worst-case drivers identified. The architecture bounds latency with micro-batching, fallback radius limits, cache limits, and watchdog-controlled restart points.
