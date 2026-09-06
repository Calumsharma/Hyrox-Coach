from app.services.periodization import build_intensity_curve


def test_curve_has_correct_length_and_week_numbers():
    curve = build_intensity_curve(8)
    assert len(curve) == 8
    assert [w.week_number for w in curve] == list(range(1, 9))


def test_intensity_rises_through_base_build_peak():
    curve = build_intensity_curve(12)
    non_taper = [w for w in curve if w.phase != "taper"]
    intensities = [w.planned_intensity for w in non_taper]
    assert intensities == sorted(intensities)


def test_taper_drops_intensity_below_peak():
    curve = build_intensity_curve(12)
    peak_weeks = [w for w in curve if w.phase == "peak"]
    taper_weeks = [w for w in curve if w.phase == "taper"]
    assert peak_weeks and taper_weeks
    assert taper_weeks[-1].planned_intensity < peak_weeks[-1].planned_intensity


def test_final_taper_week_is_lightest():
    curve = build_intensity_curve(10)
    assert curve[-1].planned_intensity == min(w.planned_intensity for w in curve)


def test_single_week_block_does_not_crash():
    curve = build_intensity_curve(1)
    assert len(curve) == 1
