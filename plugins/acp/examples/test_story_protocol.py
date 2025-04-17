import os
import hashlib
import requests
from io import BytesIO
from PIL import Image
from typing import Dict, Any, Tuple

import os
from acp_plugin_gamesdk.interface import AcpJobPhasesDesc, IDeliverable


# Helper functions
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

def validate_url(image_url):
    try:
        if image_url.startswith('http'):
            response = requests.get(image_url)
            img_data = response.content
            checksum = hashlib.md5(img_data).hexdigest()

            try:
                img = Image.open(BytesIO(img_data))
                return {"type": "image", "checksum": checksum}
            except:
                return {"type": "video", "checksum": checksum}
        else:
            raise Exception("Invalid image URL")

    except Exception as e:
        print(f"Error processing file and checksum: {str(e)}")
        return None

def extract_url(text: str) -> str:
    import re
    match = re.search(r"https?://\S+", text)
    return match.group(0) if match else ""

# Main evaluation function
def on_evaluate(deliverable: IDeliverable) -> Tuple[bool, str]:
    try:
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

        active_job = [{
               "jobId":478,
               "desc":"Upload to story protocol https://d1kfhpz1mqv5dj.cloudfront.net/generated-image/_/04-25/2eb48b44-7f93-472b-98c0-daebf34d8881.png",
               "price":"1",
               "phase":"evaluation",
               "memo":[
                  {
                     "id":588,
                     "createdAt":1744726830441
                  }
               ],
               "tweetHistory":[
                  
               ],
               "lastUpdated":1744726830444
            }]

        if not active_job:
            raise Exception("No active job found")
        

        acp_state_content = next((job for job in active_job if job.get('phase') == AcpJobPhasesDesc.EVALUATION), None).get('desc')
        
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

        print("Deliverable approved by evaluator")
        return True, "Deliverable approved by evaluator"

    except Exception as e:
        print(f"Error evaluating deliverable: {str(e)}")
        return False, f"Error evaluating deliverable: {str(e)}"

# Test function
def test_on_evaluate():
    deliverable = IDeliverable(
        type="txHashUrl",
        value="https://explorer.story.foundation/ipa/0xa5621758B54AdA3e27d32Ec603060AF6cF5f75c1"
    )
    
    on_evaluate(deliverable)

if __name__ == "__main__":
    test_on_evaluate()
