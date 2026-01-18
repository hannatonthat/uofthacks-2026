"""Specialized agents for sustainability analysis, indigenous context, and workflows."""

from __future__ import annotations

import os
from typing import List, Optional, Dict, Any, TypedDict
from .agents import BaseAgent, AgentConfig
from .backboard_provider import BackboardProvider
from .prompts_config import get_prompt, get_all_constraints


class SustainabilityAgent(BaseAgent):
	"""Analyzes land, proposes redesigns, and renders a future-vision image."""

	# Prompt tuning hotspot: update the redesign prompt in suggest_sustainable_redesign()
	# and the image prompt in generate_future_vision() when adjusting model behavior.

	class AnalysisState(TypedDict):
		"""Pipeline state container shared across steps."""
		image_path: str
		analysis: Dict[str, Any]
		redesign_suggestions: List[str]
		future_vision_path: str
		error: Optional[str]

	def __init__(self, name: str = "sustainability-agent", config: Optional[AgentConfig] = None, base_prompt: str = "", user_id: Optional[str] = None):
		"""Init sustainability agent, wire Backboard Gemini assistant, cache prompts."""
		super().__init__(name, config)
		self.thread_id: Optional[str] = None
		self.user_id = user_id  # For personalization tracking
		
		# Load prompts from centralized config
		loaded_base_prompt = get_prompt("sustainability_agent", "base_prompt")
		
		# Use provided base_prompt, fall back to loaded, or use default
		if base_prompt:
			self.set_prompt(base_prompt)
		elif loaded_base_prompt:
			self.set_prompt(loaded_base_prompt)
		else:
			self.set_prompt("Honor indigenous land stewardship practices. Prioritize water systems, biodiversity, and cultural significance.")
		
		# Initialize Backboard provider for unified LLM access
		try:
			from .backboard_provider import BackboardProvider
			self.backboard = BackboardProvider()
			
			# Create Backboard assistant for Gemini
			self.assistant_id = self.backboard.create_assistant(
				name="Sustainability Analysis Expert",
				system_prompt=self._prompt or "You are an expert in sustainable land design that respects indigenous practices.",
				model="gemini-1.5-flash"
			)
		except Exception as e:
			print(f"  [!] Backboard initialization failed: {e}")
			self.backboard = None
			self.assistant_id = None
		
		# Cache storage for suggestions generated in this session
		self._redesign_suggestions: List[str] = []
		# Reserved for future feature: native flora data
		self._native_flowers: List[Dict[str, str]] = []

	def chat_with_context(self, user_query: str, context: str = "") -> str:
		"""Chat entry point for sustainability agent with Backboard + local fallback."""
		constraints = get_all_constraints("sustainability_agent")
		constraint_text = "\n".join(f"- {c}" for c in constraints) if constraints else ""
		history_text = self._history_to_text()

		# NEW: Get personalization context from AnalyticsAgent
		personalization_prompt = ""
		if self.user_id:
			try:
				from .analytics_agent import AnalyticsAgent
				analytics = AnalyticsAgent()
				insights = analytics.get_rating_insights(user_id=self.user_id, agent_type="sustainability")
				personalization_prompt = insights.personalization_prompt
				
				# DEBUG: Show what's happening
				if insights.total_ratings > 0:
					print(f"\n🤖 ═══ AI PERSONALIZATION ACTIVE ═══")
					print(f"   👤 User: {self.user_id[:8]}...")
					print(f"   🎯 Agent: sustainability")
					print(f"   📊 Total ratings: {insights.total_ratings}")
					print(f"   ⭐ Avg rating: {insights.avg_rating:.2f} | Satisfaction: {insights.positive_percent:.1f}%")
					if insights.common_issues:
						print(f"   ⚠️  AI detected issues: {', '.join(insights.common_issues)}")
					if insights.ai_analysis:
						print(f"   🧠 AI Analysis: {insights.ai_analysis[:150]}...")
					if personalization_prompt:
						print(f"   ✨ Applying adaptation: {personalization_prompt[:100]}...")
					if insights.confidence_score > 0:
						print(f"   📈 Confidence: {insights.confidence_score:.0%}")
					print(f"   ═══════════════════════════════════\n")
				
			except Exception as e:
				print(f"  [!] Failed to get personalization insights: {e}")
				personalization_prompt = ""

		prompt_parts = [
			self._prompt or "You are an expert in sustainable land design that respects indigenous practices.",
			personalization_prompt,  # NEW: Add AI-generated personalization
			f"Context: {context}" if context else "Context: none provided",
			f"User request: {user_query}",
			"Constraints:",
			constraint_text,
			"Conversation so far:",
			history_text,
		]
		prompt = "\n\n".join(p for p in prompt_parts if p)

		self.add_message("user", user_query)

		response: str
		if self.backboard and self.assistant_id:
			try:
				response, self.thread_id = self.backboard.chat(self.assistant_id, prompt, self.thread_id)
			except Exception as e:
				response = self._local_fallback(user_query, context, f"Backboard error: {e}")
		else:
			response = self._local_fallback(user_query, context, "Backboard not initialized")

		self.add_message("assistant", response)
		return response

	def _local_fallback(self, user_query: str, context: str, reason: str = "") -> str:
		"""Offline fallback: deterministic, constraint-aware suggestions when LLM unavailable."""
		prefix = "Unable to reach model; using quick local guidance. "
		if reason:
			prefix += f"({reason}) "

		context_note = context or "small park"
		return (
			f"{prefix}Here are two respectful redesign ideas for {context_note}:\n"
			"1) Add native tree clusters, a rain garden, and permeable paths that protect waterways and honor existing gathering spaces.\n"
			"2) Create a quiet medicinal plant garden with signage about indigenous stewardship, plus shaded seating and a small play loop built from natural materials."
		)

	def run_full_analysis(self, image_path: str, context: str = "", vision_output_path: str = None) -> Dict[str, Any]:
		"""Run analyze -> redesign -> vision via LangGraph when available, else sequential fallback."""
		try:
			from langgraph.graph import StateGraph, END
			
			def analyze_node(state: SustainabilityAgent.AnalysisState) -> SustainabilityAgent.AnalysisState:
				analysis = self.analyze_land_image(state["image_path"])
				return {**state, "analysis": analysis}
			
			def redesign_node(state: SustainabilityAgent.AnalysisState) -> SustainabilityAgent.AnalysisState:
				analysis_context = context or str(state.get("analysis", {}))
				suggestions = self.suggest_sustainable_redesign(analysis_context)
				return {**state, "redesign_suggestions": suggestions}
			
			def vision_node(state: SustainabilityAgent.AnalysisState) -> SustainabilityAgent.AnalysisState:
				out_path = vision_output_path or f"future_vision_{state['image_path'].split('/')[-1]}"
				# Pass context as extra_instructions to the vision generation
				future = self.generate_future_vision(state["image_path"], out_path, extra_instructions=context)
				return {**state, "future_vision_path": future}
			
			graph = StateGraph(SustainabilityAgent.AnalysisState)
			graph.add_node("analyze", analyze_node)
			graph.add_node("redesign", redesign_node)
			graph.add_node("vision", vision_node)
			graph.set_entry_point("analyze")
			graph.add_edge("analyze", "redesign")
			graph.add_edge("redesign", "vision")
			graph.add_edge("vision", END)
			app = graph.compile()
			result: SustainabilityAgent.AnalysisState = app.invoke({
				"image_path": image_path,
				"analysis": {},
				"redesign_suggestions": [],
				"future_vision_path": vision_output_path or "",
				"error": None,
			})
			return {
				"image_path": image_path,
				"analysis": result.get("analysis", {}),
				"redesign_suggestions": result.get("redesign_suggestions", []),
				"future_vision_path": result.get("future_vision_path", vision_output_path),
				"error": None,
			}
		except Exception:
			# Fallback: simple sequential pipeline
			try:
				analysis = self.analyze_land_image(image_path)
				analysis_context = context or str(analysis)
				suggestions = self.suggest_sustainable_redesign(analysis_context)
				out_path = vision_output_path or f"future_vision_{image_path.split('/')[-1]}"
				# Pass context as extra_instructions to vision generation
				future = self.generate_future_vision(image_path, out_path, extra_instructions=context)
				return {
					"image_path": image_path,
					"analysis": analysis,
					"redesign_suggestions": suggestions,
					"future_vision_path": future,
					"error": None,
				}
			except Exception as e:
				out_path = vision_output_path or f"future_vision_{image_path.split('/')[-1]}"
				return {
					"image_path": image_path,
					"analysis": self.analyze_land_image(image_path),
					"redesign_suggestions": [],
					"future_vision_path": out_path,
					"error": str(e),
				}

	def analyze_land_image(self, image_path: str) -> Dict[str, Any]:
		"""Placeholder land analysis until a real vision model is wired."""
		# TODO: Integrate real vision API (OpenAI Vision, Gemini Vision, Claude Vision)
		return {
			"current_state": "Land analysis placeholder",
			"sustainability_score": 6.5,
			"recommendations": [
				"Preserve existing tree canopy",
				"Create water retention areas",
				"Maintain wildlife corridors",
				"Honor historical indigenous sites",
			],
			"image_path": image_path,
		}

	def suggest_sustainable_redesign(self, analysis_context: str) -> List[str]:
		"""Ask Backboard/Gemini for 5 redesign suggestions using base prompt + analysis."""
		# Load redesign suggestions prompt from config
		redesign_prompt = get_prompt("sustainability_agent", "redesign_suggestions_prompt")
		if not redesign_prompt:
			redesign_prompt = "Generate 5 specific, actionable sustainable redesign suggestions that respect indigenous land use practices. Focus on water systems, native vegetation, wildlife corridors, and cultural significance. Format as a numbered list."
		
		# Build prompt from memory system + loaded prompt
		prompt = f"""
		{self._prompt}
		
		Based on this land analysis:
		{analysis_context}
		
		{redesign_prompt}
		"""
		
		try:
			# Use Backboard to call Gemini
			response, _ = self.backboard.chat(
				self.assistant_id,
				prompt,
				None  # No thread persistence needed for single suggestion
			)
			
			# Parse response into suggestions list
			suggestions = response.strip().split("\n")
			suggestions = [s.strip() for s in suggestions if s.strip()]
			
			# Add response to conversation history for multi-turn context
			self.add_message("assistant", "\n".join(suggestions))
			
			# Cache in instance variable
			self._redesign_suggestions = suggestions
			return suggestions
		except Exception as e:
			raise RuntimeError(f"Failed to generate redesign suggestions: {e}")

	def generate_future_vision(self, image_path: str, out_path: str = "future_vision.png", extra_instructions: str = "") -> str:
		"""Generate a subtly enhanced vision image via Gemini 2.5 Flash (image + prompt)."""
		from google import genai
		from PIL import Image
		from io import BytesIO
		import os.path
		
		api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
		if not api_key:
			raise RuntimeError("GOOGLE_API_KEY or GEMINI_API_KEY not set in environment")
		
		client = genai.Client(api_key=api_key)
		
		if not os.path.exists(image_path):
			img = Image.new("RGB", (512, 512), color=(100, 150, 100))
			img.save("temp_image.png")
			image_to_process = "temp_image.png"
		else:
			image_to_process = image_path
		
		input_image = Image.open(image_to_process)
		print(f"  ℹ Generating sustainable vision with Gemini 2.5 Flash Image...")
		
		# Load image generation prompt from centralized config
		prompt = get_prompt("sustainability_agent", "future_vision_image_prompt")
		if not prompt:
			# Fallback to basic prompt if config not loaded
			prompt = "Enhance this image by adding subtle sustainable and ecological improvements while keeping the overall layout and structure recognizable."
		
		# Append extra instructions (user message) to the prompt
		if extra_instructions.strip():
			prompt += f"\n\nUSER REQUEST:\n{extra_instructions.strip()}\n"
		
		response = client.models.generate_content(
			model="gemini-2.5-flash-image",
			contents=[prompt, input_image],
		)
		
		for part in response.parts:
			if part.inline_data is not None and part.inline_data.mime_type == "image/png":
				image_bytes = part.inline_data.data
				generated_image = Image.open(BytesIO(image_bytes))
				generated_image.save(out_path)
				image_size = os.path.getsize(out_path)
				print(f"  [OK] Sustainable vision generated: {out_path} ({image_size} bytes)")
				
				# Clean up temp file if created
				if image_path != image_to_process and os.path.exists("temp_image.png"):
					os.remove("temp_image.png")
				
				return out_path
		
		# If no image in response
		raise RuntimeError("Gemini 2.5 Flash Image did not return an image in response")

	def edit_future_vision(self, image_path: str, out_path: str, instructions: str) -> str:
		"""Lightweight post-edit: overlay instructions onto the generated image (tweak as needed)."""
		try:
			from PIL import Image, ImageDraw, ImageFont
		except Exception as e:
			raise RuntimeError(f"Pillow not available for editing: {e}")

		if not os.path.exists(image_path):
			raise RuntimeError(f"Image to edit not found: {image_path}")

		base = Image.open(image_path).convert("RGBA")
		overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
		draw = ImageDraw.Draw(overlay)
		font = ImageFont.load_default()
		padding = 16
		box_height = 80
		box_color = (0, 0, 0, 140)
		text_color = (255, 255, 255, 255)
		# Draw translucent box at bottom
		draw.rectangle(
			[(0, base.height - box_height), (base.width, base.height)],
			fill=box_color,
		)
		# Render instruction text
		draw.text((padding, base.height - box_height + padding), instructions.strip(), font=font, fill=text_color)
		# Merge and save
		edited = Image.alpha_composite(base, overlay).convert("RGB")
		edited.save(out_path)
		return out_path


