import os
from acp_plugin_gamesdk.acp_plugin import AcpToken, AcpPlugin, AcpPluginOptions

def delete_completed_job() -> None:
    """Delete completed job for all configured ACP tokens."""
    try:
        api_key = os.environ.get("GAME_DEV_API_KEY")
        acp_token = os.environ.get("ACP_TOKEN_BUYER")
        agent_wallet_address = os.environ.get("ACP_AGENT_WALLET_ADDRESS_BUYER")
        print(f"Deleting completed job for token: {acp_token}, wallet address: {agent_wallet_address}")
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
        state = acp_plugin.get_acp_state()
        print(f"Completed jobs: {state.get('jobs').get('completed',[])}")
        
        # Prompt user to input the job ID they want to delete
        job_id = input("Enter the job ID you want to delete: ")
        
        acp_plugin.delete_completed_job(job_id)
        print(f"Successfully deleted completed job for token: {acp_token}")
        exit()
    except Exception as e:
        print(f"Failed to delete completed job: {e}")

def prune_old_jobs(n_jobs_to_remain: int = 2) -> None:
    """
    Deletes completed ACP jobs for the configured token,
    keeping only the n most recently updated ones.
    """
    try:
        api_key = os.environ.get("GAME_DEV_API_KEY")
        acp_token = os.environ.get("ACP_TOKEN_BUYER")
        agent_wallet_address = os.environ.get("ACP_AGENT_WALLET_ADDRESS_BUYER")

        print(f"Pruning completed jobs for token: {acp_token}, wallet: {agent_wallet_address}")

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

        state = acp_plugin.get_acp_state()
        completed_jobs = state.get('jobs', {}).get('completed', [])

        if not completed_jobs:
            print("No completed jobs found.")
            return

        num_completed_jobs = len(completed_jobs)
        print(f"Found {num_completed_jobs} completed jobs.")

        if num_completed_jobs <= n_jobs_to_remain:
            print(f"No pruning needed. Keeping all {num_completed_jobs} jobs.")
            return

        # Sort jobs by 'lastUpdated' descending and keep only the most recent
        sorted_completed_jobs = sorted(
            completed_jobs, key=lambda job: job['lastUpdated'], reverse=True
        )
        jobs_to_prune = sorted_completed_jobs[n_jobs_to_remain:]

        for job in jobs_to_prune:
            job_id = job.get('jobId')
            acp_plugin.delete_completed_job(job_id)
            print(f"✅ Deleted job ID: {job_id}")

    except Exception as e:
        print(f"❌ Failed to prune jobs: {e}")


if __name__ == "__main__":
    print("Choose an operation:")
    print("1. Delete a specific completed job")
    print("2. Prune all but the N most recent completed jobs")

    choice = input("Enter 1 or 2: ").strip()

    if choice == "1":
        delete_completed_job()
    elif choice == "2":
        n = input("Enter the number of most recent jobs to keep (default: 2): ").strip()
        n = int(n) if n.isdigit() else 2
        prune_old_jobs(n_jobs_to_remain=n)
    else:
        print("❌ Invalid choice. Exiting.")
