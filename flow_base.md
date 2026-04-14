flowchart TD
    A[Start] --> B[Inspect git state and repo root]
    B --> C[Create or switch to documentation branch]
    C --> D[Run full repository census]
    D --> E[Build file index and language inventory]
    E --> F[Classify files into useful / ignored]
    F --> G[Partition useful files into work units]
    G --> H[Initialize queue, ledger, unresolved lists, update metadata]
    H --> I{Any work unit left in queue?}

    I -- Yes --> J[Pick next work unit]
    J --> K[Read only local unit files and nearby context]
    K --> L[Generate deep unit docs]
    L --> M[Update reference docs, contracts, flows]
    M --> N[Generate compressed unit summary]
    N --> O[Run verifier on that unit]
    O --> P{Verifier passed?}

    P -- No --> Q[Add misses to unresolved and verification report]
    Q --> R[Deepen local read and patch docs]
    R --> O

    P -- Yes --> S[Mark unit verified in coverage ledger]
    S --> I

    I -- No --> T[Consolidate global docs]
    T --> U[Generate interop docs]
    U --> V[Finalize metadata and update-readiness artifacts]
    V --> W[Run final audit]
    W --> X{Audit passed?}

    X -- No --> Y[Patch unresolved high-priority gaps]
    Y --> W

    X -- Yes --> Z[Commit docs]
    Z --> AA[Push documentation branch]
    AA --> AB[Report results]