import requests
from typing import Optional, Dict, Any

class StoryProtocol:
    def __init__(self, api_key: str, chain: str):
        """
        Initialize the Story Protocol client.
        
        Args:
            api_key: The API key for Story Protocol
            chain: The blockchain chain to use
        """
        self.api_key = api_key
        self.chain = chain
        self.base_url = "https://api.storyapis.com/api/v3"
        self.headers = {
            "x-api-key": self.api_key,
            "x-chain": self.chain,
            "Content-Type": "application/json"
        }
    
    def get_asset(self, asset_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/assets/{asset_id}"
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to get asset: {response.status_code} - {response.text}")
        
        return response.json()
    
    def get_asset_metadata(self, asset_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/assets/{asset_id}/metadata"
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to get asset metadata: {response.status_code} - {response.text}")
        
        return response.json()
