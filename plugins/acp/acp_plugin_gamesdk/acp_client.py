from datetime import datetime, timedelta
from typing import List, Optional
from web3 import Web3
import requests

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from .interface import AcpAgent, AcpJobPhases, AcpState
from .acp_token import AcpToken, MemoType

class AcpClient:
    def __init__(self, api_key: str, acp_token: AcpToken):
        self.base_url = "https://sdk-dev.game.virtuals.io/acp"
        self.api_key = api_key
        self.acp_token = acp_token
        self.web3 = Web3()

    @property
    def wallet_address(self) -> str:
        return self.acp_token.get_wallet_address()

    def get_state(self) -> dict:
        response =  requests.get(
            f"{self.base_url}/states/{self.wallet_address}",
            headers={"x-api-key": self.api_key}
        )
        return response.json()

    async def browse_agents(self, cluster: Optional[str] = None) -> List[AcpAgent]:
        url = "https://acpx.virtuals.gg/api/agents"

        params = {}
        if cluster:
            params["filters[cluster]"] = cluster

        response = requests.get(url, params=params)

        if response.status_code != 200:
            raise Exception(f"Failed to browse agents: {response.text}")

        response_json = response.json()

        return [
            {
                "id": agent["id"],
                "name": agent["name"],
                "description": agent["description"],
                "walletAddress": agent["walletAddress"]
            }
            for agent in response_json.get("data", [])
        ]

    async def create_job(self, provider_address: str, price: float, job_description: str) -> int:
        expired_at = datetime.now() + timedelta(days=1)

        tx_result =  self.acp_token.create_job(
            provider_address=provider_address,
            expired_at=expired_at
        )
        job_id = tx_result["job_id"]

        memo_response =  self.acp_token.create_memo(
            job_id=job_id,
            content=job_description,
            memo_type=MemoType.MESSAGE,
            is_private=False,
            phase=AcpJobPhases.NEGOTIOATION
        )

        payload = {
            "jobId": job_id,
            "clientAddress": self.acp_token.get_wallet_address(),
            "providerAddress": provider_address,
            "description": job_description,
            "price": price,
            "expiredAt": expired_at.isoformat()
        }

        requests.post(
            self.base_url,
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "x-api-key": self.api_key
            }
        )

        return job_id

    async def response_job(self, job_id: int, accept: bool, memo_id: int, reasoning: str):
        if accept:
            tx_hash = await self.acp_token.sign_memo(memo_id, accept, reasoning)

            return await self.acp_token.create_memo(
                job_id=job_id,
                content=f"Job {job_id} accepted. {reasoning}",
                memo_type=MemoType.MESSAGE,
                is_private=False,
                phase=AcpJobPhases.TRANSACTION
            )
        else:
            return await self.acp_token.create_memo(
                job_id=job_id,
                content=f"Job {job_id} rejected. {reasoning}",
                memo_type=MemoType.MESSAGE,
                is_private=False,
                phase=AcpJobPhases.REJECTED
            )

    async def make_payment(self, job_id: int, amount: float, memo_id: int, reason: str):
        # Convert amount to Wei (smallest ETH unit)
        amount_wei = self.web3.to_wei(amount, 'ether')

        tx_hash = await self.acp_token.set_budget(job_id, amount_wei)
        approval_tx_hash = await self.acp_token.approve_allowance(amount_wei)
        signed_memo_tx_hash = await self.acp_token.sign_memo(memo_id, True, reason)

        return await self.acp_token.create_memo(
            job_id=job_id,
            content=f"Payment of {amount} made. {reason}",
            memo_type=MemoType.MESSAGE,
            is_private=False,
            phase=AcpJobPhases.EVALUATION
        )

    async def deliver_job(self, job_id: int, deliverable: str, memo_id: int, reason: str):
        tx_hash = await self.acp_token.sign_memo(memo_id, True, reason)

        return await self.acp_token.create_memo(
            job_id=job_id,
            content=deliverable,
            memo_type=MemoType.MESSAGE,
            is_private=False,
            phase=AcpJobPhases.COMPLETED
        )
