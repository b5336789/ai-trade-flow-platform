"""WorkflowRun + WorkflowSignal persist and round-trip."""

from __future__ import annotations

from sqlmodel import Session, select

from app.db import engine
from app.models import WorkflowRun, WorkflowSignal


def test_workflow_run_and_signal_roundtrip():
    with Session(engine) as s:
        run = WorkflowRun(
            run_id="abc123",
            kind="backtest",
            graph_json={"nodes": [], "edges": []},
            market="crypto",
            symbols=["BTC/USDT", "ETH/USDT"],
            timeframe="1h",
            starting_cash=100_000.0,
            params_json={"limit": 500},
            metrics_json={"total_return_pct": 1.5},
            equity_curve_json=[{"timestamp": "t", "equity": 100.0}],
            trades_json=[],
            status="ok",
        )
        s.add(run)
        s.commit()
        s.refresh(run)
        s.add(
            WorkflowSignal(
                run_id=run.id,
                order_node_id="o",
                symbol="BTC/USDT",
                timestamp="2024-01-01T00:00:00+00:00",
                bar_index=3,
                action="buy",
                confidence=0.8,
                price=9.0,
                trace_json=[{"node_id": "s", "type": "strategy", "summary": {"signal": {"action": "buy"}}}],
            )
        )
        s.commit()

        got = s.exec(select(WorkflowSignal).where(WorkflowSignal.run_id == run.id)).all()
        assert len(got) == 1
        assert got[0].action == "buy"
        assert got[0].trace_json[0]["node_id"] == "s"
        assert run.symbols == ["BTC/USDT", "ETH/USDT"]
