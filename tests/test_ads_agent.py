"""Unit tests for agents/ads_agent.py."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from agents.ads_agent import AdsAgent, AdsAnalysis, AdsRequest, CampaignMetrics, PerformanceStatus
from agents.context import AgentContext
from agents.contracts import AgentResult
from core.ai.exceptions import GenAIModelError


@pytest.fixture
def mock_genai_client():
    client = MagicMock()
    client.default_model = "gemini-2.5-flash"
    return client


def test_ads_agent_initialization(mock_genai_client):
    agent = AdsAgent(genai_client=mock_genai_client)
    assert agent.agent_id == "ads-agent"
    assert agent.name == "Ads Agent"
    assert "Ads Analytics" in agent.system_instruction


def test_ads_request_contract_valid():
    metrics = CampaignMetrics(impressions=1000, clicks=50, spend=100.0, revenue=300.0, roas=3.0)
    req = AdsRequest(campaign_id="cmp-123", metrics=metrics, objective="Maximize ROAS")
    assert req.campaign_id == "cmp-123"
    assert req.metrics.spend == 100.0
    assert req.metrics.roas == 3.0


@pytest.mark.anyio
async def test_ads_agent_execute_success(mock_genai_client):
    expected_analysis = AdsAnalysis(
        summary="Campaign cmp-123 is performing strongly with ROAS of 3.2.",
        performance_status=PerformanceStatus.EXCELLENT,
        key_findings=["CTR is above benchmark at 5.0%", "ROAS targets exceeded"],
        anomalies=[],
        recommendations=["Increase daily budget by 15%"],
        missing_data=[],
        requires_human_approval=True,
        confidence=0.92,
    )
    mock_genai_client.generate_structured_async = AsyncMock(return_value=expected_analysis)

    ads_agent = AdsAgent(genai_client=mock_genai_client)
    context = AgentContext()

    metrics = CampaignMetrics(impressions=10000, clicks=500, spend=200.0, revenue=640.0, ctr=5.0, roas=3.2)
    request = AdsRequest(campaign_id="cmp-123", metrics=metrics)

    result = await ads_agent.execute(request, context)

    assert isinstance(result, AgentResult)
    assert result.success is True
    assert result.agent_id == "ads-agent"
    assert result.output["performance_status"] == "EXCELLENT"
    assert "Increase daily budget by 15%" in result.output["recommendations"]


@pytest.mark.anyio
async def test_ads_agent_execute_missing_metrics(mock_genai_client):
    expected_analysis = AdsAnalysis(
        summary="Campaign data is missing financial metric 'spend'.",
        performance_status=PerformanceStatus.INSUFFICIENT_DATA,
        key_findings=[],
        anomalies=[],
        recommendations=["Provide financial metrics before budget optimization"],
        missing_data=["spend", "roas"],
        requires_human_approval=True,
        confidence=0.85,
    )
    mock_genai_client.generate_structured_async = AsyncMock(return_value=expected_analysis)

    ads_agent = AdsAgent(genai_client=mock_genai_client)
    context = AgentContext()

    request = AdsRequest(campaign_id="cmp-999", metrics=CampaignMetrics(impressions=100))

    result = await ads_agent.execute(request, context)

    assert result.success is True
    assert result.output["performance_status"] == "INSUFFICIENT_DATA"
    assert "spend" in result.output["missing_data"]


@pytest.mark.anyio
async def test_ads_agent_validation_failure(mock_genai_client):
    mock_genai_client.generate_structured_async = AsyncMock(
        side_effect=GenAIModelError("Structured parsing error")
    )

    ads_agent = AdsAgent(genai_client=mock_genai_client)
    context = AgentContext()

    result = await ads_agent.execute(AdsRequest(campaign_id="cmp-err"), context)

    assert result.success is False
    assert "AdsAgent execution failed" in result.error
