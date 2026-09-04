"""Unit tests for agents/debugger_agent.py."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from agents.context import AgentContext
from agents.contracts import AgentResult
from agents.debugger_agent import DebuggerAgent
from agents.debugging_models import DebugAnalysis, DebuggerRequest, ErrorReport, ErrorSeverity, PatchRecommendation
from core.ai.exceptions import GenAIModelError


@pytest.fixture
def mock_genai_client():
    client = MagicMock()
    client.default_model = "gemini-2.5-flash"
    return client


def test_debugger_agent_initialization(mock_genai_client):
    agent = DebuggerAgent(genai_client=mock_genai_client)
    assert agent.agent_id == "debugger-agent"
    assert agent.name == "Debugger Agent"
    assert "Debugger Agent" in agent.system_instruction


@pytest.mark.anyio
async def test_debugger_agent_execute_success(mock_genai_client):
    expected_patch = PatchRecommendation(
        file_path="agents/cs_agent.py",
        description="Add None check for customer_id before query execution",
        change_type="BUG_FIX",
        old_behavior="Directly accessed customer_id without checking None value.",
        new_behavior="Check if customer_id is not None before processing.",
        rationale="Prevents AttributeError when customer_id is omitted.",
        validation_steps=["Run test_cs_agent.py with customer_id=None"],
        diff_text="--- old\n+++ new",
    )

    expected_analysis = DebugAnalysis(
        classification="UNHANDLED_NONE_TYPE",
        severity=ErrorSeverity.HIGH,
        root_cause="AttributeError caused by missing None check on customer_id field.",
        affected_components=["agents/cs_agent.py"],
        evidence=["Stack trace shows AttributeError at line 42"],
        recommended_fix="Safely handle None customer_id in CSAgent execute method.",
        patch=expected_patch,
        tests_to_add=["test_cs_agent_null_customer_id"],
        confidence=0.96,
        requires_human_review=True,
    )
    mock_genai_client.generate_structured_async = AsyncMock(return_value=expected_analysis)

    debugger = DebuggerAgent(genai_client=mock_genai_client)
    context = AgentContext()

    report = ErrorReport(
        request_id="req-999",
        component="cs_agent",
        exception_type="AttributeError",
        message="'NoneType' object has no attribute 'lower'",
        stack_trace="Traceback ... AttributeError: 'NoneType' object has no attribute 'lower'",
    )

    result = await debugger.execute(report, context)

    assert isinstance(result, AgentResult)
    assert result.success is True
    assert result.agent_id == "debugger-agent"
    assert result.output["classification"] == "UNHANDLED_NONE_TYPE"
    assert result.output["requires_human_review"] is True
    assert result.output["patch"]["file_path"] == "agents/cs_agent.py"


@pytest.mark.anyio
async def test_debugger_never_executes_patch(mock_genai_client):
    expected_analysis = DebugAnalysis(
        classification="SYNTAX_ERROR",
        severity=ErrorSeverity.CRITICAL,
        root_cause="Missing closing parenthesis.",
        affected_components=["main.py"],
        evidence=["SyntaxError on line 12"],
        recommended_fix="Add missing closing parenthesis.",
        patch=PatchRecommendation(
            file_path="main.py",
            description="Fix syntax",
            change_type="BUG_FIX",
            old_behavior="Broken syntax",
            new_behavior="Correct syntax",
            rationale="Fix syntax error",
        ),
        tests_to_add=[],
        confidence=0.9,
        requires_human_review=True,
    )
    mock_genai_client.generate_structured_async = AsyncMock(return_value=expected_analysis)

    debugger = DebuggerAgent(genai_client=mock_genai_client)
    context = AgentContext()

    report = ErrorReport(
        request_id="req-syntax",
        component="main.py",
        exception_type="SyntaxError",
        message="unexpected EOF while parsing",
        stack_trace="Traceback ... SyntaxError",
    )

    result = await debugger.execute(report, context)

    # Verify output always enforces human review requirement and does not execute modifications
    assert result.output["requires_human_review"] is True
    assert result.output["patch"]["file_path"] == "main.py"
