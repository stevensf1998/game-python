import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from plugins.story_protocol.story_protocol_plugin import StoryProtocol

API_KEY = os.environ.get("STORY_PROTOCOL_API_KEY", "xxx")
CHAIN = "story"  # or other supported chain

# Initialize the Story Protocol client
story_client = StoryProtocol(api_key=API_KEY, chain=CHAIN)

# Example asset ID
asset_id = "xxx"

try:
    # Get asset information
    asset_info = story_client.get_asset(asset_id)
    print(f"Asset Information: {asset_info}")
    
    # Get asset metadata
    asset_metadata = story_client.get_asset_metadata(asset_id)
    print(f"Asset Metadata: {asset_metadata}")
    
except Exception as e:
    print(f"Error: {e}") 