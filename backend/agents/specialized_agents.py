"""Specialized agents for sustainability analysis, indigenous context, and workflows."""

from __future__ import annotations

import os
from typing import List, Optional, Dict, Any, TypedDict
from agents import BaseAgent, AgentConfig
from backboard_provider import BackboardProvider


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

	def __init__(self, name: str = "sustainability-agent", config: Optional[AgentConfig] = None, base_prompt: str = ""):
		"""Init sustainability agent, wire Backboard Gemini assistant, cache prompts."""
		super().__init__(name, config)
		if base_prompt:
			self.set_prompt(base_prompt)
		
		# Initialize Backboard provider for unified LLM access
		try:
			from backboard_provider import BackboardProvider
			self.backboard = BackboardProvider()
			
			# Create Backboard assistant for Gemini
			self.assistant_id = self.backboard.create_assistant(
				name="Sustainability Analysis Expert",
				system_prompt=self._prompt or "You are an expert in sustainable land design that respects indigenous practices.",
				model="gemini-1.5-flash"
			)
		except Exception as e:
			print(f"  ⚠ Backboard initialization failed: {e}")
			self.backboard = None
			self.assistant_id = None
		
		# Cache storage for suggestions generated in this session
		self._redesign_suggestions: List[str] = []
		# Reserved for future feature: native flora data
		self._native_flowers: List[Dict[str, str]] = []

	def run_full_analysis(self, image_path: str, context: str = "", vision_output_path: str = None) -> Dict[str, Any]:
		"""Run analyze → redesign → vision via LangGraph when available, else sequential fallback."""
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
				future = self.generate_future_vision(state["image_path"], out_path)
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
				future = self.generate_future_vision(image_path, out_path)
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
		# Build prompt from memory system
		prompt = f"""
		{self._prompt}
		
		Based on this land analysis:
		{analysis_context}
		
		Generate 5 specific, actionable sustainable redesign suggestions that respect indigenous land use practices.
		Focus on water systems, native vegetation, wildlife corridors, and cultural significance.
		Format as a numbered list.
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
		
		# Subtle enhancement prompt - keep the landscape mostly the same, add sustainable features
		prompt = """Enhance this image by adding subtle sustainable and ecological improvements while keeping the overall layout and structure recognizable:

SUBTLE ADDITIONS (keep existing features, add these):
• Add bike lanes marked on roads - painted clearly but not intrusive
• Plant trees strategically along streets and open areas (20-30% more greenery, not overwhelming)
• Add small community gardens or green spaces in unused areas
• Increase water features modestly - small pond or rain garden if space allows
• Add green roofs or solar panels on existing buildings (visible but not dominating)
• Place benches and small parks in empty spaces
• Plant native vegetation and flowers in landscaping areas
• Add small walking/pedestrian paths through available spaces
• Improve visibility of any existing water features

IMPORTANT CONSTRAINTS:
• Keep the existing buildings, roads, and general structure recognizable and mostly unchanged
• The image should look like subtle improvements to the existing location, not a complete redesign
• Maintain the same perspective and scale as the original
• Make it look like realistic, achievable improvements you could implement in 5-10 years
• The overall composition should be very similar to the original, just enhanced

STYLE: Photorealistic, maintain existing colors and lighting, just show what this space could look like with thoughtful sustainable enhancements."""
		if extra_instructions.strip():
			prompt += f"\n\nEXTRA REQUESTS:\n{extra_instructions.strip()}\n"
		
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
				print(f"  ✓ Sustainable vision generated: {out_path} ({image_size} bytes)")
				
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

	def __init__(self, name: str = "indigenous-context-agent", config: Optional[AgentConfig] = None, base_prompt: str = ""):
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
		if base_prompt:
			self.set_prompt(base_prompt)
		
		# Initialize knowledge base storage (reserved for future feature)
		self._knowledge_base: List[Dict[str, str]] = []
		
		# Initialize proposal section builder (accumulates proposal content)
		self._proposal_sections: Dict[str, str] = {}
		
		# Initialize Backboard provider and assistant
		self.backboard: Optional[BackboardProvider] = None
		self.assistant_id: Optional[str] = None
		self.thread_id: Optional[str] = None
		
		try:
			# Create Backboard provider (handles API key loading)
			self.backboard = BackboardProvider()
			
			# Create Claude assistant with system prompt from memory
			# System prompt includes base_prompt (e.g., "Focus on indigenous practices")
			system_prompt = (
				f"You are an expert in indigenous land stewardship and perspectives. "
				f"Provide thoughtful, respectful guidance respecting tribal sovereignty. "
				f"{self._prompt}"
			)
			self.assistant_id = self.backboard.create_assistant(
				name="Indigenous Context Expert",
				system_prompt=system_prompt,
				model="claude-3-5-sonnet"
			)
			print(f"✓ Backboard Claude assistant created: {self.assistant_id}")
		except Exception as e:
			# Print warning but continue (will use local fallback in chat_with_context)
			print(f"⚠ Backboard initialization failed: {e}")
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
			# Call Backboard API
			# Returns (response_text, thread_id)
			response, self.thread_id = self.backboard.chat(
				self.assistant_id,
				query,
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

	def __init__(self, name: str = "proposal-workflow-agent", config: Optional[AgentConfig] = None, base_prompt: str = ""):
		"""Set prompts, init workflow tracking, and prep contacts list."""
		super().__init__(name, config)
		if base_prompt:
			self.set_prompt(base_prompt)
		
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
			print(f"✓ Backboard assistant created for ProposalWorkflowAgent: {self.assistant_id}")
		except Exception as e:
			print(f"⚠ Backboard initialization failed for ProposalWorkflowAgent: {e}")
		
		# Submission progress tracker
		self._submission_status: Dict[str, Any] = {
			"step": 0,
			"total_steps": 10
		}
		
		# Contact list for outreach
		self._contacts: List[Dict[str, str]] = []

	def get_submission_workflow(self, region: str) -> List[str]:
		"""
		GET STEP-BY-STEP WORKFLOW for proposal submission.
		
		CURRENT IMPLEMENTATION:
		  Returns generic 10-step workflow applicable to most regions.
		  
		FUTURE ENHANCEMENT:
		  Could customize workflow per region:
		    - British Columbia: Different tribal governance structures
		    - Alberta: Different regulatory requirements
		    - International: Different land rights frameworks
		
		  Example future implementation:
		    if region == "British Columbia":
		      return BC_SPECIFIC_WORKFLOW
		    elif region == "Alberta":
		      return ALBERTA_SPECIFIC_WORKFLOW
		
		PARAMETERS:
		  region: Geographic region for proposal (currently unused)
		         Could be used in future for region-specific workflows
		
		RETURNS:
		  List of 10 workflow steps as strings, e.g.:
		    [
		      "1. Finalize proposal with indigenous perspectives",
		      "2. Identify and document tribal leaders in region",
		      ...
		      "10. Execute agreement and implement with oversight"
		    ]
		
		USAGE:
		  workflow_steps = agent.get_submission_workflow("British Columbia")
		  for i, step in enumerate(workflow_steps):
		    print(f"{i+1}. {step}")
		"""
		# Generic 10-step workflow (can be customized per region in future)
		return [
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
		
		# PROMPT TUNING: adjust wording below to change outreach tone/content
		prompt = (
			f"Write a respectful, professional outreach email to {contact_name} "
			f"requesting consultation on a sustainable land development proposal titled '{proposal_title}'. "
			f"Emphasize indigenous sovereignty, community partnership, and respect for land stewardship. "
			f"Keep it concise (3-4 paragraphs). "
			f"Include subject line."
		)
		
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