class IndigenousContextAgent(BaseAgent):
	"""Adds indigenous context, builds proposal sections, and persists threads via Backboard."""

	def __init__(self, name: str = "indigenous-context-agent", config: Optional[AgentConfig] = None, base_prompt: str = "", user_id: Optional[str] = None):
		"""
		Initialize IndigenousContextAgent with Backboard.io integration.
		
		PARAMETERS:
		  name: Agent identifier for logging/identification
		  config: AgentConfig (currently unused, Claude only)
		  base_prompt: System-level instructions for all Backboard requests
		              Example: "Focus on ancestral land use and cultural significance"
		
		INITIALIZATION FLOW:
		  1. Call parent BaseAgent.__init__() for memory system
		  2. If base_prompt provided, store it via set_prompt()
		  3. Initialize Backboard.io provider:
		     - Load BACKBOARD_API_KEY from environment
		     - Create Claude assistant with system_prompt = self._prompt
		  4. Initialize thread_id = None (created on first chat)
		  5. Initialize _proposal_sections dict for incremental proposal building
		
		BACKBOARD INITIALIZATION:
		  - BackboardProvider loads API key automatically
		  - Requires BACKBOARD_API_KEY environment variable
		  - create_assistant() returns assistant_id
		  - Thread created on first chat() call (auto-managed)
		
		ERROR HANDLING:
		  Catches exceptions during Backboard init and prints warning.
		  Falls back to local responses if Backboard unavailable.
		  This allows development/testing without API key.
		"""
		super().__init__(name, config)
		
		# Load prompts from centralized config
		loaded_base_prompt = get_prompt("indigenous_context_agent", "base_prompt")
		
		# Use provided base_prompt, fall back to loaded, or use default
		if base_prompt:
			self.set_prompt(base_prompt)
		elif loaded_base_prompt:
			self.set_prompt(loaded_base_prompt)
		else:
			self.set_prompt("Focus on indigenous land stewardship principles. Prioritize tribal sovereignty and long-term ecological stewardship.")
		
		# Initialize knowledge base storage (reserved for future feature)
		self._knowledge_base: List[Dict[str, str]] = []
		
		# Initialize proposal section builder (accumulates proposal content)
		self._proposal_sections: Dict[str, str] = {}
		
		# Initialize Backboard provider and assistant
		self.backboard: Optional[BackboardProvider] = None
		self.assistant_id: Optional[str] = None
		self.thread_id: Optional[str] = None
		self.user_id = user_id  # For personalization tracking
		
		try:
			# Create Backboard provider (handles API key loading)
			self.backboard = BackboardProvider()
			
			# Load system prompt addition from config
			system_addition = get_prompt("indigenous_context_agent", "system_prompt_addition")
			if not system_addition:
				system_addition = "You are an expert in indigenous land stewardship and perspectives. Provide thoughtful, respectful guidance respecting tribal sovereignty."
			
			# Create Claude assistant with system prompt from memory
			system_prompt = (
				f"{system_addition} {self._prompt}"
			)
			self.assistant_id = self.backboard.create_assistant(
				name="Indigenous Context Expert",
				system_prompt=system_prompt,
				model="claude-3-5-sonnet"
			)
			print(f"[OK] Backboard Claude assistant created: {self.assistant_id}")
		except Exception as e:
			# Print warning but continue (will use local fallback in chat_with_context)
			print(f"[!] Backboard initialization failed: {e}")
			print(f"  Will use local fallback for responses")

	def chat_with_context(self, user_query: str) -> str:
		"""
		MAIN ENTRY POINT: Chat with indigenous context expert.
		
		PROCESS:
		  1. If Backboard initialized successfully:
		     - Call _backboard_chat() to use Claude via Backboard
		     - Maintains thread_id for conversation history
		  2. If Backboard not available:
		     - (No local fallback - force explicit Backboard setup)
		     - Will fail with error message
		
		PARAMETERS:
		  user_query: User's question about indigenous perspectives
		             Example: "What water resources should we protect?"
		
		RETURNS:
		  Claude's response string (or error message)
		
		THREAD MANAGEMENT:
		  - First call creates thread_id automatically
		  - Subsequent calls reuse same thread_id
		  - Full conversation history maintained server-side by Backboard
		  - Can persist thread_id to database for resuming later
		
		EXAMPLE MULTI-TURN CONVERSATION:
		  agent.chat_with_context("What are sacred sites?")  # Creates thread
		  agent.chat_with_context("How do we protect them?")  # Uses same thread
		  # Backboard remembers both messages and context
		"""
		if self.backboard and self.assistant_id:
			return self._backboard_chat(user_query)
		else:
			# No local fallback - require explicit Backboard setup
			raise RuntimeError(
				"Backboard not initialized. Ensure BACKBOARD_API_KEY is set in .env"
			)

	def _backboard_chat(self, query: str) -> str:
		"""
		Chat using Backboard.io Claude API.
		
		PROCESS:
		  1. Call self.backboard.chat():
		     - Sends query to Claude assistant
		     - Auto-creates thread_id on first call
		     - Reuses thread_id for subsequent calls
		     - Returns (response_text, thread_id)
		  2. Update self.thread_id for next call (thread persistence)
		  3. Add messages to local history via add_message():
		     - Ensures conversation is logged locally
		     - Allows _history_to_text() to access messages
		  4. Return Claude's response
		
		PARAMETERS:
		  query: User's message to send to Claude
		
		RETURNS:
		  Claude's response string
		
		THREAD PERSISTENCE:
		  - self.thread_id updated each call
		  - Should be persisted to database for session resumption
		  - Example storage: proposals.thread_id in SQLAlchemy model
		
		ERROR HANDLING:
		  Raises RuntimeError if Backboard API fails.
		
		DEPENDENCIES:
		  - Backboard.io REST API
		  - self.backboard must be initialized
		  - self.assistant_id must be created
		"""
		try:
			# NEW: Get personalization context
			personalization_prompt = ""
			if self.user_id:
				try:
					from .analytics_agent import AnalyticsAgent
					analytics = AnalyticsAgent()
					insights = analytics.get_rating_insights(user_id=self.user_id, agent_type="indigenous")
					personalization_prompt = insights.personalization_prompt
					
					# DEBUG: Show what's happening
					if insights.total_ratings > 0:
						print(f"\n🤖 ═══ AI PERSONALIZATION ACTIVE ═══")
						print(f"   👤 User: {self.user_id[:8]}...")
						print(f"   🎯 Agent: indigenous")
						print(f"   📊 Total ratings: {insights.total_ratings}")
						print(f"   ⭐ Avg rating: {insights.avg_rating:.2f} | Satisfaction: {insights.positive_percent:.1f}%")
						if insights.common_issues:
							print(f"   ⚠️  AI detected issues: {', '.join(insights.common_issues)}")
						if insights.ai_analysis:
							print(f"   🧠 AI Analysis: {insights.ai_analysis[:150]}...")
						if personalization_prompt:
							print(f"   ✨ Applying adaptation: {personalization_prompt[:100]}...")
						if insights.confidence_score > 0:
							print(f"   📈 Confidence: {insights.confidence_score:.0%}")
						print(f"   ═══════════════════════════════════\n")
					
				except Exception as e:
					print(f"  [!] Failed to get personalization insights: {e}")
			
			# Prepend personalization to query
			enhanced_query = query
			if personalization_prompt:
				enhanced_query = f"{personalization_prompt}\n\n{query}"
			
			# Call Backboard API
			# Returns (response_text, thread_id)
			response, self.thread_id = self.backboard.chat(
				self.assistant_id,
				enhanced_query,
				self.thread_id
			)
			
			# Add messages to local history for logging/recall
			self.add_message("user", query)
			self.add_message("assistant", response)
			
			return response
		except Exception as e:
			raise RuntimeError(f"Backboard API error: {e}")

	def add_proposal_section(self, section_name: str, content: str) -> None:
		"""
		ADD SECTION TO BUILDING PROPOSAL.
		
		PROCESS:
		  1. Store content in self._proposal_sections[section_name]
		  2. Log action to conversation history
		  3. Allows incremental proposal building
		
		PARAMETERS:
		  section_name: Name of proposal section (e.g., "Water Systems", "Sacred Sites")
		  content: Content for this section (text from user or agent)
		
		EXAMPLE:
		  agent.add_proposal_section("Water Systems", "Protect existing streams...")
		  agent.add_proposal_section("Wildlife", "Maintain deer migration corridors...")
		  proposal_doc = agent.build_proposal_document()
		  # proposal_doc will have both sections formatted together
		
		USAGE IN WORKFLOW:
		  1. User asks question via chat_with_context()
		  2. Get Claude response
		  3. Call add_proposal_section() to save response to proposal
		  4. Repeat for different sections
		  5. Call build_proposal_document() to export final proposal
		"""
		self._proposal_sections[section_name] = content
		self.add_message("user", f"Added proposal section: {section_name}")

	def build_proposal_document(self) -> str:
		"""
		BUILD COMPLETE PROPOSAL DOCUMENT from accumulated sections.
		
		PROCESS:
		  1. Start with markdown header
		  2. Iterate through self._proposal_sections (preserves insertion order in Python 3.7+)
		  3. Format each section as markdown:
		     ## Section Name
		     Content
		  4. Append conversation history summary at end
		  5. Return complete proposal as string
		
		RETURNS:
		  String with complete proposal document (markdown formatted)
		
		EXAMPLE OUTPUT:
		  # Indigenous Perspectives Development Proposal
		  
		  ## Water Systems
		  Protect existing streams and wetlands...
		  
		  ## Sacred Sites
		  Honor traditional gathering places...
		  
		  ## Conversation History
		  [Summary of previous messages...]
		
		USAGE:
		  1. Build proposal via multiple add_proposal_section() calls
		  2. Call build_proposal_document()
		  3. Save to file or send to ProposalWorkflowAgent
		  4. Can export as markdown or convert to PDF
		"""
		doc = "# Indigenous Perspectives Development Proposal\n\n"
		
		# Add each proposal section
		for section, content in self._proposal_sections.items():
			doc += f"## {section}\n{content}\n\n"
		
		# Add conversation history summary
		doc += f"## Conversation History\n{self._history_to_text(max_chars=1000)}\n"
		
		return doc


