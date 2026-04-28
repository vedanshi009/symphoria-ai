from src.planner_agent import PlannerAgent, RecommendationPlan


def make_user_prefs():
    return {
        "favorite_genre": "lofi",
        "mood_context": ["chill"],
        "target_energy_range": (0.4, 0.6),
    }


def test_focused_plan_high_confidence():
    planner = PlannerAgent()

    intent = {
        "confidence": 0.9,
        "energy": 0.5,
        "ambiguity": False,
    }

    plan = planner.create_plan(intent, make_user_prefs())

    assert isinstance(plan, RecommendationPlan)
    assert plan.mode == "focused"
    assert plan.max_artists == 1


def test_balanced_plan_low_confidence():
    planner = PlannerAgent()

    intent = {
        "confidence": 0.2,
        "ambiguity": True,
    }

    plan = planner.create_plan(intent, make_user_prefs())

    assert plan.mode == "balanced"
    assert plan.diversity_required is True


def test_high_energy_plan():
    planner = PlannerAgent()

    intent = {
        "confidence": 0.9,
        "energy": 0.9,
        "ambiguity": False,
    }

    plan = planner.create_plan(intent, make_user_prefs())

    assert plan.mode == "exploration"
    assert plan.max_artists == 3


def test_refine_plan_adjusts_energy_range():
    planner = PlannerAgent()

    plan = planner.create_plan(
        {"confidence": 1.0, "energy": 0.5},
        make_user_prefs(),
    )

    report = {
        "issues": ["playlist too monotonous in energy"]
    }

    refined = planner.refine_plan(plan, report)

    lo_old, hi_old = plan.adjusted_user_prefs["target_energy_range"]
    lo_new, hi_new = refined.adjusted_user_prefs["target_energy_range"]

    assert lo_new <= lo_old
    assert hi_new >= hi_old