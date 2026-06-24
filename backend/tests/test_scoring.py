"""Unit tests for the hiking score algorithm.

Covers boundary cases for each penalty and all three verdicts per FEATURE_SPEC.
Pure functions — no DB, no HTTP, no async.
"""

from app.services.scoring import Reason, ScoreResult, score_day


def _score(
    precip_mm: float = 0.0,
    precip_prob: int = 0,
    gusts: float = 0.0,
    apparent_temp_min: float = 10.0,
    elevation_m: float = 1000.0,
    uv_index_max: float = 3.0,
    cape_afternoon: list[float] | None = None,
    visibility_daylight: list[float] | None = None,
) -> ScoreResult:
    return score_day(
        precipitation_sum_mm=precip_mm,
        precipitation_probability_max=precip_prob,
        wind_gusts_kmh=gusts,
        apparent_temp_min=apparent_temp_min,
        elevation_m=elevation_m,
        uv_index_max=uv_index_max,
        cape_afternoon=cape_afternoon if cape_afternoon is not None else [],
        visibility_daylight=visibility_daylight if visibility_daylight is not None else [],
    )


class TestPerfectConditions:
    def test_no_penalties_scores_100(self) -> None:
        r = _score()
        assert r.score == 100
        assert r.verdict == "go"
        assert r.reasons == []

    def test_score_never_exceeds_100(self) -> None:
        assert _score().score <= 100

    def test_score_never_below_zero(self) -> None:
        r = _score(
            precip_mm=30.0,
            gusts=80.0,
            cape_afternoon=[1500.0],
            apparent_temp_min=-15.0,
            uv_index_max=12.0,
            visibility_daylight=[200.0],
        )
        assert r.score >= 0


class TestPrecipPenalty:
    def test_no_precip_no_penalty(self) -> None:
        assert _score(precip_mm=0.0).score == 100

    def test_boundary_exactly_2mm_no_penalty(self) -> None:
        assert _score(precip_mm=2.0).score == 100

    def test_just_above_2mm_low_prob_penalty_5(self) -> None:
        assert _score(precip_mm=2.1, precip_prob=50).score == 95

    def test_just_above_2mm_high_prob_penalty_10(self) -> None:
        assert _score(precip_mm=2.1, precip_prob=80).score == 90

    def test_above_10mm_penalty_20(self) -> None:
        assert _score(precip_mm=15.0).score == 80

    def test_above_20mm_penalty_35(self) -> None:
        assert _score(precip_mm=25.0).score == 65

    def test_boundary_exactly_10mm_penalty_5_or_10(self) -> None:
        # 10mm is NOT > 10, so falls to the > 2 branch
        r_low = _score(precip_mm=10.0, precip_prob=50)
        r_high = _score(precip_mm=10.0, precip_prob=80)
        assert r_low.score == 95
        assert r_high.score == 90

    def test_boundary_exactly_20mm_penalty_20(self) -> None:
        # 20mm is NOT > 20, so falls to the > 10 branch
        assert _score(precip_mm=20.0).score == 80


class TestWindPenalty:
    def test_no_gusts_no_penalty(self) -> None:
        assert _score(gusts=0.0).score == 100

    def test_at_35kmh_no_penalty(self) -> None:
        assert _score(gusts=35.0).score == 100

    def test_just_above_35kmh_penalty_5(self) -> None:
        assert _score(gusts=36.0).score == 95

    def test_above_50kmh_penalty_15(self) -> None:
        assert _score(gusts=55.0).score == 85

    def test_at_70kmh_penalty_15_not_25(self) -> None:
        # 70 is NOT > 70, so falls to the > 50 branch
        assert _score(gusts=70.0).score == 85

    def test_above_70kmh_penalty_25(self) -> None:
        assert _score(gusts=75.0).score == 75


class TestThunderstormPenalty:
    def test_empty_cape_no_penalty(self) -> None:
        assert _score(cape_afternoon=[]).score == 100

    def test_zero_cape_no_penalty(self) -> None:
        assert _score(cape_afternoon=[0.0, 0.0]).score == 100

    def test_at_500_jkg_no_penalty(self) -> None:
        assert _score(cape_afternoon=[500.0]).score == 100

    def test_just_above_500_jkg_penalty_10(self) -> None:
        assert _score(cape_afternoon=[501.0]).score == 90

    def test_above_1000_jkg_penalty_25(self) -> None:
        assert _score(cape_afternoon=[1200.0]).score == 75

    def test_at_1000_jkg_penalty_10_not_25(self) -> None:
        # 1000 is NOT > 1000, so falls to the > 500 branch
        assert _score(cape_afternoon=[1000.0]).score == 90

    def test_uses_max_not_average(self) -> None:
        # One spike above 1000, others low — penalty should be 25
        assert _score(cape_afternoon=[0.0, 1100.0, 200.0]).score == 75


