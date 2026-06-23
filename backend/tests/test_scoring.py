"""Unit tests for the hiking score algorithm.

Pure functions — no DB, no HTTP, no async. Fast to run and easy to extend
when scoring weights are adjusted.
"""

from app.services.scoring import ScoreResult, score_day


def _score(
    code: int = 0,
    temp_max: float = 20.0,
    temp_min: float = 10.0,
    precip: float = 0.0,
    gusts: float = 0.0,
) -> ScoreResult:
    return score_day(code, temp_max, temp_min, precip, gusts)


class TestPerfectConditions:
    def test_clear_sky_no_wind_no_rain_scores_100(self) -> None:
        r = _score(code=0)
        assert r.score == 100
        assert r.label == "Excellent"
        assert "good" in r.reason.lower()

    def test_partly_cloudy_no_penalty(self) -> None:
        r = _score(code=2)
        assert r.score == 100


class TestWeatherCodePenalties:
    def test_thunderstorm_is_dangerous(self) -> None:
        r = _score(code=95)
        assert r.score == 45          # 100 - 55 penalty
        assert r.label == "Poor"      # 30-49 range
        assert "thunderstorm" in r.reason.lower()

    def test_thunderstorm_with_hail_collapses_score(self) -> None:
        r = _score(code=99)
        assert r.score == 35          # 100 - 65 penalty

    def test_heavy_rain_is_poor(self) -> None:
        r = _score(code=65)
        assert r.score <= 60

    def test_fog_penalises_significantly(self) -> None:
        r = _score(code=45)
        assert r.score <= 70
        assert "fog" in r.reason.lower()


class TestWindPenalties:
    def test_light_wind_no_penalty(self) -> None:
        r = _score(gusts=20.0)
        assert r.score == 100

    def test_moderate_gusts_small_penalty(self) -> None:
        r = _score(gusts=35.0)
        assert r.score == 90

    def test_strong_gusts_significant_penalty(self) -> None:
        r = _score(gusts=50.0)
        assert r.score == 75

    def test_dangerous_gusts_is_dangerous(self) -> None:
        r = _score(gusts=95.0)
        assert r.score <= 40
        assert r.label in ("Poor", "Dangerous")
        assert "dangerous" in r.reason.lower() or "km/h" in r.reason


class TestTemperaturePenalties:
    def test_normal_temp_no_penalty(self) -> None:
        r = _score(temp_max=22.0, temp_min=12.0)
        assert r.score == 100

    def test_below_freezing_small_penalty(self) -> None:
        r = _score(temp_min=-2.0)
        assert r.score == 95

    def test_extreme_cold_large_penalty(self) -> None:
        r = _score(temp_min=-20.0)
        assert r.score <= 70
        assert "cold" in r.reason.lower() or "frostbite" in r.reason.lower()

    def test_extreme_heat_penalises(self) -> None:
        r = _score(temp_max=40.0)
        assert r.score <= 75


class TestCombinedPenalties:
    def test_thunderstorm_plus_high_wind_is_zero(self) -> None:
        r = _score(code=95, gusts=95.0)
        assert r.score == 0
        assert r.label == "Dangerous"

    def test_worst_reason_is_reported(self) -> None:
        # Thunderstorm (55) > wind (10) — thunderstorm should be reason
        r = _score(code=95, gusts=35.0)
        assert "thunderstorm" in r.reason.lower()

    def test_score_never_exceeds_100(self) -> None:
        r = _score(code=0, temp_max=20.0, temp_min=15.0, precip=0.0, gusts=0.0)
        assert r.score <= 100

    def test_score_never_below_zero(self) -> None:
        r = _score(code=99, gusts=100.0, precip=25.0, temp_min=-20.0)
        assert r.score >= 0


class TestScoreLabels:
    def test_100_is_excellent(self) -> None:
        assert _score().label == "Excellent"

    def test_85_is_excellent(self) -> None:
        r = _score(gusts=30.0)  # -10 → 90
        assert r.label == "Excellent"

    def test_moderate_degradation_gives_good(self) -> None:
        # gusts 50 → -25 → score 75
        r = _score(gusts=50.0)
        assert r.label == "Good"
