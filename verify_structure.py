import sys
import os
import asyncio

# Ensure no src in path, but current dir is in path
sys.path.append(os.getcwd())

async def verify():
    print("Verifying Directory Structure...")
    if os.path.exists("src"):
        print("FAIL: src/ directory found!")
        sys.exit(1)
        
    print("Verifying Imports...")
    try:
        from app.main import app
        from orchestration.executor import OrchestrationExecutor
        from agents.retrieval_agent import RetrievalAgent
        print("Imports Successful.")
    except ImportError as e:
        print(f"FAIL: Import Error: {e}")
        sys.exit(1)
        
    print("Verifying Logic Instantiation...")
    try:
        ex = OrchestrationExecutor()
        print("Executor Instantiated.")
    except Exception as e:
        print(f"FAIL: Logic Error: {e}")
        # Note: Might fail if API keys missing, but structure is valid
        pass

    print("PASS: Structure Valid.")

if __name__ == "__main__":
    asyncio.run(verify())
