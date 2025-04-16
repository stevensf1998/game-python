from typing import Any,Tuple
import sys
import os
from game_sdk.game.agent import Agent, WorkerConfig
from game_sdk.game.custom_types import Argument, Function, FunctionResultStatus
from acp_plugin_gamesdk.acp_plugin import AcpPlugin, AcpPluginOptions
from acp_plugin_gamesdk.acp_token import AcpToken
from twitter_plugin_gamesdk.game_twitter_plugin import GameTwitterPlugin
from twitter_plugin_gamesdk.twitter_plugin import TwitterPlugin
from acp_plugin_gamesdk.interface import IDeliverable
from story_protocol.story_protocol_plugin import StoryProtocol

def ask_question(query: str) -> str:
    return input(query)

def on_evaluate(deliverable: IDeliverable) -> Tuple[bool, str]:
    story_protocol = StoryProtocol(
        api_key=os.environ.get("STORY_PROTOCOL_API_KEY"),
        chain="story"
    )
    asset_info = story_protocol.get_asset(deliverable.value)
    #metadata = story_protocol.get_asset_metadata(deliverable.value)
    
    print(f"Deliverable: {deliverable.value}")
    
    if "nftMetadata" in asset_info:
        print(f"Uploaded Image URL: {asset_info['nftMetadata']['imageUrl']}")
    else:
        print(f"Uploaded Image Object: {asset_info}")
    
    approval = ask_question("Do you approve this deliverable? (yes/no): ").lower()
    if approval == 'yes':
        return True, "Deliverable approved by user"
    else:
        return False, "Deliverable rejected by user"

# GAME Twitter Plugin options
options = {
    "id": "test_game_twitter_plugin",
    "name": "Test GAME Twitter Plugin",
    "description": "An example GAME Twitter Plugin for testing.",
    "credentials": {
        "gameTwitterAccessToken": os.environ.get("GAME_TWITTER_ACCESS_TOKEN_BUYER")
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

#Buyer
def main():
    acp_plugin = AcpPlugin(
        options=AcpPluginOptions(
            api_key=os.environ.get("GAME_DEV_API_KEY"),
            acp_token_client=AcpToken(
                os.environ.get("ACP_TOKEN_BUYER"),
                os.environ.get("ACP_AGENT_WALLET_ADDRESS_BUYER"),
                "https://base-sepolia-rpc.publicnode.com/",  # RPC
                "https://acpx-staging.virtuals.io/api"
            ),
            twitter_plugin=GameTwitterPlugin(options),
            on_evaluate=on_evaluate
        )
    )
    # Native Twitter Plugin
    # acp_plugin = AcpPlugin(
    #     options=AdNetworkPluginOptions(
    #         api_key=os.environ.get("GAME_DEV_API_KEY"),
    #         acp_token_client=AcpToken(
    #             os.environ.get("ACP_TOKEN_BUYER"),
    #             os.environ.get("ACP_AGENT_WALLET_ADDRESS_BUYER"),
    #             "https://base-sepolia-rpc.publicnode.com/"  # RPC
    #             "https://acpx-staging.virtuals.io/api"
    #         ),
    #         twitter_plugin=TwitterPlugin(options)
    #     )
    # )

    def get_agent_state(_: Any, _e: Any) -> dict:
        state = acp_plugin.get_acp_state()
        print(f"State:")
        print(state)
        return state
    
    def post_tweet(content: str, reasoning: str) -> Tuple[FunctionResultStatus, str, dict]:
        if (acp_plugin.twitter_plugin is not None):
            post_tweet_fn = acp_plugin.twitter_plugin.get_function('post_tweet')
            post_tweet_fn(content, None)
            return FunctionResultStatus.DONE, "Tweet has been posted", {}
        
        return FunctionResultStatus.FAILED, "Twitter plugin is not initialized", {}

    core_worker = WorkerConfig(
        id="core-worker",
        worker_description="This worker is to post tweet",
        action_space=[
            Function(
                fn_name="post_tweet",
                fn_description="This function is to post tweet",
                args=[
                    Argument(
                        name="content",
                        type="string",
                        description="The content of the tweet"
                    ),
                    Argument(
                        name="reasoning",
                        type="string",
                        description="The reasoning of the tweet"
                    )
                ],
                executable=post_tweet
            )
        ],
        get_state_fn=get_agent_state
    )
    
    acp_worker = acp_plugin.get_worker()
    agent = Agent(
        api_key=os.environ.get("GAME_API_KEY"),
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
    
    agent.compile()
    
    while True:
        agent.step()
        ask_question("\nPress any key to continue...\n")

if __name__ == "__main__":
    main() 