from datetime import datetime, timedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.models import Arrival, Line, Trip

def seed_if_empty(db: Session) -> None:
    if (db.scalar(select(func.count()).select_from(Line)) or 0) > 0:
        return
    base = datetime(2026, 9, 17, 7, 0, 0)
    line = Line(code="B12", name="城东环线", planned_headway_min=8.0, bunch_threshold=3.0,
                large_threshold=15.0, early_tolerance_min=3.0, late_tolerance_min=5.0)
    db.add(line); db.flush()
    specs = [("T01", "粤A1001", 0), ("T02", "粤A1002", 2), ("T03", "粤A1003", 18), ("T04", "粤A1004", 26)]
    stops = ["起点站", "市民中心", "火车站", "终点站"]
    # 相对计划到站（计划发车 + 每站 6 分钟计划走行）的扰动样例；
    # 两班都只在市民中心偏离、后续站恢复，计划走行中位数仍为每区间 6 分钟。
    overrides = {
        ("T03", "市民中心"): 31,   # 计划 24，晚到 7 分钟，超出晚到带宽 5 → 偏离
        ("T04", "市民中心"): 27,   # 计划 32，早到 5 分钟，超出早到带宽 3 → 偏离
    }
    for trip_no, vehicle, offset in specs:
        trip = Trip(line_id=line.id, trip_no=trip_no, planned_depart=base + timedelta(minutes=offset), vehicle_no=vehicle)
        db.add(trip); db.flush()
        for seq, stop in enumerate(stops):
            arrive = base + timedelta(minutes=offset + seq * 6)
            if (trip_no, stop) in overrides:
                arrive = base + timedelta(minutes=overrides[(trip_no, stop)])
            if stop == "市民中心" and trip_no == "T02":
                arrive = base + timedelta(minutes=8)
            db.add(Arrival(trip_id=trip.id, stop_name=stop, stop_seq=seq, actual_arrive=arrive))
    db.commit()
