"""Tool-documentation replacement, reads and clearing through both SDK clients."""

from conftest import TEST_KEY, MockGateway
from ultrarouter import AsyncUltraRouter, UltraRouter


def test_replace_read_clear(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        result = client.learning.put_tool_documentation(
            "ct_1", tools=[{"type": "function", "function": {"name": "reserve_stock"}}]
        )
        assert result.tool_count == 1 and result.digest is not None
        assert client.learning.tool_documentation("ct_1").digest == result.digest
        cleared = client.learning.put_tool_documentation("ct_1", tools=[])
        assert cleared.tool_count == 0 and cleared.digest is None
    puts = [r for r in mock_gateway.requests if r["method"] == "PUT"]
    assert puts[0]["body"]["tools"][0]["function"]["name"] == "reserve_stock"
    assert puts[1]["body"] == {"tools": []}


async def test_async_replace_read_clear(mock_gateway: MockGateway) -> None:
    async with AsyncUltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        result = await client.learning.put_tool_documentation(
            "ct_1", tools=[{"type": "function", "function": {"name": "reserve_stock"}}]
        )
        assert (await client.learning.tool_documentation("ct_1")).digest == result.digest
        assert (await client.learning.put_tool_documentation("ct_1", tools=[])).tool_count == 0
