# Phase 3 Promoted Summary

Derived from the completed Phase 3 execution program and its confirmation reruns on March 29, 2026.

## Integrity

- canonical confirmation studies completed successfully
- earlier main Phase 3 studies are retained only as replication context
- no incomplete Phase 3 campaign root is promoted into the paper-facing evidence set

## Promoted Findings

- `H5` is unsupported on the expanded `split_k` surface.
  - representative GEMM canonical mapping:
    - `prune_rank`: `1.0324`
    - `naive_random_search`: `1.0427`
    - `v4_transfer_safe_profiled`: `0.1609`
  - takeaway: the transfer-safe corrective pass does not recover near-random-search quality

- The Phase 3 selector ablation confirms transfer failure rather than a profiling miss.
  - parent `prune_rank`: about `0.9692`
  - `v4_transfer_safe_frontier`: about `0.162`
  - `v4_transfer_safe_profiled`: about `0.162`
  - takeaway: the failure is dominated by frontier selection on the enlarged surface

- `split_k` does not survive as a meaningful mainline family.
  - selected non-unit `split_k`: `0`
  - best-scored non-unit `split_k`: `0`
  - takeaway: `split_k` stays diagnostic only and is retired from the paper-facing mainline

- `rows_per_program` does not survive as a meaningful mainline LayerNorm lever.
  - `small_batch`: non-unit choices appear only in weak or noisy paths
  - `large_batch`: non-unit choices appear mostly in regressing profiled or revised paths
  - takeaway: `rows_per_program` stays diagnostic only and is retired from the paper-facing mainline

## Role In The Final Paper

Phase 3 supplies the main bounded negative result in the paper:

- revised selectors are a transfer story, not a simple success story
- failure analysis can justify clean mainline retirements
- negative results improve the credibility of the final bounded positive result
