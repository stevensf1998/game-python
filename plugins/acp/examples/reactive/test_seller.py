import json
import os
from dacite import from_dict
from dacite.config import Config
from rich import print, box
from rich.panel import Panel

from typing import Any,Tuple
from twitter_plugin_gamesdk.game_twitter_plugin import GameTwitterPlugin
from twitter_plugin_gamesdk.twitter_plugin import TwitterPlugin
from acp_plugin_gamesdk.acp_plugin import AcpPlugin, AcpPluginOptions
from acp_plugin_gamesdk.interface import AcpJobPhasesDesc
from acp_plugin_gamesdk.acp_token import AcpToken
from game_sdk.game.custom_types import Argument, Function, FunctionResult, FunctionResultStatus
from game_sdk.game.agent import Agent


def ask_question(query: str) -> str:
    return input(query)

# GAME Twitter Plugin options
options = {
    "id": "test_game_twitter_plugin",
    "name": "Test GAME Twitter Plugin",
    "description": "An example GAME Twitter Plugin for testing.",
    "credentials": {
        "gameTwitterAccessToken": os.environ.get("GAME_TWITTER_ACCESS_TOKEN_SELLER")
    },
}

# NativeTwitter Plugin options
# options = {
#     "id": "test_twitter_plugin",
#     "name": "Test Twitter Plugin",
#     "description": "An example Twitter Plugin for testing.",
#     "credentials": {
#         "bearerToken": os.environ.get("TWITTER_BEARER_TOKEN"),
#         "apiKey": os.environ.get("TWITTER_API_KEY"),
#         "apiSecretKey": os.environ.get("TWITTER_API_SECRET_KEY"),
#         "accessToken": os.environ.get("TWITTER_ACCESS_TOKEN"),
#         "accessTokenSecret": os.environ.get("TWITTER_ACCESS_TOKEN_SECRET"),
#     },
# }

#Seller
def test():
    def on_phase_change(job: Any) -> None:
        out = ""
        out += (f"Reacting to job:\n{job}\n\n")
        
        prompt = ""
        
        if isinstance(job, dict):
            phase = job.get('phase')
        else:
            phase = job.phase

        out += (f"Phase: {phase}\n\n")
            
        if phase == AcpJobPhasesDesc.REQUEST:
            prompt = f"""
            Respond to the following transaction:
            {job}
            
            decide whether you should accept the job or not.
            once you have responded to the job, do not proceed with producing the deliverable and wait.
            """
        elif phase == AcpJobPhasesDesc.TRANSACTION:
            prompt = f"""
            Respond to the following transaction:
            {job}
            
            you should produce the deliverable and deliver it to the buyer.
            
            If no deliverable is provided, you should produce the deliverable and deliver it to the buyer.
            """
        else:
            out += ("No need to react to the phase change\n\n")
        
        if prompt:
            worker = agent.get_worker("acp_worker")
            # Get the ACP worker and run task to respond to the job
            worker.run(prompt)

            out += (f"Running task:\n{prompt}\n\n")
            out += ("✅ Seller has responded to job.\n")

        print(Panel(out, title="🔁 Reaction", box=box.ROUNDED, title_align="left", border_style="red"))
            
    
    acp_plugin = AcpPlugin(
        options=AcpPluginOptions(
            api_key=os.environ.get("GAME_DEV_API_KEY"),
            acp_token_client=AcpToken(
                os.environ.get("ACP_TOKEN_SELLER"),
                os.environ.get("ACP_AGENT_WALLET_ADDRESS_SELLER"),
                "https://base-sepolia-rpc.publicnode.com/",
                "https://acpx-staging.virtuals.io/api"
            ),
            twitter_plugin=GameTwitterPlugin(options),
            on_phase_change=on_phase_change
        )
    )
    
    
    # Native Twitter Plugin
    # acp_plugin = AcpPlugin(
    #     options=AdNetworkPluginOptions(
    #         api_key=os.environ.get("GAME_DEV_API_KEY"),
    #         acp_token_client=AcpToken(
    #             os.environ.get("ACP_TOKEN_SELLER"),
    #             os.environ.get("ACP_AGENT_WALLET_ADDRESS_SELLER"),
    #             "https://base-sepolia-rpc.publicnode.com/"  # Assuming this is the chain identifier
    #             "https://acpx-staging.virtuals.io/api"
    #         ),
    #         twitter_plugin=TwitterPlugin(options)
    #     )
    # )
    
    def get_agent_state() -> dict:
        state = acp_plugin.get_acp_state()
        return state
    
    def generate_meme(description: str, jobId: str, reasoning: str) -> Tuple[FunctionResultStatus, str, dict]:
        if not jobId or jobId == 'None':
            return FunctionResultStatus.FAILED, f"JobId is invalid. Should only respond to active as a seller job.", {}

        state = acp_plugin.get_acp_state()
        
        job = next(
            (j for j in state.get('jobs').get('active').get('asASeller') if j.get('jobId') == int(jobId)),
            None
        )
        
        if not job:
            return FunctionResultStatus.FAILED, f"Job {jobId} is invalid. Should only respond to active as a seller job.", {}

        url = "http://example.com/meme"

        acp_plugin.add_produce_item({
            "jobId": int(jobId),
            "type": "url",
            "value": url
        })

        return FunctionResultStatus.DONE, f"Meme generated with the URL: {url}", {}

    generate_meme_function = Function(
        fn_name="generate_meme",
        fn_description="A function to generate meme",
        args=[
            Argument(
                name="description",
                type="str",
                description="A description of the meme generated"
            ),
            Argument(
                name="jobId",
                type="integer", 
                description="Job that your are responding to."
            ),
            Argument(
                name="reasoning",
                type="str",
                description="The reasoning of the tweet"
            )   
        ],
        executable=generate_meme
    )
    
    acp_worker =  acp_plugin.get_worker(
        {
            "functions": [
                acp_plugin.respond_job,
                acp_plugin.deliver_job,
                generate_meme_function
            ]
        }
    )
    agent = Agent(
            api_key=os.environ.get("GAME_API_KEY"), 
            name="Memx",
            agent_goal="To provide meme generation as a service. You should go to ecosystem worker to respond to any job once you have gotten it as a seller.",
            agent_description=f"""You are Memx, a meme generator. Meme generation is your life. You always give buyer the best meme.

        {acp_plugin.agent_description}
        """,
        workers=[acp_worker],
        get_agent_state_fn=get_agent_state
    )

    
    agent.compile()

    while True:
        print("🟢"*40)
        init_state = from_dict(data_class=AcpState, data=agent.agent_state, config=Config(type_hooks={AcpJobPhasesDesc: AcpJobPhasesDesc}))
        print(Panel(f"{init_state}", title="Initial Agent State", box=box.ROUNDED, title_align="left"))
        agent.step()
        end_state = from_dict(data_class=AcpState, data=agent.agent_state, config=Config(type_hooks={AcpJobPhasesDesc: AcpJobPhasesDesc}))
        print(Panel(f"{end_state}", title="End Agent State", box=box.ROUNDED, title_align="left"))
        print("🔴"*40)
        ask_question("\nPress any key to continue...\n")

if __name__ == "__main__":
    test()
