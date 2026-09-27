from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Line
router = APIRouter(prefix="/lines", tags=["lines"])


def _line_dict(r: Line) -> dict:
    return {"id": r.id, "code": r.code, "name": r.name,
            "planned_headway_min": r.planned_headway_min,
            "bunch_threshold": r.bunch_threshold,
            "large_threshold": r.large_threshold,
            "early_tolerance_min": r.early_tolerance_min,
            "late_tolerance_min": r.late_tolerance_min}


@router.get("")
def list_lines(db: Session = Depends(get_db)):
    rows = db.scalars(select(Line).order_by(Line.id)).all()
    return [_line_dict(r) for r in rows]


class LineUpdate(BaseModel):
    early_tolerance_min: float | None = None
    late_tolerance_min: float | None = None


@router.patch("/{line_id}")
def update_line(line_id: int, payload: LineUpdate, db: Session = Depends(get_db)):
    line = db.get(Line, line_id)
    if not line:
        raise HTTPException(404, "线路不存在")
    if payload.early_tolerance_min is not None:
        if payload.early_tolerance_min < 0:
            raise HTTPException(422, "允许早到分钟不能为负")
        line.early_tolerance_min = payload.early_tolerance_min
    if payload.late_tolerance_min is not None:
        if payload.late_tolerance_min < 0:
            raise HTTPException(422, "允许晚到分钟不能为负")
        line.late_tolerance_min = payload.late_tolerance_min
    db.commit()
    return _line_dict(line)