class TestColdPenalty:
    def test_warm_no_penalty(self) -> None:
        assert _score(apparent_temp_min=10.0).score == 100

    def test_below_zero_low_elevation_no_penalty(self) -> None:
        # < 0 but elevation <= 1800 — no penalty
        assert _score(apparent_temp_min=-1.0, elevation_m=1500.0).score == 100

    def test_below_zero_high_elevation_penalty_8(self) -> None:
        assert _score(apparent_temp_min=-1.0, elevation_m=2000.0).score == 92

    def test_at_minus5_high_elevation_penalty_8(self) -> None:
        # -5 is NOT < -5, so only altitude branch applies
        assert _score(apparent_temp_min=-5.0, elevation_m=2000.0).score == 92

    def test_below_minus5_any_elevation_penalty_15(self) -> None:
        assert _score(apparent_temp_min=-6.0, elevation_m=500.0).score == 85

    def test_below_minus5_high_elevation_still_only_15(self) -> None:
        # First branch wins — no double-counting
        assert _score(apparent_temp_min=-6.0, elevation_m=2500.0).score == 85


class TestVisibilityPenalty:
    def test_no_data_no_penalty(self) -> None:
        assert _score(visibility_daylight=[]).score == 100

    def test_good_visibility_no_penalty(self) -> None:
        assert _score(visibility_daylight=[10000.0, 20000.0]).score == 100

    def test_at_5000m_no_penalty(self) -> None:
        assert _score(visibility_daylight=[5000.0]).score == 100

    def test_below_5000m_penalty_5(self) -> None:
        assert _score(visibility_daylight=[3000.0]).score == 95

    def test_at_1000m_penalty_5_not_10(self) -> None:
        # 1000 is NOT < 1000
        assert _score(visibility_daylight=[1000.0]).score == 95

    def test_below_1000m_penalty_10(self) -> None:
        assert _score(visibility_daylight=[500.0]).score == 90

    def test_uses_minimum_across_window(self) -> None:
        # One bad reading among good ones → penalty applies
        assert _score(visibility_daylight=[20000.0, 800.0, 15000.0]).score == 90


class TestUVPenalty:
    def test_uv_below_9_no_penalty(self) -> None:
        assert _score(uv_index_max=8.9).score == 100

    def test_uv_exactly_9_penalty_5(self) -> None:
        assert _score(uv_index_max=9.0).score == 95

    def test_uv_above_9_still_only_5(self) -> None:
        assert _score(uv_index_max=12.0).score == 95


class TestVerdicts:
    def test_score_100_is_go(self) -> None:
        assert _score().verdict == "go"

    def test_score_70_is_go(self) -> None:
        # gusts 36 (5) + precip 15 (20) + uv 9 (5) = 30 → score 70
        r = _score(precip_mm=15.0, gusts=36.0, uv_index_max=9.0)
        assert r.score == 70
        assert r.verdict == "go"

    def test_score_69_is_caution(self) -> None:
        # gusts 36 (5) + precip 15 (20) + uv 9 (5) + vis 3000 (5) = 35 → score 65
        r = _score(precip_mm=15.0, gusts=36.0, uv_index_max=9.0, visibility_daylight=[3000.0])
        assert r.score == 65
        assert r.verdict == "caution"

    def test_score_40_is_caution(self) -> None:
        # precip 25 (35) + gusts 36 (5) + cape 501 (10) + uv 9 (5) + vis 3000 (5) = 60 → score 40
        r = _score(
            precip_mm=25.0,
            gusts=36.0,
            cape_afternoon=[501.0],
            uv_index_max=9.0,
            visibility_daylight=[3000.0],
        )
        assert r.score == 40
        assert r.verdict == "caution"

    def test_score_39_is_no_go(self) -> None:
        # precip 25 (35) + gusts 75 (25) = 60 → score 40... need more
        # precip 25 (35) + gusts 75 (25) + cape 1200 (25) = 85 → score 15
        r = _score(precip_mm=25.0, gusts=75.0, cape_afternoon=[1200.0])
        assert r.score == 15
        assert r.verdict == "no_go"


class TestReasons:
    def test_no_penalties_empty_reasons(self) -> None:
        assert _score().reasons == []

    def test_single_penalty_one_reason(self) -> None:
        r = _score(gusts=75.0)
        assert len(r.reasons) == 1

    def test_reasons_capped_at_three(self) -> None:
        r = _score(
            precip_mm=25.0,
            gusts=75.0,
            cape_afternoon=[1200.0],
            apparent_temp_min=-10.0,
            uv_index_max=9.0,
            visibility_daylight=[500.0],
        )
        assert len(r.reasons) <= 3

    def test_largest_penalty_is_first_reason(self) -> None:
        # precip 25mm → 35 pts, gusts 55 → 15 pts; precip should be first
        r = _score(precip_mm=25.0, gusts=55.0)
        assert "precipitation" in r.reasons[0].en.lower() or "mm" in r.reasons[0].en

    def test_each_reason_has_en_and_ro(self) -> None:
        r = _score(gusts=75.0)
        reason = r.reasons[0]
        assert isinstance(reason, Reason)
        assert len(reason.en) > 0
        assert len(reason.ro) > 0
