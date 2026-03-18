# Module Spec: Kernel Registry

## Purpose

Define how kernels are registered, identified, validated, and connected to both Triton implementations and reference implementations.

## Responsibilities

- load `KernelSpec` definitions from YAML
- validate kernel metadata
- provide stable lookup by `kernel_id`
- bind each kernel spec to required implementation hooks
- validate shape schemas for each kernel family

## Non-Responsibilities

- generating configuration candidates
- running benchmarks
- collecting compile signals
- writing artifacts directly

## Public Inputs and Outputs

Inputs:

- kernel config YAML
- in-repo Python implementation references for Triton and reference kernels

Outputs:

- validated `KernelSpec`
- resolved kernel object with required hooks:
  - `make_inputs(shape, seed, device="cuda")`
  - `supports_config(shape, config)`
  - `run_kernel(inputs, shape, config)`
  - `reference_impl(inputs, policy)`
  - `validate_output(candidate_output, reference_output, policy)`
  - `performance_metric(shape, config, latency_median_us)`
  - `compile_metadata(inputs, shape, config)`

Stable metadata fields:

- `kernel_id`
- `family`
- `description`
- `shape_schema`
- `dtype_support`
- `config_parameters`
- `reference_impl`
- `supports_profiling`

Optional kernel metadata may include:

- `default_config`
- `correctness_policy`
- `tags`
- `notes`

Current v1 families:

- `gemm`
- `layernorm`

## Internal Workflow

1. Load YAML config for a kernel.
2. Validate required metadata fields.
3. Normalize the shape schema into a typed representation.
4. Validate any `correctness_policy` fields that the benchmark harness will require for output checking.
5. Resolve implementation references.
6. Bind runtime hooks, reference hooks, and metadata hooks.
7. Register the kernel under `kernel_id`.

## Persisted Artifacts Touched

- reads `configs/kernels/<kernel_id>.yaml`
- does not write run artifacts directly

## Failure Modes and Fallback Behavior

- missing required metadata: reject registration
- duplicate `kernel_id`: reject registration
- missing implementation reference: reject registration
- incompatible shape schema: reject registration
- unsupported dtype request: reject shape or config resolution before execution

There is no fallback to partially registered kernels in v1.

## Logging and Observability Requirements

- log successful kernel registrations with `kernel_id` and `family`
- log duplicate or invalid registrations with clear reasons
- log implementation resolution failures with the referenced symbol path

## Test Cases

- reject missing metadata
- reject duplicate kernel IDs
- resolve valid GEMM kernel config
- resolve valid LayerNorm kernel config
- fail on missing implementation hook
- fail shape validation for malformed shape records

## Extension Points

- additional kernel families
- family-specific shape normalizers
- kernel-specific metadata fields under a namespaced optional section

## Stable Contract vs Exploratory Areas

Stable contract:

- `kernel_id` is the canonical registry key
- every registered kernel must expose the required hooks
- shape validation happens at registration and resolution time
- v1 kernel resolution supports GEMM and LayerNorm

Exploratory areas:

- exact representation of implementation references
- additional optional metadata fields per kernel family
