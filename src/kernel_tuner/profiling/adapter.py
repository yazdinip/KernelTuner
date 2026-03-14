"""Profiling adapter."""

from __future__ import annotations


def profile_experiment(*args, **kwargs):
    raise NotImplementedError("profiling adapter has not been implemented yet")


def profile_once_entrypoint(payload: str) -> None:
    raise NotImplementedError("internal profiling entrypoint has not been implemented yet")
