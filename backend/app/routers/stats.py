import statistics
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import BenchStat, OutcomesByYear
from models.case import Case
from models.enums import OutcomeEnum
from models.order import Order

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


@router.get("/benches", response_model=list[BenchStat])
def get_bench_stats(db: Session = Depends(get_db)) -> list[BenchStat]:
    cases = list(db.execute(select(Case).where(Case.bench.isnot(None))).scalars())

    by_bench: dict[str, list[Case]] = defaultdict(list)
    for case in cases:
        if case.bench:
            by_bench[case.bench].append(case)

    stats = []
    for bench, bench_cases in sorted(by_bench.items()):
        durations = [
            (c.latest_order_date - c.first_order_date).days
            for c in bench_cases
            if c.first_order_date and c.latest_order_date
        ]
        median_duration = statistics.median(durations) if durations else None
        stats.append(
            BenchStat(
                bench=bench,
                case_count=len(bench_cases),
                median_duration_days=median_duration,
            )
        )

    return stats


@router.get("/outcomes-by-year", response_model=list[OutcomesByYear])
def get_outcomes_by_year(db: Session = Depends(get_db)) -> list[OutcomesByYear]:
    orders = list(
        db.execute(select(Order).where(Order.order_date.isnot(None))).scalars()
    )

    counts: dict[tuple[int, OutcomeEnum], int] = defaultdict(int)
    for order in orders:
        if order.order_date:
            counts[(order.order_date.year, order.outcome)] += 1

    return [
        OutcomesByYear(year=year, outcome=outcome, count=count)
        for (year, outcome), count in sorted(counts.items())
    ]
