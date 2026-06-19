from __future__ import annotations

import pytest
from sqlmodel import Session

from app.db import engine, init_db
from app.strategies import library
from app.strategies.spec import StrategySpec


def _spec() -> StrategySpec:
    return StrategySpec.model_validate({
        "indicators": [{"id": "c", "kind": "close", "args": {}}],
        "entry": {"kind": "cmp", "left": {"type": "indicator", "ref": "c"},
                  "op": "gt", "right": {"type": "literal", "value": 0}},
        "exit": {"kind": "cmp", "left": {"type": "indicator", "ref": "c"},
                 "op": "lt", "right": {"type": "literal", "value": 0}},
        "params": [],
    })


def test_crud_round_trip():
    init_db()
    with Session(engine) as s:
        created = library.save_strategy(s, "t1", _spec(), description="d", source="manual")
        assert created.id is not None
        assert library.get_strategy(s, created.id).name == "t1"
        assert any(x.id == created.id for x in library.list_strategies(s))
        loaded = library.load_spec(s, created.id)
        assert loaded.indicators[0].kind.value == "close"
        library.update_strategy(s, created.id, name="t2")
        assert library.get_strategy(s, created.id).name == "t2"
        assert library.delete_strategy(s, created.id) is True
        assert library.get_strategy(s, created.id) is None


def test_load_missing_fails_loud():
    init_db()
    with Session(engine) as s:
        with pytest.raises(ValueError):
            library.load_spec(s, 999999)
