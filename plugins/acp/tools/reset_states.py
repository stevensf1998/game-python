import os
from acp_plugin_gamesdk.acp_plugin import AcpToken, AcpPlugin, AcpPluginOptions


def reset_acp_states() -> None:
    """Reset plugin state for all configured ACP tokens."""
    acp_configs = [
        {
            "acp_token": os.environ.get("ACP_TOKEN_BUYER"),
            "agent_wallet_address": os.environ.get("ACP_AGENT_WALLET_ADDRESS_BUYER")
        },
        {
            "acp_token": os.environ.get("ACP_TOKEN_SELLER"),
            "agent_wallet_address": os.environ.get("ACP_AGENT_WALLET_ADDRESS_SELLER")
        }
    ]
    for acp_config in acp_configs:
        try:
            api_key = os.environ.get("GAME_DEV_API_KEY")
            acp_token = acp_config["acp_token"]
            agent_wallet_address = acp_config["agent_wallet_address"]
            print(f"Resetting state for token: {acp_token}, wallet address: {agent_wallet_address}")
            acp_plugin = AcpPlugin(
                options=AcpPluginOptions(
                    api_key=api_key,
                    acp_token_client=AcpToken(
                        acp_token,
                        agent_wallet_address,
                        "https://base-sepolia-rpc.publicnode.com/"
                    )
                )
            )
            acp_plugin.reset_state()
            new_state = acp_plugin.acp_client.get_state()
            print(new_state)
            print(f"Successfully reset state for token: {acp_config["acp_token"]}")
        except Exception as e:
            print(f"Failed to reset state for token {acp_config["acp_token"]}: {e}")


if __name__ == "__main__":
    reset_acp_states()
