"""Unit tests for V1 AgentResult and AgentRequest contracts."""

from app.agents.contracts import AgentRequest, AgentResult


def test_agent_result_v1_schema():
    """Test V1 AgentResult model instantiation and validation."""
    res = AgentResult(
        task_id="task_1001",
        status="COMPLETED",
        finding="Order #12345 has been refunded.",
        evidence=["Refund transaction ID: tx_999"],
        confidence=0.98,
        recommendation="Notify customer via email.",
        next_action="Send email template",
    )

    assert res.task_id == "task_1001"
    assert res.status == "COMPLETED"
    assert res.finding == "Order #12345 has been refunded."
    assert res.evidence == ["Refund transaction ID: tx_999"]
    assert res.confidence == 0.98
    assert res.recommendation == "Notify customer via email."
    assert res.next_action == "Send email template"
    assert res.success is True


def test_agent_result_legacy_compatibility():
    """Test that AgentResult maintains compatibility with success boolean and output dict."""
    res = AgentResult(
        success=True,
        agent_id="cs-agent",
        request_id="req_500",
        output={"finding": "General support response"},
    )

    assert res.status == "COMPLETED"
    assert res.finding == "General support response"
    assert res.agent_id == "cs-agent"
    assert res.request_id == "req_500"
    assert res.success is True
