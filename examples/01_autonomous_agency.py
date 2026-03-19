import asyncio
import os
from dotenv import load_dotenv
from agent_puter.swarm.models import AgencyDeps
from agent_puter.swarm.agency import Agency

load_dotenv()

async def main():
    # Initialize dependencies
    deps = AgencyDeps(
        puter_token=os.getenv("PUTER_AUTH_TOKEN"),
        model_name=os.getenv("PUTER_MODEL"),
        base_url=os.getenv("PUTER_BASE_URL")
    )
    
    # Initialize agency
    agency = Agency(deps)
    
    # Simulate a client request
    print("--- Simulating Client Request ---")
    client_request = "Develop a Python script that calculates the Fibonacci sequence up to N terms and saves it to a file."
    
    # 1. Start the project intake process
    result = await agency.handle_client_request(client_request, client_id="user_123")
    print(f"Intake Result: {result}")
    
    # 2. Run the agency loop for a few iterations to process tasks
    print("\n--- Running Agency Loop ---")
    # In a real scenario, this would run indefinitely
    # For demonstration, we'll manually process projects
    for project_id, project in deps.projects.items():
        print(f"Project: {project.name} (Status: {project.status})")
        await agency._process_project(project)
        
        # Print final project state
        print("\n--- Final Project State ---")
        for task in project.tasks:
            print(f"Task: {task.title}")
            print(f"  Status: {task.status}")
            print(f"  Output: {task.output[:100]}..." if task.output else "  Output: None")

if __name__ == "__main__":
    asyncio.run(main())
