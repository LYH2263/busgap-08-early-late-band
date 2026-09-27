"""Bus bunching: schedule-deviation band + planned headway vs actual arrival gaps."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from statistics import median


@dataclass
class GapEvent:
    stop_name: str
    earlier_trip: str
    later_trip: str
    gap_min: float
    planned_headway_min: float
    status: str
    suggestion: str
    kind: str = "pair"
    deviation_min: float = 0.0
    scheduled_arrive: str = ""
    direction: str = ""


# 兼容旧测试的调用签名：按计划间隔与现网阈值判定两班间隔。
def classify_gap(gap_min: float, planned_headway_min: float, bunch_threshold: float, large_threshold: float) -> tuple[str, str]:
    if gap_min < bunch_threshold:
        return ("bunching", f"间隔 {gap_min:.1f} 分钟低于串车阈值 {bunch_threshold}，建议后车缓行或抽稀。")
    if gap_min > large_threshold:
        return ("large_gap", f"间隔 {gap_min:.1f} 分钟超过大间隔阈值 {large_threshold}，建议前车减速或加发。")
    return ("normal", f"间隔接近计划 {planned_headway_min:.1f} 分钟，保持即可。")


def _infer_scheduled_arrivals(arrivals: list[dict]) -> dict[tuple[str, str], datetime]:
    """以「计划发车 + 沿途计划走行」推导各班在各站的计划到站时刻。

    计划发车取自 scheduled/planned_depart；沿途计划走行按 stop_seq 用各班
    实际走行时长的中位数估计（中位数对个别早到晚到的班次稳健）。
    缺少计划发车的班次不推导（不在返回表中的班对，调用方按只判间隔处理）。
    """
    planned_depart: dict[str, datetime] = {}
    seq_of: dict[tuple[str, str], int] = {}

    for a in arrivals:
        dep = a.get("scheduled") or a.get("planned_depart")
        seq = a.get("stop_seq")
        if dep is not None:
            planned_depart.setdefault(a["trip_no"], dep)
        if seq is not None:
            seq_of[(a["trip_no"], a["stop_name"])] = seq
    if not planned_depart or not seq_of:
        return {}

    # 各班按站序排列，收集相邻站之间的实际走行秒数。
    per_trip: dict[str, list[tuple[int, datetime]]] = {}
    for a in arrivals:
        if a.get("stop_seq") is None:
            continue
        per_trip.setdefault(a["trip_no"], []).append((a["stop_seq"], a["actual_arrive"]))
    leg_seconds: dict[int, list[float]] = {}
    for legs in per_trip.values():
        legs.sort(key=lambda x: x[0])
        for (prev_seq, prev_at), (seq, at) in zip(legs, legs[1:]):
            if seq == prev_seq + 1:
                leg_seconds.setdefault(prev_seq, []).append((at - prev_at).total_seconds())
    leg_median = {seq: median(vals) for seq, vals in leg_seconds.items()}

    scheduled: dict[tuple[str, str], datetime] = {}
    for (trip_no, stop_name), seq in seq_of.items():
        dep = planned_depart.get(trip_no)
        if dep is None:
            continue
        offset = sum(leg_median.get(s, 0.0) for s in range(seq))
        scheduled[(trip_no, stop_name)] = dep + timedelta(seconds=offset)
    return scheduled


def _deviation_event(stop_name: str, trip_no: str, deviation_min: float,
                     scheduled_arrive: datetime, early: float, late: float) -> GapEvent:
    if deviation_min < 0:
        detail = f"早到 {-deviation_min:.1f} 分钟，超出允许早到 {early:.0f} 分钟"
    else:
        detail = f"晚到 {deviation_min:.1f} 分钟，超出允许晚到 {late:.0f} 分钟"
    return GapEvent(
        stop_name=stop_name,
        earlier_trip=trip_no,
        later_trip=trip_no,
        gap_min=0.0,
        planned_headway_min=0.0,
        status="deviation",
        suggestion=f"该班在该站相对计划到站{detail}，先按偏离处理，不参与串车/大间隔配对。",
        kind="deviation",
        deviation_min=round(deviation_min, 2),
        scheduled_arrive=scheduled_arrive.isoformat(),
        direction="early" if deviation_min < 0 else "late",
    )


def detect_bunching(arrivals: list[dict], planned_headway_min: float, bunch_threshold: float,
                    large_threshold: float, early_tolerance_min: float = 0.0,
                    late_tolerance_min: float = 0.0) -> list[GapEvent]:
    # 两带宽都为 0 时不做偏离判定，行为与只判间隔时一致。
    check_deviation = early_tolerance_min > 0 or late_tolerance_min > 0
    scheduled = _infer_scheduled_arrivals(arrivals) if check_deviation else {}

    by_stop: dict[str, list[dict]] = {}
    for a in arrivals:
        by_stop.setdefault(a["stop_name"], []).append(a)

    events: list[GapEvent] = []
    for stop, items in by_stop.items():
        items = sorted(items, key=lambda x: x["actual_arrive"])
        in_band: list[dict] = []
        for a in items:
            if check_deviation and (a["trip_no"], stop) in scheduled:
                planned_at = scheduled[(a["trip_no"], stop)]
                deviation_min = (a["actual_arrive"] - planned_at).total_seconds() / 60.0
                # 早到偏差为负：早到超过 early 才算偏离；晚到偏差为正：超过 late 才算偏离。
                is_off = deviation_min < -early_tolerance_min or deviation_min > late_tolerance_min
                if is_off:
                    events.append(_deviation_event(stop, a["trip_no"], deviation_min,
                                                   planned_at, early_tolerance_min, late_tolerance_min))
                    continue  # 偏离班次不参与与邻班的串车/大间隔配对
            in_band.append(a)

        for i in range(1, len(in_band)):
            prev, cur = in_band[i - 1], in_band[i]
            gap_min = (cur["actual_arrive"] - prev["actual_arrive"]).total_seconds() / 60.0
            status, suggestion = classify_gap(gap_min, planned_headway_min, bunch_threshold, large_threshold)
            events.append(GapEvent(stop, prev["trip_no"], cur["trip_no"], round(gap_min, 2),
                                   planned_headway_min, status, suggestion))
    return events


def events_to_dicts(events: list[GapEvent]) -> list[dict]:
    return [asdict(e) for e in events]
