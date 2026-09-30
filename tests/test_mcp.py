import asyncio
from unittest import TestCase
from unittest.mock import patch
from mcp import Client
from integrations.mcp_server import mcp
from integrations.enlace_client import EnlaceUnavailable

class MCPContractTests(TestCase):
    def test_discovery_and_typed_tool_contract(self):
        async def scenario():
            async with Client(mcp) as client:
                listed=await client.list_tools()
                names={tool.name for tool in listed.tools}
                self.assertIn('search_capabilities',names);self.assertIn('assess_goal',names);self.assertNotIn('run_shell',names)
                with patch('integrations.mcp_server.client') as connection:
                    connection.return_value.call.return_value={'results':[{'id':'stable-node','project_id':'stable-project'}]}
                    response=await client.call_tool('search_capabilities',{'objective':'criar site'})
                    self.assertEqual(response.structured_content['results'][0]['id'],'stable-node')
                    connection.return_value.call.assert_called_once_with('search',question='criar site')
        asyncio.run(scenario())
    def test_disconnected_is_an_error(self):
        async def scenario():
            async with Client(mcp) as client:
                with patch('integrations.mcp_server.client') as connection:
                    connection.return_value.call.side_effect=EnlaceUnavailable('Central indisponível')
                    response=await client.call_tool('search_capabilities',{'objective':'criar site'})
                    self.assertTrue(response.is_error)
        asyncio.run(scenario())
