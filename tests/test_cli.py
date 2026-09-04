"""Unit tests for CLI Interaction Layer."""

import io
import pytest

from app_factory import build_application
from cli import CLIApplication, CLIOutputFormatter
from orchestrator import ExecutionStatus, ExecutionTraceEntry, OrchestrationResult


def test_cli_output_formatter():
    buf = io.StringIO()
    formatter = CLIOutputFormatter(out_stream=buf)

    trace_entry = ExecutionTraceEntry(
        request_id="req-123",
        agent_id="cs-agent",
        event="Processing query",
        status=ExecutionStatus.RUNNING,
    )
    formatter.print_trace_entry(trace_entry)

    res = OrchestrationResult(
        request_id="req-123",
        success=True,
        final_response="Output completed.",
        status=ExecutionStatus.COMPLETED,
    )
    formatter.print_result(res)

    output = buf.getvalue()
    assert "[CS] Processing query" in output
    assert "[RESULT] Request ID: req-123" in output
    assert "Output completed." in output


@pytest.mark.asyncio
async def test_cli_application_commands():
    orchestrator = build_application(simulation_mode=True)
    buf = io.StringIO()
    formatter = CLIOutputFormatter(out_stream=buf)
    cli_app = CLIApplication(orchestrator=orchestrator, formatter=formatter)

    cli_app.show_status()
    assert "Active Agents Registered: 4" in buf.getvalue()

    cli_app.show_agents()
    assert "owner: Owner Agent" in buf.getvalue()

    result = await cli_app.execute_instruction("Analyze customer support")
    assert result.success is True
