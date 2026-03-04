# ADR-003: File-Based Artifact Store

- Status: Accepted
- Date: 2026-03-03

## Context

The project needs reproducible experiment outputs, but it does not need a service-based storage layer or shared database for v1.

## Decision

All run artifacts will be written to the local filesystem under `artifacts/<experiment_id>/<run_id>/` using YAML, JSON, and Parquet.

## Consequences

- Storage is easy to inspect manually.
- Artifacts are simple to archive and share.
- The system avoids infrastructure dependencies that would slow development.
- Schema versioning and manifest quality become especially important because there is no database enforcing structure.

## Rejected Alternatives

- SQLite or embedded database: rejected as unnecessary complexity for v1.
- Remote metadata service: rejected because it does not help the core research goal.
- Ad hoc CSV outputs: rejected because schema drift and nested fields are harder to manage.

## Revisit If

- Artifact volume becomes difficult to manage with flat files.
- Multiple collaborators need concurrent artifact discovery or querying beyond manifest-based workflows.
