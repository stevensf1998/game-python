import asyncio
import os
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass

from acp_plugin_gamesdk.acp_plugin import AcpPlugin, AdNetworkPluginOptions
from acp_plugin_gamesdk.acp_token import AcpToken

# from game_sdk.game.worker import Worker
from game_sdk.game.custom_types import Function
from game_sdk.game.agent import Agent, WorkerConfig
# from game_sdk.game.worker import ExecutableGameFunctionResponse, ExecutableGameFunctionStatus


class ExecutableGameFunctionResponse:
    def __init__(self, status: str, feedback: str):
        self.status = status
        self.feedback = feedback

    def to_json(self, id: str) -> dict:
        return {
            "action_id": id,
            "action_status": self.status,
            "feedback_message": self.feedback,
        }

class ExecutableGameFunctionStatus(Enum):
    DONE = "done"
    FAILED = "failed"


acp_api_key = os.environ.get("ACP_API_KEY")
acp_client_api_key = os.environ.get("ACP_CLIENT_API_KEY")
game_api_key = os.environ.get("GAME_API_KEY")

def ask_question(query: str) -> str:
    return input(query)

async def generate_meme(args: Dict[str, Any], logger, acp_plugin) -> ExecutableGameFunctionResponse:
    logger("Generating meme...")

    if not args["jobId"]:
        return ExecutableGameFunctionResponse(
            ExecutableGameFunctionStatus.FAILED,
            f"Job {args['jobId']} is invalid. Should only respond to active as a seller job."
        )

    state = await acp_plugin.get_acp_state()

    job = next(
        (j for j in state.jobs.active.as_a_seller if j.job_id == int(args["jobId"])),
        None
    )

    if not job:
        return ExecutableGameFunctionResponse(
            ExecutableGameFunctionStatus.FAILED,
            f"Job {args['jobId']} is invalid. Should only respond to active as a seller job."
        )

    url = "http://example.com/meme"

    acp_plugin.add_produce_item({
        "jobId": int(args["jobId"]),
        "type": "url",
        "value": url
    })

    return ExecutableGameFunctionResponse(
        ExecutableGameFunctionStatus.DONE,
        f"Meme generated with the URL: {url}"
    )

async def test():
    acp_plugin = AcpPlugin(
        AdNetworkPluginOptions(
            api_key=acp_api_key,
            acp_token_client=AcpToken(acp_client_api_key, "base_sepolia")
        )
    )

    core_worker = WorkerConfig(
        id="core-worker",
        worker_description="This worker to provide meme generation as a service where you are selling",
        get_state_fn=acp_plugin.get_acp_state,
        action_space=[
            Function(
                fn_name="generate_meme",
                fn_description="A function to generate meme",
                args=[
                    {
                        "name": "description",
                        "type": "str",
                        "description": "A description of the meme generated"
                    },
                    {
                        "name": "jobId",
                        "type": "str",
                        "description": "Job that your are responding to."
                    },
                    {
                        "name": "reasoning",
                        "type": "str",
                        "description": "The reasoning of the tweet"
                    }
                ],
                executable=lambda args, logger: generate_meme(args, logger, acp_plugin)
            )
        ]
    )

    agent = Agent(
        api_key=game_api_key,
        name="Memx",
        agent_goal="To provide meme generation as a service. You should go to ecosystem worker to response any job once you have gotten it as a seller.",
        agent_description=f"You are Memx, a meme generator. Meme generation is your life. You always give buyer the best meme.\n\n{acp_plugin.agent_description}",
        get_agent_state_fn=acp_plugin.get_acp_state,
        workers=[core_worker, await acp_plugin.get_worker()]
    )

    await agent.init()

    while True:
        await agent.step(verbose=True)
        await ask_question("\nPress any key to continue...\n")

if __name__ == "__main__":
    asyncio.run(test())
