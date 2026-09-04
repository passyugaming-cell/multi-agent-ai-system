"""Unit tests for agents/debugging_loop.py."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from agents.context import AgentContext
from agents.contracts import AgentResult
from agents.debugger_agent import DebuggerAgent
from agents.debugging_loop import SelfDebuggingLoop
from agents.debugging_models import DebugAnalysis, ErrorSeverity, PatchRecommendation


@pytest.fixture
def mock_debugger_agent():
    agent = MagicMock(spec=DebuggerAgent)
    agent.agent_id = "debugger-agent"
    return agent


@pytest.mark.anyio
async def test_self_debugging_loop_success(mock_debugger_agent):
    analysis_output = DebugAnalysis(
        classification="ZERO_DIVISION",
        severity=ErrorSeverity.HIGH,
        root_cause="Division by zero when spend is zero.",
        affected_components=["agents/ads_agent.py"],
        evidence=["ZeroDivisionError in calculate_cpc"],
        recommended_fix="Check if spend > 0 before dividing.",
        patch=PatchRecommendation(
            file_path="agents/ads_agent.py",
            description="Add zero check for spend",
            change_type="BUG_FIX",
            old_behavior="Divided by zero spend",
            new_behavior="Return 0 if spend is 0",
            rationale="Avoid ZeroDivisionError",
        ),
        tests_to_add=["test_ads_agent_zero_spend"],
        confidence=0.98,
        requires_human_review=True,
    )

    mock_debugger_agent.execute = AsyncMock(
        return_value=AgentResult(
            success=True,
            agent_id="debugger-agent",
            request_id="req-loop-1",
            output=analysis_output.model_dump(),
        )
    )

    loop = SelfDebuggingLoop(debugger_agent=mock_debugger_agent, max_attempts=3)
    context = AgentContext(request_id="req-loop-1")

    try:
        x = 1 / 0
    except ZeroDivisionError as exc:
        result = await loop.analyze_exception(
            exc=exc,
            component="ads_agent",
            context=context,
            attempt_count=1,
        )

    assert result.success is True
    assert result.output["classification"] == "ZERO_DIVISION"
    assert result.output["requires_human_review"] is True
    assert mock_debugger_agent.execute.called


@pytest.mark.anyio
async def test_self_debugging_loop_max_attempts_exceeded(mock_debugger_agent):
    loop = SelfDebuggingLoop(debugger_agent=mock_debugger_agent, max_attempts=3)
    context = AgentContext(request_id="req-loop-limit")

    exc = KeyError("missing_key")

    result = await loop.analyze_exception(
        exc=exc,
        component="cs_agent",
        context=context,
        attempt_count=4,  # Exceeds max_attempts=3
    )

    assert result.success is False
    assert "exceeded max attempts" in result.error
    assert result.metadata["max_attempts_exceeded"] is True
    assert not mock_debugger_agent.execute.called
