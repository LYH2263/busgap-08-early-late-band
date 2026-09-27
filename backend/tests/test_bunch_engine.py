from datetime import datetime, timedelta
from app.services.bunch_engine import classify_gap, detect_bunching

BASE = datetime(2026, 1, 1, 8, 0)


def arr(trip, arrive_min, dep_min=None, seq=0, stop="A"):
    a = {"stop_name": stop, "trip_no": trip,
         "actual_arrive": BASE + timedelta(minutes=arrive_min), "stop_seq": seq}
    if dep_min is not None:
        a["scheduled"] = BASE + timedelta(minutes=dep_min)
    return a


def test_classify_bunching():
    assert classify_gap(2.0, 8.0, 3.0, 15.0)[0] == "bunching"


def test_classify_large():
    assert classify_gap(16.0, 8.0, 3.0, 15.0)[0] == "large_gap"


def test_classify_normal():
    assert classify_gap(8.0, 8.0, 3.0, 15.0)[0] == "normal"


def test_detect_bunching_events():
    arrivals = [
        arr("T1", 0),
        arr("T2", 2),
        arr("T3", 20),
    ]
    # 旧调用方不带计划发车与带宽：只判间隔。
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0)
    assert len(events) == 2
    assert events[0].status == "bunching"
    assert events[1].status == "large_gap"


def test_late_deviation_flagged_and_excluded_from_pairing():
    arrivals = [
        arr("T1", 0, 0),
        arr("T2", 16, 8),    # 计划 8，晚到 +8，超出晚到带宽 5 → 偏离
        arr("T3", 16.5, 16),
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0, early_tolerance_min=3.0, late_tolerance_min=5.0)
    devs = [e for e in events if e.kind == "deviation"]
    pairs = [e for e in events if e.kind != "deviation"]
    assert len(devs) == 1
    d = devs[0]
    assert d.earlier_trip == "T2"
    assert d.direction == "late"
    assert d.deviation_min == 8.0
    # T2 不参与任何邻班配对：配对中不得出现 T2。
    assert all("T2" not in (p.earlier_trip, p.later_trip) for p in pairs)
    # 剔除 T2 后，带宽内的 T1 与 T3 直接按间隔配对（16.5 分钟 → 大间隔）。
    assert [(p.earlier_trip, p.later_trip, p.status) for p in pairs] == [("T1", "T3", "large_gap")]


def test_early_deviation_flagged():
    arrivals = [
        arr("T1", 2, 10),    # 计划 10，早到 -8，超出早到带宽 3 → 偏离
        arr("T2", 16, 16),
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0, early_tolerance_min=3.0, late_tolerance_min=5.0)
    devs = [e for e in events if e.kind == "deviation"]
    assert len(devs) == 1
    assert devs[0].direction == "early"
    assert devs[0].deviation_min == -8.0
    # 早到班被剔除，只剩 T2 无邻班可配。
    assert [e for e in events if e.kind != "deviation"] == []


def test_within_band_still_pairs():
    arrivals = [
        arr("T1", 2, 0),     # 晚到 +2，在晚到带宽 5 内
        arr("T2", 6, 8),     # 早到 -2，在早到带宽 3 内
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0, early_tolerance_min=3.0, late_tolerance_min=5.0)
    assert [e for e in events if e.kind == "deviation"] == []
    assert len(events) == 1
    assert events[0].status == "normal"


def test_zero_bandwidths_behave_like_gap_only():
    arrivals = [
        arr("T1", 0, 0),
        arr("T2", 2, 8),     # 早到 6 分钟，但两带宽为 0 → 不判偏离
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0, early_tolerance_min=0.0, late_tolerance_min=0.0)
    assert all(e.kind != "deviation" for e in events)
    assert len(events) == 1
    assert events[0].status == "bunching"


def test_missing_scheduled_falls_back_to_gaps():
    arrivals = [
        arr("T1", 0),
        arr("T2", 2),
        arr("T3", 20),
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0, early_tolerance_min=3.0, late_tolerance_min=5.0)
    assert all(e.kind != "deviation" for e in events)
    assert [e.status for e in events] == ["bunching", "large_gap"]


def test_scheduled_includes_planned_travel_to_later_stop():
    arrivals = [
        arr("T1", 0, 0, seq=0, stop="A"),
        arr("T1", 6, 0, seq=1, stop="B"),
        arr("T2", 10, 10, seq=0, stop="A"),
        arr("T2", 23, 10, seq=1, stop="B"),   # 计划到站 10 + 计划走行 6 = 16，晚到 7 → 偏离
        arr("T3", 20, 20, seq=0, stop="A"),
        arr("T3", 26, 20, seq=1, stop="B"),
    ]
    # 三班车的 A→B 走行为 6 / 13 / 6 分钟，计划走行取中位数 6。
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0, early_tolerance_min=3.0, late_tolerance_min=5.0)
    b_devs = [e for e in events if e.kind == "deviation" and e.stop_name == "B"]
    assert len(b_devs) == 1
    assert b_devs[0].earlier_trip == "T2"
    assert b_devs[0].deviation_min == 7.0
    # B 站 T2 被剔除，T1、T3 直接配对（20 分钟 → 大间隔）。
    b_pairs = [(p.earlier_trip, p.later_trip, p.status)
               for p in events if p.stop_name == "B" and p.kind != "deviation"]
    assert b_pairs == [("T1", "T3", "large_gap")]
    # A 站三班均在带宽内，相邻两两配对，间隔正常。
    a_pairs = [e for e in events if e.stop_name == "A" and e.kind != "deviation"]
    assert len(a_pairs) == 2
    assert all(p.status == "normal" for p in a_pairs)
