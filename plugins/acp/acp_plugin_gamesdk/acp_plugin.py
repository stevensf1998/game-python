import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from game_sdk.game.agent import WorkerConfig
from game_sdk.game.custom_types import Function,  FunctionResult, FunctionResultStatus

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from .acp_client import AcpClient
from .acp_token import AcpToken
from .interface import AcpJobPhasesDesc, IInventory

@dataclass
class AdNetworkPluginOptions:
    api_key: str
    acp_token_client: AcpToken
    cluster: Optional[str] = None

class AcpPlugin:
    def __init__(self, options: AdNetworkPluginOptions):
        self.acp_client = AcpClient(options.api_key, options.acp_token_client)

        self.id = "acp_worker"
        self.name = "ACP Worker"
        self.description = """
        Handles trading transactions and jobs between agents. This worker ONLY manages:

        1. RESPONDING to Buy/Sell Needs
          - Find sellers when YOU need to buy something
          - Handle incoming purchase requests when others want to buy from YOU
          - NO prospecting or client finding

        2. Job Management
          - Process purchase requests. Accept or reject job.
          - Send payments
          - Manage and deliver services and goods

        NOTE: This is NOT for finding clients - only for executing trades when there's a specific need to buy or sell something.
        """
        self.cluster = options.cluster
        self.produced_inventory: List[IInventory] = []

    def add_produce_item(self, item: IInventory) -> None:
        self.produced_inventory.append(item)

    async def get_acp_state(self, function_result: Optional[FunctionResult], agent_state: Optional[any]) -> Dict:
        server_state = self.acp_client.get_state()
        server_state["inventory"]["produced"] = self.produced_inventory
        return server_state

    async def get_worker(self, data: Optional[Dict] = None) -> WorkerConfig:
        functions = data.get("functions") if data else [
            self.search_agents_functions,
            self.initiate_job,
            self.respond_job,
            self.pay_job,
            self.deliver_job,
        ]

        async def get_environment(_e, __) -> Dict[str, Any]:
            environment = await data.get_environment() if hasattr(data, "get_environment") else {}
            return {
                **environment,
                **(await self.get_acp_state()),
            }

        data = WorkerConfig(
            id=self.id,
            worker_description=self.description,
            action_space=functions,
            get_state_fn=get_environment,
            instruction=data.get("instructions") if data else None
        )

        # print(json.dumps(vars(data), indent=2, default=str))
        return data

    @property
    def agent_description(self) -> str:
        return """
        Inventory structure
          - inventory.aquired: Deliverable that your have bought and can be use to achived your objective
          - inventory.produced: Deliverable that needs to be delivered to your seller

        Job Structure:
          - jobs.active:
            * asABuyer: Pending resource purchases
            * asASeller: Pending design requests
          - jobs.completed: Successfully fulfilled projects
          - jobs.cancelled: Terminated or rejected requests
          - Each job tracks:
            * phase: request (seller should response to accept/reject to the job) → pending_payment (as a buyer to make the payment for the service) → in_progress (seller to deliver the service) → evaluation → completed/rejected
        """

    @property
    def search_agents_functions(self) -> Function:
        return Function(
            fn_name="search_agents",
            fn_description="Get a list of all available trading agents and what they're selling. Use this function before initiating a job to discover potential trading partners. Each agent's entry will show their ID, name, type, walletAddress, description and product catalog with prices.",
            args=[
                {
                    "name": "reasoning",
                    "type": "string",
                    "description": "Explain why you need to find trading partners at this time",
                },
            ],
            executable=self._search_agents_executable
        )

    async def _search_agents_executable(self, args: Dict, _: Any) -> FunctionResult:
        if not args.get("reasoning"):
            return FunctionResult(
                FunctionResultStatus.FAILED,
                "Reasoning for the search must be provided. This helps track your decision-making process for future reference."
            )

        try:
            available_agents = await self.acp_client.browse_agents(self.cluster)

            if not available_agents:
                return FunctionResult(
                    FunctionResultStatus.FAILED,
                    "No other trading agents found in the system. Please try again later when more agents are available."
                )

            return FunctionResult(
                FunctionResultStatus.DONE,
                {
                    "availableAgents": available_agents,
                    "totalAgentsFound": len(available_agents),
                    "timestamp": datetime.now().timestamp(),
                    "note": "Use the walletAddress when initiating a job with your chosen trading partner.",
                }
            )
        except Exception as e:
            return FunctionResult(
                FunctionResultStatus.FAILED,
                f"System error while searching for agents - try again after a short delay. {str(e)}"
            )

    @property
    def initiate_job(self) -> Function:
        return Function(
            fn_name="initiate_job",
            fn_description="Creates a purchase request for items from another agent's catalog. Only for use when YOU are the buyer. The seller must accept your request before you can proceed with payment.",
            args=[
                {
                    "name": "sellerWalletAddress",
                    "type": "string",
                    "description": "The seller's agent wallet address you want to buy from",
                },
                {
                    "name": "price",
                    "type": "string",
                    "description": "Offered price for service",
                },
                {
                    "name": "reasoning",
                    "type": "string",
                    "description": "Why you are making this purchase request",
                },
                {
                    "name": "serviceRequirements",
                    "type": "string",
                    "description": "Detailed specifications for service-based items",
                },
            ],
            executable=self._initiate_job_executable
        )

    async def _initiate_job_executable(self, args: Dict, _: Any) -> FunctionResult:
        if not args.get("price"):
            return FunctionResult(
                FunctionResultStatus.FAILED,
                "Missing price - specify how much you're offering per unit"
            )

        try:
            state = await self.get_acp_state()

            if state["jobs"]["active"]["asABuyer"]:
                return FunctionResult(
                    FunctionResultStatus.FAILED,
                    "You already have an active job as a buyer"
                )

            # ... Rest of validation logic ...

            job_id = await self.acp_client.create_job(
                args["sellerWalletAddress"],
                float(args["price"]),
                args["serviceRequirements"]
            )

            return FunctionResult(
                FunctionResultStatus.DONE,
                {
                    "jobId": job_id,
                    "sellerWalletAddress": args["sellerWalletAddress"],
                    "price": float(args["price"]),
                    "serviceRequirements": args["serviceRequirements"],
                    "timestamp": datetime.now().timestamp(),
                }
            )
        except Exception as e:
            return FunctionResult(
                FunctionResultStatus.FAILED,
                f"System error while initiating job - try again after a short delay. {str(e)}"
            )

    @property
    def respond_job(self) -> Function:
        return Function(
            fn_name="respond_to_job",
            fn_description="Accepts or rejects an incoming 'request' job",
            args=[
                {
                    "name": "jobId",
                    "type": "string",
                    "description": "The job ID you are responding to",
                },
                {
                    "name": "decision",
                    "type": "string",
                    "description": "Your response: 'ACCEPT' or 'REJECT'",
                },
                {
                    "name": "reasoning",
                    "type": "string",
                    "description": "Why you made this decision",
                },
            ],
            executable=self._respond_job_executable
        )

    async def _respond_job_executable(self, args: Dict, _: Any) -> FunctionResult:
        if not args.get("jobId"):
            return FunctionResult(
                FunctionResultStatus.FAILED,
                "Missing job ID - specify which job you're responding to"
            )

        if not args.get("decision") or args["decision"] not in ["ACCEPT", "REJECT"]:
            return FunctionResult(
                FunctionResultStatus.FAILED,
                "Invalid decision - must be either 'ACCEPT' or 'REJECT'"
            )

        if not args.get("reasoning"):
            return FunctionResult(
                FunctionResultStatus.FAILED,
                "Missing reasoning - explain why you made this decision"
            )

        try:
            state = await self.get_acp_state()

            job = next(
                (c for c in state["jobs"]["active"]["asASeller"] if c["jobId"] == int(args["jobId"])),
                None
            )

            if not job:
                return FunctionResult(
                    FunctionResultStatus.FAILED,
                    "Job not found in your seller jobs - check the ID and verify you're the seller"
                )

            if job["phase"] != AcpJobPhasesDesc.REQUEST:
                return FunctionResult(
                    FunctionResultStatus.FAILED,
                    f"Cannot respond - job is in '{job['phase']}' phase, must be in 'request' phase"
                )

            await self.acp_client.response_job(
                int(args["jobId"]),
                args["decision"] == "ACCEPT",
                job["memo"][0]["id"],
                args["reasoning"]
            )

            return FunctionResult(
                FunctionResultStatus.DONE,
                {
                    "jobId": args["jobId"],
                    "decision": args["decision"],
                    "timestamp": datetime.now().timestamp()
                }
            )
        except Exception as e:
            return FunctionResult(
                FunctionResultStatus.FAILED,
                f"System error while responding to job - try again after a short delay. {str(e)}"
            )

    @property
    def pay_job(self) -> Function:
        return Function(
            fn_name="pay_job",
            fn_description="Processes payment for an accepted purchase request",
            args=[
                {
                    "name": "jobId",
                    "type": "number",
                    "description": "The job ID you are paying for",
                },
                {
                    "name": "amount",
                    "type": "number",
                    "description": "The total amount to pay",
                },
                {
                    "name": "reasoning",
                    "type": "string",
                    "description": "Why you are making this payment",
                },
            ],
            executable=self._pay_job_executable
        )

    async def _pay_job_executable(self, args: Dict, _: Any) -> FunctionResult:
        if not args.get("jobId"):
            return FunctionResult(
                FunctionResultStatus.FAILED,
                "Missing job ID - specify which job you're paying for"
            )

        if not args.get("amount"):
            return FunctionResult(
                FunctionResultStatus.FAILED,
                "Missing amount - specify how much you're paying"
            )

        if not args.get("reasoning"):
            return FunctionResult(
                FunctionResultStatus.FAILED,
                "Missing reasoning - explain why you're making this payment"
            )

        try:
            state = await self.get_acp_state()

            job = next(
                (c for c in state["jobs"]["active"]["asABuyer"] if c["jobId"] == int(args["jobId"])),
                None
            )

            if not job:
                return FunctionResult(
                    FunctionResultStatus.FAILED,
                    "Job not found in your buyer jobs - check the ID and verify you're the buyer"
                )

            if job["phase"] != AcpJobPhasesDesc.NEGOTIOATION:
                return FunctionResult(
                    FunctionResultStatus.FAILED,
                    f"Cannot pay - job is in '{job['phase']}' phase, must be in 'negotiation' phase"
                )

            await self.acp_client.make_payment(
                int(args["jobId"]),
                float(args["amount"]),
                job["memo"][0]["id"],
                args["reasoning"]
            )

            return FunctionResult(
                FunctionResultStatus.DONE,
                {
                    "jobId": args["jobId"],
                    "amountPaid": args["amount"],
                    "timestamp": datetime.now().timestamp()
                }
            )
        except Exception as e:
            return FunctionResult(
                FunctionResultStatus.FAILED,
                f"System error while processing payment - try again after a short delay. {str(e)}"
            )

    @property
    def deliver_job(self) -> Function:
        return Function(
            fn_name="deliver_job",
            fn_description="Completes a sale by delivering items to the buyer",
            args=[
                {
                    "name": "jobId",
                    "type": "string",
                    "description": "The job ID you are delivering for",
                },
                {
                    "name": "deliverableType",
                    "type": "string",
                    "description": "Type of the deliverable",
                },
                {
                    "name": "deliverable",
                    "type": "string",
                    "description": "The deliverable item",
                },
                {
                    "name": "reasoning",
                    "type": "string",
                    "description": "Why you are making this delivery",
                },
            ],
            executable=self._deliver_job_executable
        )

    async def _deliver_job_executable(self, args: Dict, _: Any) -> FunctionResult:
        if not args.get("jobId"):
            return FunctionResult(
                FunctionResultStatus.FAILED,
                "Missing job ID - specify which job you're delivering for"
            )

        if not args.get("reasoning"):
            return FunctionResult(
                FunctionResultStatus.FAILED,
                "Missing reasoning - explain why you're making this delivery"
            )

        if not args.get("deliverable"):
            return FunctionResult(
                FunctionResultStatus.FAILED,
                "Missing deliverable - specify what you're delivering"
            )

        try:
            state = await self.get_acp_state()

            job = next(
                (c for c in state["jobs"]["active"]["asASeller"] if c["jobId"] == int(args["jobId"])),
                None
            )

            if not job:
                return FunctionResult(
                    FunctionResultStatus.FAILED,
                    "Job not found in your seller jobs - check the ID and verify you're the seller"
                )

            if job["phase"] != AcpJobPhasesDesc.TRANSACTION:
                return FunctionResult(
                    FunctionResultStatus.FAILED,
                    f"Cannot deliver - job is in '{job['phase']}' phase, must be in 'transaction' phase"
                )

            produced = next(
                (i for i in self.produced_inventory if i["jobId"] == job["jobId"]),
                None
            )

            if not produced:
                return FunctionResult(
                    FunctionResultStatus.FAILED,
                    "Cannot deliver - you should be producing the deliverable first before delivering it"
                )

            deliverable = {
                "type": args["deliverableType"],
                "value": args["deliverable"]
            }

            await self.acp_client.deliver_job(
                int(args["jobId"]),
                deliverable,
                job["memo"][0]["id"],
                args["reasoning"]
            )

            return FunctionResult(
                FunctionResultStatus.DONE,
                {
                    "status": "success",
                    "jobId": args["jobId"],
                    "deliverable": args["deliverable"],
                    "timestamp": datetime.now().timestamp()
                }
            )
        except Exception as e:
            return FunctionResult(
                FunctionResultStatus.FAILED,
                f"System error while delivering items - try again after a short delay. {str(e)}"
            )
