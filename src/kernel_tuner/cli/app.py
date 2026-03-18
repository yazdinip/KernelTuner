"""Typer application for KernelTuner."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from kernel_tuner.analysis.comparison import compare_runs_from_path, validate_study_from_path
from kernel_tuner.analysis.reporting import summarize_run
from kernel_tuner.benchmark.harness import benchmark_experiment
from kernel_tuner.common.config import (
    load_experiment_spec,
    load_kernel_spec,
)
from kernel_tuner.common.logging_utils import configure_logging
from kernel_tuner.config_space.generator import generate_candidate_configs
from kernel_tuner.experiments.campaigns import (
    materialize_campaign_from_path,
    resume_campaign_from_path,
    run_campaign_from_path,
)
from kernel_tuner.experiments.orchestrator import run_experiment
from kernel_tuner.kernels.registry import resolve_kernel
from kernel_tuner.profiling.adapter import profile_experiment, profile_once_entrypoint
from kernel_tuner.profiling.compatibility import validate_counter_set_from_path
from kernel_tuner.selector.engine import select_for_experiment
from kernel_tuner.signals.collector import collect_signals_for_experiment

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command("validate-kernel")
def validate_kernel(
    kernel: Path = typer.Option(..., "--kernel", exists=True, dir_okay=False),
    verbose: bool = False,
) -> None:
    configure_logging(verbose)
    spec = load_kernel_spec(kernel)
    resolve_kernel(spec)
    typer.echo(f"Validated kernel '{spec.kernel_id}' from {kernel}")


@app.command("generate-configs")
def generate_configs(
    experiment: Path = typer.Option(..., "--experiment", exists=True, dir_okay=False),
    verbose: bool = False,
) -> None:
    configure_logging(verbose)
    spec = load_experiment_spec(experiment)
    result = generate_candidate_configs(spec, emit_artifacts=True, experiment_path=experiment)
    typer.echo(json.dumps(result, indent=2))


@app.command("benchmark")
def benchmark(
    experiment: Path = typer.Option(..., "--experiment", exists=True, dir_okay=False),
    verbose: bool = False,
) -> None:
    configure_logging(verbose)
    result = benchmark_experiment(load_experiment_spec(experiment), experiment_path=experiment)
    typer.echo(json.dumps(result, indent=2))


@app.command("collect-signals")
def collect_signals(
    experiment: Path = typer.Option(..., "--experiment", exists=True, dir_okay=False),
    verbose: bool = False,
) -> None:
    configure_logging(verbose)
    result = collect_signals_for_experiment(load_experiment_spec(experiment), experiment_path=experiment)
    typer.echo(json.dumps(result, indent=2))


@app.command("profile")
def profile(
    experiment: Path = typer.Option(..., "--experiment", exists=True, dir_okay=False),
    verbose: bool = False,
) -> None:
    configure_logging(verbose)
    result = profile_experiment(load_experiment_spec(experiment), experiment_path=experiment)
    typer.echo(json.dumps(result, indent=2))


@app.command("validate-counter-set")
def validate_counter_set(
    experiment: Path = typer.Option(..., "--experiment", exists=True, dir_okay=False),
    verbose: bool = False,
) -> None:
    configure_logging(verbose)
    result = validate_counter_set_from_path(experiment)
    typer.echo(json.dumps(result, indent=2))


@app.command("select")
def select(
    experiment: Path = typer.Option(..., "--experiment", exists=True, dir_okay=False),
    verbose: bool = False,
) -> None:
    configure_logging(verbose)
    result = select_for_experiment(load_experiment_spec(experiment), experiment_path=experiment)
    typer.echo(json.dumps(result, indent=2))


@app.command("run-experiment")
def run(
    experiment: Path = typer.Option(..., "--experiment", exists=True, dir_okay=False),
    verbose: bool = False,
) -> None:
    configure_logging(verbose)
    result = run_experiment(load_experiment_spec(experiment), experiment_path=experiment)
    typer.echo(json.dumps(result, indent=2))


@app.command("summarize")
def summarize(
    run: Path = typer.Option(..., "--run", exists=True, file_okay=False),
    verbose: bool = False,
) -> None:
    configure_logging(verbose)
    result = summarize_run(run)
    typer.echo(json.dumps(result, indent=2))


@app.command("compare-runs")
def compare_runs(
    spec: Path = typer.Option(..., "--spec", exists=True, dir_okay=False),
    verbose: bool = False,
) -> None:
    configure_logging(verbose)
    result = compare_runs_from_path(spec)
    typer.echo(json.dumps(result, indent=2))


@app.command("validate-study")
def validate_study(
    spec: Path = typer.Option(..., "--spec", exists=True, dir_okay=False),
    verbose: bool = False,
) -> None:
    configure_logging(verbose)
    result = validate_study_from_path(spec)
    typer.echo(json.dumps(result, indent=2))


@app.command("materialize-campaign")
def materialize_campaign(
    spec: Path = typer.Option(..., "--spec", exists=True, dir_okay=False),
    verbose: bool = False,
) -> None:
    configure_logging(verbose)
    result = materialize_campaign_from_path(spec)
    typer.echo(json.dumps(result, indent=2))


@app.command("run-campaign")
def run_campaign(
    spec: Path = typer.Option(..., "--spec", exists=True, dir_okay=False),
    verbose: bool = False,
) -> None:
    configure_logging(verbose)
    result = run_campaign_from_path(spec)
    typer.echo(json.dumps(result, indent=2))


@app.command("resume-campaign")
def resume_campaign(
    spec: Path = typer.Option(..., "--spec", exists=True, dir_okay=False),
    verbose: bool = False,
) -> None:
    configure_logging(verbose)
    result = resume_campaign_from_path(spec)
    typer.echo(json.dumps(result, indent=2))


@app.command("_profile-once", hidden=True)
def profile_once(payload: str) -> None:
    profile_once_entrypoint(payload)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