class ProposalWorkflowAgent(BaseAgent):
	"""Manages 10-step submission workflow, contacts, and outreach emails."""

	def __init__(self, name: str = "proposal-workflow-agent", config: Optional[AgentConfig] = None, base_prompt: str = "", user_id: Optional[str] = None):
		"""Set prompts, init workflow tracking, and prep contacts list."""
		super().__init__(name, config)
		self.user_id = user_id  # For personalization tracking
		
		# Load prompts from centralized config
		loaded_base_prompt = get_prompt("proposal_workflow_agent", "base_prompt")
		
		# Use provided base_prompt, fall back to loaded, or use default
		if base_prompt:
			self.set_prompt(base_prompt)
		elif loaded_base_prompt:
			self.set_prompt(loaded_base_prompt)
		else:
			self.set_prompt("Ensure all outreach emphasizes community-led decision-making and respect for indigenous sovereignty.")
		
		# Initialize Backboard provider and assistant for email generation
		self.backboard: Optional[BackboardProvider] = None
		self.assistant_id: Optional[str] = None
		
		try:
			self.backboard = BackboardProvider()
			system_prompt = (
				f"You are an expert at writing respectful, professional outreach emails "
				f"that emphasize indigenous sovereignty and community partnership. "
				f"{self._prompt}"
			)
			self.assistant_id = self.backboard.create_assistant(
				name="Outreach Email Expert",
				system_prompt=system_prompt,
				model="gpt-4o-mini"
			)
			print(f"[OK] Backboard assistant created for ProposalWorkflowAgent: {self.assistant_id}")
		except Exception as e:
			print(f"[!] Backboard initialization failed for ProposalWorkflowAgent: {e}")
		
		# Thread tracking for conversation history
		self.thread_id: Optional[str] = None
		
		# Submission progress tracker
		self._submission_status: Dict[str, Any] = {
			"step": 0,
			"total_steps": 10
		}
		
		# Contact list for outreach
		self._contacts: List[Dict[str, str]] = []

	def get_submission_workflow(self, region: str) -> List[str]:
		"""
		GET STEP-BY-STEP WORKFLOW for proposal submission with AI-powered personalization.
		
		NEW: Uses AnalyticsAgent to adapt workflow based on user completion patterns.
		
		PARAMETERS:
		  region: Geographic region for proposal
		
		RETURNS:
		  List of workflow steps, potentially reordered/simplified based on analytics
		"""
		# Default 10-step workflow
		default_workflow = [
			"1. Finalize proposal document with all indigenous perspectives",
			"2. Identify and document tribal leaders and organizations in the region",
			"3. Schedule initial consultation meetings with indigenous representatives",
			"4. Incorporate feedback and refine proposal based on community input",
			"5. Prepare formal submission package with respectful cover letter",
			"6. Submit to tribal council, land management, and local authorities",
			"7. Track responses and schedule follow-up conversations",
			"8. Iterate and adapt proposal based on community input",
			"9. Prepare environmental and cultural impact assessment",
			"10. Execute final agreement and begin implementation with community oversight",
		]
		
		# NEW: Get workflow insights from analytics
		try:
			from .analytics_agent import AnalyticsAgent
			analytics = AnalyticsAgent()
			insights = analytics.get_workflow_insights(region=region)
			
			# If certain steps are commonly skipped, we could reorder or simplify
			# For now, just return default but this shows the integration point
			skipped_steps = insights.get("common_skipped_steps", [])
			if skipped_steps:
				print(f"  [Analytics] Steps {skipped_steps} commonly skipped - consider simplification")
			
		except Exception as e:
			print(f"  [!] Failed to get workflow insights: {e}")
		
		return default_workflow

	def add_contact(self, name: str, role: str, email: str, phone: str = "") -> None:
		"""
		ADD CONTACT to outreach list.
		
		PARAMETERS:
		  name: Person's name (e.g., "Chief Sarah")
		  role: Their role (e.g., "Tribal Leader", "Environmental Manager")
		  email: Email address for outreach
		  phone: Optional phone number for follow-up
		
		PROCESS:
		  1. Create dict with contact info
		  2. Append to self._contacts list
		  3. Log to conversation history
		
		EXAMPLE:
		  agent.add_contact("Chief Sarah", "Tribal Leader", "sarah@tribe.ca", "250-555-1234")
		  agent.add_contact("Dr. James", "Environmental Officer", "james@env.gov.bc.ca")
		
		USAGE IN WORKFLOW:
		  1. Add all contacts via repeated add_contact() calls
		  2. Call get_contacts() to see full list
		  3. Generate emails for each contact via generate_outreach_email()
		  4. Send emails (integration point for email provider)
		"""
		self._contacts.append({
			"name": name,
			"role": role,
			"email": email,
			"phone": phone,
		})
		self.add_message("system", f"Contact added: {name} ({role})")

	def get_contacts(self) -> List[Dict[str, str]]:
		"""
		RETRIEVE FULL CONTACT LIST.
		
		RETURNS:
		  List of contact dicts with keys: name, role, email, phone
		  
		EXAMPLE:
		  contacts = agent.get_contacts()
		  for contact in contacts:
		    print(f"{contact['name']}: {contact['email']}")
		"""
		return self._contacts

	def generate_outreach_email(self, contact_name: str, proposal_title: str) -> str:
		"""Generate a respectful outreach email via Backboard (prompt below is the tweak point)."""
		if not self.backboard or not self.assistant_id:
			raise RuntimeError("Backboard not initialized. Ensure BACKBOARD_API_KEY is set in environment.")
		
		# Load email prompt from config
		email_prompt_template = get_prompt("proposal_workflow_agent", "outreach_email_prompt")
		if not email_prompt_template:
			email_prompt_template = (
				f"Write a respectful, professional outreach email to {{contact_name}} "
				f"requesting consultation on a sustainable land development proposal titled '{{proposal_title}}'. "
				f"Emphasize indigenous sovereignty, community partnership, and respect for land stewardship. "
				f"Keep it concise (3-4 paragraphs). Include subject line."
			)
		
		prompt = email_prompt_template.format(contact_name=contact_name, proposal_title=proposal_title)
		
		try:
			# Use Backboard to generate email (routes to configured model)
			response, _ = self.backboard.chat(
				self.assistant_id,
				prompt,
				None  # No thread persistence needed for email generation
			)
			return response
		except Exception as e:
			raise RuntimeError(f"Backboard API error: {e}")

	def update_submission_status(self, step: int, total_steps: int) -> None:
		"""
		UPDATE WORKFLOW PROGRESS.
		
		PARAMETERS:
		  step: Current step number (1-10)
		  total_steps: Total steps in workflow (always 10 for current workflow)
		
		EXAMPLE:
		  agent.update_submission_status(3, 10)  # On step 3 of 10
		  # Indicates: Scheduled consultation meetings (step 3)
		"""
		self._submission_status = {
			"step": step,
			"total_steps": total_steps
		}

	def get_submission_status(self) -> Dict[str, Any]:
		"""
		GET CURRENT SUBMISSION PROGRESS.
		
		RETURNS:
		  Dict with:
		    - step: Current step (0-10)
		    - total_steps: Total steps (always 10)
		
		EXAMPLE:
		  status = agent.get_submission_status()
		  print(f"Progress: {status['step']}/{status['total_steps']}")
		"""
		return self._submission_status

	def chat_with_context(self, user_query: str) -> str:
		"""
		MAIN ENTRY POINT: Chat with proposal workflow expert via Backboard.
		
		PROCESS:
		  1. If Backboard initialized: use Claude/GPT to answer workflow questions
		  2. If Backboard not available: return error
		
		PARAMETERS:
		  user_query: User's question about workflow, contacts, or next steps
		             Example: "What are the workflow steps for British Columbia?"
		
		RETURNS:
		  Claude/GPT response string (or error message)
		
		THREAD MANAGEMENT:
		  - Thread created automatically on first call
		  - Subsequent calls reuse thread for conversation history
		  - Full history maintained server-side by Backboard
		
		EXAMPLE USAGE:
		  agent.chat_with_context("What are the submission steps?")
		  agent.chat_with_context("How do I write an outreach email?")
		"""
		if self.backboard and self.assistant_id:
			try:
				# NEW: Get personalization context (CROSS-AGENT LEARNING!)
				personalization_prompt = ""
				if self.user_id:
					try:
						from .analytics_agent import AnalyticsAgent
						analytics = AnalyticsAgent()
						
						# Get insights from ALL agents (not just proposal)
						all_insights = analytics.get_rating_insights(user_id=self.user_id, agent_type=None)
						proposal_insights = analytics.get_rating_insights(user_id=self.user_id, agent_type="proposal")
						
						# Use cross-agent insights if we have them, otherwise use proposal-specific
						if all_insights.total_ratings > 0:
							insights = all_insights
							personalization_prompt = insights.personalization_prompt
						else:
							insights = proposal_insights
							personalization_prompt = insights.personalization_prompt
						
						# DEBUG: Show what's happening
						if insights.total_ratings > 0:
							print(f"\n🤖 ═══ CROSS-AGENT AI LEARNING ═══")
							print(f"   👤 User: {self.user_id[:8]}...")
							print(f"   🎯 Agent: proposal (learning from ALL agents)")
							print(f"   📊 Total ratings across ALL agents: {insights.total_ratings}")
							print(f"   ⭐ Avg rating: {insights.avg_rating:.2f} | Satisfaction: {insights.positive_percent:.1f}%")
							if insights.common_issues:
								print(f"   ⚠️  AI detected issues: {', '.join(insights.common_issues)}")
							if insights.ai_analysis:
								print(f"   🧠 AI Analysis: {insights.ai_analysis[:150]}...")
							if personalization_prompt:
								print(f"   ✨ Applying adaptation: {personalization_prompt[:100]}...")
							if insights.confidence_score > 0:
								print(f"   📈 Confidence: {insights.confidence_score:.0%}")
							print(f"   ═══════════════════════════════════\n")
						
					except Exception as e:
						print(f"  [!] Failed to get personalization insights: {e}")
				
				# Prepend personalization to query
				enhanced_query = user_query
				if personalization_prompt:
					enhanced_query = f"{personalization_prompt}\n\n{user_query}"
				
				# Use Backboard to chat with the model
				response, thread_id = self.backboard.chat(
					self.assistant_id,
					enhanced_query,
					getattr(self, 'thread_id', None)
				)
				self.thread_id = thread_id
				self.add_message("user", user_query)
				self.add_message("assistant", response)
				return response
			except Exception as e:
				raise RuntimeError(f"Backboard API error: {e}")
		else:
			raise RuntimeError(
				"Backboard not initialized. Ensure BACKBOARD_API_KEY is set in .env"
			)
