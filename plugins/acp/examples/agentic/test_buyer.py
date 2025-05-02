import hashlib
import re
from typing import Any,Tuple, Dict
from dacite import from_dict
from dacite.config import Config
from rich import print, box
from rich.panel import Panel
from typing import Any,Tuple
import os

import requests
from game_sdk.game.agent import Agent, WorkerConfig
from game_sdk.game.custom_types import Argument, Function, FunctionResultStatus
from acp_plugin_gamesdk.acp_plugin import AcpPlugin, AcpPluginOptions
from acp_plugin_gamesdk.acp_token import AcpToken
from twitter_plugin_gamesdk.game_twitter_plugin import GameTwitterPlugin
from twitter_plugin_gamesdk.twitter_plugin import TwitterPlugin
from acp_plugin_gamesdk.interface import IDeliverable, AcpJobPhasesDesc

from acp_plugin_gamesdk.interface import IDeliverable, AcpState, AcpJobPhasesDesc
def ask_question(query: str) -> str:
    return input(query)

def get_asset_info(asset_id: str) -> Dict[str, Any]:
    base_url = "https://api.storyapis.com/api/v3"
    headers = {
        "x-api-key": os.environ.get("STORY_PROTOCOL_API_KEY"),
        "x-chain": "story",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{base_url}/assets/{asset_id}", headers=headers)
       
        if response.status_code != 200:
            raise Exception(f"Failed to get asset: {response.status_code} - {response.text}")
        
        return response.json()
   
    except Exception as e:
        print(f"Error retrieving asset info: {str(e)}")
        return {"error": str(e)}
    
def extract_url(content: str) -> str:
    url_pattern = r'https?://[^\s]+'
    match = re.search(url_pattern, content)
    if match:
        return match.group(0)
    else:
        return None

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
    def on_evaluate(deliverable: IDeliverable) -> Tuple[bool, str]:
        try:
            acp_state = acp_plugin.get_acp_state()
            
            if acp_state is None:
                raise Exception("State not found")
            
            #Expect a txHashUrl deliverable
            if deliverable.type == "txHashUrl":
                tx_hash = deliverable.value.split('/')[-1]
                print(f"Transaction Hash: {tx_hash}")
                
            if not tx_hash:
                raise Exception("Invalid transaction hash - must be a valid hex string")
            
            asset_info = get_asset_info(tx_hash)
            
            if not asset_info:
                raise Exception("Asset info not found")
            
            onchain_content = asset_info.get('data', {}).get('nftMetadata', {}).get('imageUrl')
            
            if not onchain_content:
                raise Exception("No image or video URL found in metadata")       
                 
            active_job = acp_state.get('jobs', {}).get('active', {}).get('asABuyer', [])
            
            if not active_job:
                raise Exception("No active job found")
            
            acp_state_content= next((job for job in active_job if job.get('phase') == AcpJobPhasesDesc.EVALUATION), None).get('desc')
            
            if not acp_state_content:
                raise Exception("No content found")
            
            onchain_info = validate_url(onchain_content)
            acp_state_info = validate_url(extract_url(acp_state_content))
                    
            if onchain_info is None or acp_state_info is None:
                raise Exception("Could not process files")
            
            if onchain_info["type"] != acp_state_info["type"]:
                raise Exception(f"File types do not match: {onchain_info['type']} vs {acp_state_info['type']}")
            
            if onchain_info["checksum"] != acp_state_info["checksum"]:
                raise Exception(f"File checksums do not match: {onchain_info['checksum']} vs {acp_state_info['checksum']}")
        
            print(f"Deliverable approved by evaluator")
            return True, "Deliverable approved by evaluator"
        except Exception as e:
            print(f"Error evaluating deliverable: {str(e)}")
            return False, f"Error evaluating deliverable: {str(e)}"

    def validate_url(image_url):
        try:
            if image_url.startswith('http'):
                response = requests.get(image_url)
                img_data = response.content
                checksum = hashlib.md5(img_data).hexdigest()
                
                return {"type": "image", "checksum": checksum}
            else:
                raise Exception("Invalid image URL")
            
        except Exception as e:
            print(f"Error processing file and checksum: {str(e)}")
            return None
        
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

    def get_agent_state() -> dict:
        state = acp_plugin.get_acp_state()
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
        print("🟢"*40)
        agent.step()
        state = from_dict(data_class=AcpState, data=agent.agent_state, config=Config(type_hooks={AcpJobPhasesDesc: AcpJobPhasesDesc}))
        print(Panel(f"{state}", title="Agent State", box=box.ROUNDED, title_align="left"))
        print("🔴"*40)
        ask_question("\nPress any key to continue...\n")

if __name__ == "__main__":
    main() 