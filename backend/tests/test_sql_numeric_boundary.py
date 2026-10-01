"""PostgreSQL SUM(bigint) returns Decimal; normalize every public aggregate scalar."""
from decimal import Decimal
from types import SimpleNamespace
import json
from app.accounting import energy_projection
from app.energy_sql import hourly_totals
from app.db import utcnow


def test_hourly_aggregate_does_not_expose_driver_specific_decimals(app,monkeypatch):
    application,_=app
    with application.state.session_factory() as db:
        _,_,_,projection,_=energy_projection(db)
        rows=[SimpleNamespace(timestamp=utcnow(),known_kwh=Decimal('1.25'),active_kw=Decimal('2.5'),seconds=Decimal('1800'),interval_count=Decimal('1'),observed_device_count=1)]
        monkeypatch.setattr(db,'execute',lambda query:rows)
        result=hourly_totals(db,projection)
        json.dumps(result,allow_nan=False)
        assert type(result[0]['interval_count']) is int
        assert type(result[0]['known_kwh']) is float
        assert type(result[0]['active_kw']) is float
