from __future__ import annotations

import os
from pathlib import Path
from backend.agents.agents import AgentConfig, AgentOrchestrator


def demo() -> None:
	# Configure to "local" by default so it runs without API keys.
	provider = os.getenv("AGENT_PROVIDER", "local")
	cfg = AgentConfig(provider=provider, llm_model=os.getenv("LLM_MODEL"))

	orchestrator = AgentOrchestrator(config=cfg)
	orchestrator.set_prompt1("Prioritize rapid prototyping and clear milestones.")
	# Set a base private prompt and add prior messages to simulate memory
	orchestrator.workflow_agent.set_prompt("Base objective: Assist urban land development planning.")
	orchestrator.workflow_agent.add_message("user", "We are interested in mixed-use development with green spaces.")
	orchestrator.workflow_agent.add_message("assistant", "Consider zoning, environmental impact, and utility access.")

	context = (
		"Build a web app with Next.js frontend and Python backend. "
		"Add an image generation capability and an agent to plan development steps."
	)
	steps = orchestrator.next_steps(context)
	print("Workflow Plan ({}):".format(provider))
	for i, s in enumerate(steps, start=1):
		print(f"{i}. {s}")

	out_path = Path("generated.png")
	img_path = orchestrator.create_image(
		prompt="Concept art for a modern civic planning dashboard",
		out_path=str(out_path),
	)
	print(f"Image generated at: {img_path}")


if __name__ == "__main__":
	demo()
