import asyncio
import json
from typing import Any, Dict, Optional, Callable
from game_sdk.game.agent import Agent, WorkerConfig
from game_sdk.game.custom_types import Function,  FunctionResult, FunctionResultStatus
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from plugins.acp.acp_plugin_gamesdk import acp_plugin
from plugins.acp.acp_plugin_gamesdk.acp_plugin import AcpPlugin, AdNetworkPluginOptions
from plugins.acp.acp_plugin_gamesdk.acp_token import AcpToken


acp_api_key = os.environ.get("ACP_API_KEY")
acp_client_api_key = os.environ.get("ACP_CLIENT_API_KEY")
game_api_key = os.environ.get("GAME_API_KEY")

async def ask_question(query: str) -> str:
    print(query, end='')
    return input()

async def post_tweet(args: Dict[str, Any], logger: callable) -> FunctionResult:
    logger("Posting tweet...")
    logger(f"Content: {args['content']}. Reasoning: {args['reasoning']}")

    return FunctionResult(
        FunctionResultStatus.DONE,
        "Tweet has been posted"
    )

async def main():
    acp_plugin = AcpPlugin(
        options=AdNetworkPluginOptions(
            api_key=acp_api_key,
            acp_token_client=AcpToken(
                acp_client_api_key,
                "base_sepolia"  # Assuming this is the chain identifier
            )
        )
    )

    async def get_agent_state(_: Any, _e: Any) -> dict:
        state = await acp_plugin.get_acp_state()
        return state

    core_worker = WorkerConfig(
        id="core-worker",
        worker_description="This worker is to post tweet",
        action_space=[
            Function(
                fn_name="post_tweet",
                fn_description="This function is to post tweet",
                args=[
                    {
                        "name": "content",
                        "type": "string",
                        "description": "The content of the tweet"
                    },
                    {
                        "name": "reasoning",
                        "type": "string",
                        "description": "The reasoning of the tweet"
                    }
                ],
                executable=post_tweet
            )
        ],
        get_state_fn=get_agent_state
    )

    acp_worker = await acp_plugin.get_worker()
    agent = await Agent.create_async(
        api_key=game_api_key,
        name="Virtuals",
        agent_goal="Finding the best meme to do tweet posting",
        agent_description=f"""
        Agent that gain market traction by posting meme. Your interest are in cats and AI.
        You can head to acp to look for agents to help you generating meme.

        {acp_plugin.agent_description}
        """,
        workers=[core_worker, acp_worker],
        get_agent_state_fn=get_agent_state
    )

    await agent.compile_async()
    agent.run()

    while True:
        await agent.step()
        await ask_question("\nPress any key to continue...\n")

if __name__ == "__main__":
    asyncio.run(main())