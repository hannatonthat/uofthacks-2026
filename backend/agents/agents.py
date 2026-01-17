"""Shared agent infrastructure: config, base memory, planner, image, orchestrator."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional, Literal, TypedDict, Dict, Any


try:
	from dotenv import load_dotenv  # Load environment variables from .env file
	load_dotenv()
except Exception:
	pass  # Silently continue if dotenv not available


# Type alias for supported LLM providers
Provider = Literal["local", "openai", "gemini"]


@dataclass
class AgentConfig:
	"""LLM routing config: provider hint, optional model, image size."""
	provider: Provider = "local"
	llm_model: Optional[str] = None  # e.g., "gpt-4o-mini" or "gemini-pro"
	image_size: str = "1024x1024"


# base class for agents
class BaseAgent:
	"""Base memory holder with persistent prompt, per-request hint, and short history."""

	def __init__(self, name: str, config: Optional[AgentConfig] = None):
		"""Init with optional config and memory scaffolding."""
		self.name = name
		self.config = config or AgentConfig()
		
		# Ephemeral hint per-request (can change)
		self.prompt1: str = ""
		
		# Private base prompt (persistent instructions, set once at init)
		self._prompt: str = ""
		
		# Conversation memory: list of {role, content} dicts
		self._history: List[Dict[str, str]] = []

	def set_prompt1(self, text: str) -> None:
		"""Set a per-request hint that augments the base prompt."""
		self.prompt1 = text

	def set_prompt(self, text: str) -> None:
		"""Set the persistent system instructions for all calls."""
		self._prompt = text or ""

	def add_to_prompt(self, text: str) -> None:
		"""Append extra system guidance to the persistent prompt."""
		self._prompt = (self._prompt + "\n" + (text or "")).strip()

	def add_message(self, role: str, content: str) -> None:
		"""Store a message in history, keep only the last 20 entries."""
		# Append new message
		self._history.append({"role": role, "content": content})
		
		# Keep only last 20 messages to manage token usage
		if len(self._history) > 20:
			self._history = self._history[-20:]

	def clear_history(self) -> None:
		"""Reset the conversation log."""
		self._history.clear()

	def _history_to_text(self, max_chars: int = 2000) -> str:
		"""Render history as text, trimmed to max_chars."""
		# Join all messages with role labels
		joined = "\n".join(
			f"{m.get('role','unknown')}: {m.get('content','')}"
			for m in self._history
		)
		
		# Truncate if exceeds max_chars
		if len(joined) <= max_chars:
			return joined
		
		# Return last max_chars (more recent messages)
		return joined[-max_chars:]


class WorkflowAgent(BaseAgent):
	"""Planning agent implemented with LangGraph, supporting OpenAI/Gemini/Claude."""

	# PROMPT EDIT HOTSPOT: update the workflow-planning prompt text inside
	# _openai_plan/_gemini_plan/_claude_plan below to change planner behavior.

	class PlanningState(TypedDict):
		context: str
		prompt1: str
		prompt: str
		history_text: str
		steps: List[str]

	def plan_workflow(self, context: str) -> List[str]:
		provider = (self.config.provider or "local").lower()
		try:
			# Build a tiny LangGraph pipeline: one node -> END
			from langgraph.graph import StateGraph, END

			def planner_node(state: WorkflowAgent.PlanningState) -> WorkflowAgent.PlanningState:
				prompt1 = state.get("prompt1", "")
				ctx = state.get("context", "")
				prompt = state.get("prompt", "")
				history_text = state.get("history_text", "")
				steps = self._route_plan(provider, ctx, prompt1, prompt, history_text)
				return {"context": ctx, "prompt1": prompt1, "prompt": prompt, "history_text": history_text, "steps": steps}

			graph = StateGraph(WorkflowAgent.PlanningState)
			graph.add_node("planner", planner_node)
			graph.set_entry_point("planner")
			graph.add_edge("planner", END)
			app = graph.compile()

			result: WorkflowAgent.PlanningState = app.invoke({
				"context": context,
				"prompt1": self.prompt1,
				"prompt": self._prompt,
				"history_text": self._history_to_text(),
				"steps": [],
			})
			return result.get("steps", []) or self._local_plan(context)
		except Exception:
			# If langgraph isn't installed or fails, fallback
			return self._route_plan(provider, context, self.prompt1, self._prompt, self._history_to_text())

	def _route_plan(self, provider: str, context: str, prompt1: str, prompt: str, history_text: str) -> List[str]:
		if provider in ("local", ""):
			return self._local_plan(context)
		if provider == "openai":
			return self._openai_plan(context, prompt1, prompt, history_text)
		if provider == "gemini":
			return self._gemini_plan(context, prompt1, prompt, history_text)
		if provider in ("claude", "anthropic"):
			return self._claude_plan(context, prompt1, prompt, history_text)
		return self._local_plan(context)

	def _local_plan(self, context: str) -> List[str]:
		return [
			"Clarify scope, users, and success criteria",
			"Draft architecture (frontend, backend, data, auth)",
			"Set up repository structure and environments",
			"Scaffold backend API endpoints and models",
			"Integrate image generation module and storage",
			"Implement LangGraph planner and orchestration",
			"Write minimal tests and lint configs",
			"Wire frontend to backend and iterate on UX",
			"Prepare deployment (env vars, secrets, CI/CD)",
			"Run end-to-end test and document next milestones",
		]

	def _openai_plan(self, context: str, prompt1: str, prompt: str, history_text: str) -> List[str]:
		api_key = os.getenv("OPENAI_API_KEY")
		if not api_key:
			return self._local_plan(context)
		try:
			from openai import OpenAI
			client = OpenAI(api_key=api_key)
			model = self.config.llm_model or "gpt-4o-mini"
			prompt = (
				f"You are a planning assistant. Given the context, output a concise, "
				f"10-step actionable development workflow. Context: {context}. "
				f"Base Prompt: {prompt}. Incorporate: {prompt1}. "
				f"Conversation History: {history_text}. Return plain list items."
			)
			resp = client.chat.completions.create(
				model=model,
				messages=[
					{"role": "system", "content": "Return steps as plain list items."},
					{"role": "user", "content": prompt},
				],
				temperature=0.2,
			)
			content = resp.choices[0].message.content
			steps = [s.strip(" -") for s in content.split("\n") if s.strip()]
			return steps[:10] if steps else self._local_plan(context)
		except Exception:
			return self._local_plan(context)

	def _gemini_plan(self, context: str, prompt1: str, prompt: str, history_text: str) -> List[str]:
		api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
		if not api_key:
			return self._local_plan(context)
		try:
			import google.generativeai as genai
			genai.configure(api_key=api_key)
			model_name = self.config.llm_model or "gemini-1.5-flash"
			prompt = (
				f"Create a 10-step development workflow plan. Context: {context}. "
				f"Base Prompt: {prompt}. Incorporate: {prompt1}. "
				f"Conversation History: {history_text}. Return plain list items."
			)
			model = genai.GenerativeModel(model_name)
			resp = model.generate_content(prompt)
			text = getattr(resp, "text", "") or (resp.candidates[0].content.parts[0].text if getattr(resp, "candidates", None) else "")
			steps = [s.strip(" -") for s in text.split("\n") if s.strip()]
			return steps[:10] if steps else self._local_plan(context)
		except Exception:
			return self._local_plan(context)

	def _claude_plan(self, context: str, prompt1: str, prompt: str, history_text: str) -> List[str]:
		api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
		if not api_key:
			return self._local_plan(context)
		try:
			import anthropic
			client = anthropic.Anthropic(api_key=api_key)
			model = self.config.llm_model or "claude-3-5-sonnet-20240620"
			user_prompt = (
				f"Create exactly 10 concise, actionable steps for the development workflow.\n"
				f"Context: {context}\nIncorporate: {prompt1}\n"
				f"Base Prompt: {prompt}\nConversation History: {history_text}\n"
				f"Return plain list items, one per line."
			)
			msg = client.messages.create(
				model=model,
				max_tokens=800,
				messages=[{"role": "user", "content": user_prompt}],
			)
			# Extract text from Claude response
			text = ""
			for block in getattr(msg, "content", []) or []:
				if getattr(block, "type", "") == "text":
					text += getattr(block, "text", "") + "\n"
			steps = [s.strip(" -") for s in text.split("\n") if s.strip()]
			return steps[:10] if steps else self._local_plan(context)
		except Exception:
			return self._local_plan(context)


class ImageAgent(BaseAgent):
	"""Agent that handles image generation. Fallback creates a local placeholder."""

	def generate_image(self, prompt: str, out_path: str = "generated.png") -> str:
		provider = (self.config.provider or "local").lower()
		if provider == "openai":
			path = self._openai_image(prompt, out_path)
			if path:
				return path
		# Gemini image generation is not available via google-generativeai client; fallback
		return self._local_placeholder_image(prompt, out_path)

	def _openai_image(self, prompt: str, out_path: str) -> Optional[str]:
		api_key = os.getenv("OPENAI_API_KEY")
		if not api_key:
			return None
		try:
			from openai import OpenAI

			client = OpenAI(api_key=api_key)
			# DALL·E via Images API
			img = client.images.generate(
				model="gpt-image-1",
				prompt=prompt,
				size=self.config.image_size,
			)
			b64 = img.data[0].b64_json
			import base64

			with open(out_path, "wb") as f:
				f.write(base64.b64decode(b64))
			return out_path
		except Exception:
			return None

	def _local_placeholder_image(self, text: str, out_path: str) -> str:
		# Create a simple placeholder image locally, no API needed
		try:
			from PIL import Image, ImageDraw, ImageFont
		except Exception:
			raise RuntimeError("Pillow is required for local image generation. Add 'Pillow' to requirements.")

		width, height = (1024, 1024)
		img = Image.new("RGB", (width, height), color=(245, 245, 245))
		draw = ImageDraw.Draw(img)

		title = "Placeholder Image"
		body = (text or "No prompt provided")[:300]

		try:
			font_title = ImageFont.truetype("Arial.ttf", 48)
			font_body = ImageFont.truetype("Arial.ttf", 28)
		except Exception:
			font_title = ImageFont.load_default()
			font_body = ImageFont.load_default()

		draw.text((40, 40), title, fill=(20, 20, 20), font=font_title)
		draw.text((40, 120), body, fill=(60, 60, 60), font=font_body)

		img.save(out_path)
		return out_path


class LangGraphPlanner(WorkflowAgent):
	"""Workflow planner built on LangGraph, inherits routing/fallbacks."""
	def __init__(self, name: str = "langgraph-planner", config: Optional[AgentConfig] = None):
		super().__init__(name, config)


class AgentOrchestrator:
	"""Manage a class of AI agents and route tasks."""

	def __init__(self, config: Optional[AgentConfig] = None):
		self.config = config or AgentConfig()
		self.workflow_agent = LangGraphPlanner(config=self.config)
		self.image_agent = ImageAgent("image-agent", config=self.config)
		# Lazy-load specialized agents on demand
		self._sustainability_agent = None
		self._indigenous_context_agent = None
		self._proposal_workflow_agent = None

	def set_prompt1(self, text: str) -> None:
		self.workflow_agent.set_prompt1(text)
		self.image_agent.set_prompt1(text)

	def next_steps(self, context: str) -> List[str]:
		return self.workflow_agent.plan_workflow(context)

	def create_image(self, prompt: str, out_path: str = "generated.png") -> str:
		return self.image_agent.generate_image(prompt, out_path)

	@property
	def sustainability_agent(self):
		"""Lazy-load SustainabilityAgent."""
		if self._sustainability_agent is None:
			from specialized_agents import SustainabilityAgent
			self._sustainability_agent = SustainabilityAgent(config=self.config)
		return self._sustainability_agent

	@property
	def indigenous_context_agent(self):
		"""Lazy-load IndigenousContextAgent."""
		if self._indigenous_context_agent is None:
			from specialized_agents import IndigenousContextAgent
			self._indigenous_context_agent = IndigenousContextAgent(config=self.config)
		return self._indigenous_context_agent

	@property
	def proposal_workflow_agent(self):
		"""Lazy-load ProposalWorkflowAgent."""
		if self._proposal_workflow_agent is None:
			from specialized_agents import ProposalWorkflowAgent
			self._proposal_workflow_agent = ProposalWorkflowAgent(config=self.config)
		return self._proposal_workflow_agent

	def create_sustainability_agent(self, base_prompt: str = ""):
		"""Create a new SustainabilityAgent with optional base prompt."""
		from specialized_agents import SustainabilityAgent
		return SustainabilityAgent(config=self.config, base_prompt=base_prompt)

	def create_indigenous_context_agent(self, base_prompt: str = ""):
		"""Create a new IndigenousContextAgent with optional base prompt."""
		from specialized_agents import IndigenousContextAgent
		return IndigenousContextAgent(config=self.config, base_prompt=base_prompt)

	def create_proposal_workflow_agent(self, base_prompt: str = ""):
		"""Create a new ProposalWorkflowAgent with optional base prompt."""
		from specialized_agents import ProposalWorkflowAgent
		return ProposalWorkflowAgent(config=self.config, base_prompt=base_prompt)

