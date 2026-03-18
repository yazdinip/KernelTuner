from kernel_tuner.selector.engine import _select_with_tolerance


def test_select_with_tolerance_prefers_ranked_order_within_band():
    runtime_scores = {
        "cfg_late_best": 1.00,
        "cfg_early_near_best": 1.015,
        "cfg_far": 1.20,
    }
    ranked_order = ["cfg_early_near_best", "cfg_late_best", "cfg_far"]

    selected = _select_with_tolerance(runtime_scores, ranked_order, relative_tolerance=0.02)

    assert selected == "cfg_early_near_best"


def test_select_with_tolerance_uses_best_when_gap_exceeds_band():
    runtime_scores = {
        "cfg_early": 1.05,
        "cfg_best": 1.00,
    }
    ranked_order = ["cfg_early", "cfg_best"]

    selected = _select_with_tolerance(runtime_scores, ranked_order, relative_tolerance=0.02)

    assert selected == "cfg_best"
