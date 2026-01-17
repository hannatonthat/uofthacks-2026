"""
DEMO: THREE SPECIALIZED AGENTS FOR LAND DEVELOPMENT PROPOSALS

This script demonstrates all three specialized agents working together via Backboard.io:

1. SustainabilityAgent (Gemini via Backboard.io)
   - Analyzes land images for sustainability
   - Generates sustainable redesign suggestions
   - Creates before/after future vision images
   - Full 3-node LangGraph pipeline
   - Model: gemini-1.5-flash (via Backboard unified API)

2. IndigenousContextAgent (Claude via Backboard.io)
   - Multi-turn conversations with indigenous context
   - Thread-based persistence (conversation history maintained)
   - Incremental proposal document building
   - Respects indigenous knowledge and perspectives
   - Model: claude-3-5-sonnet (via Backboard unified API)

3. ProposalWorkflowAgent (OpenAI via Backboard.io)
   - 10-step submission workflow guidance
   - Contact management (tribal leaders, authorities)
   - Respectful outreach email generation
   - Submission status tracking
   - Model: gpt-4o-mini (via Backboard unified API)

UNIFIED API APPROACH:
  All agents use Backboard.io as the unified LLM platform
  - Single BACKBOARD_API_KEY environment variable required
  - No need for individual GEMINI_API_KEY, OPENAI_API_KEY, etc.
  - Easy to switch models (config only, no code changes)
  - Backboard handles token counting, rate limiting, caching

RUNNING THE DEMO:
  # Requires BACKBOARD_API_KEY in .env
  python demo_specialized.py
  
  # With local fallbacks (no API key needed)
  python demo_specialized.py
  
ENVIRONMENT VARIABLES:
  BACKBOARD_API_KEY: Required for all agents (unified access)
  
  Optional fallback when API unavailable:
  - SustainabilityAgent: Uses local suggestion list
  - IndigenousContextAgent: Uses local knowledge base
  - ProposalWorkflowAgent: Uses local email template
  
OUTPUT:
  - Sustainability analysis + 5 redesign suggestions + future vision image
  - Multi-turn indigenous context conversation
  - Sample proposal document
  - 10-step workflow guide
  - Sample outreach email
"""

from agents.agents import AgentConfig, AgentOrchestrator
import os
import sys
from pathlib import Path

# Load .env file from parent directory
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
	from dotenv import load_dotenv
	load_dotenv(env_path)



def demo_specialized_agents(output_images: bool = False, image_dir: str = "output"):
	"""
	DEMONSTRATE ALL THREE SPECIALIZED AGENTS.
	
	PROCESS:
	  1. Load configuration from environment
	  2. Create orchestrator (agent factory)
	  3. Instantiate each agent with base_prompt
	  4. Run example workflows for each
	  5. Show outputs and integrations
	
	ENVIRONMENT:
	    AGENT_PROVIDER: Routing hint ("local", "openai", "gemini")
	    LLM_MODEL: Optional model override
	    API_KEY variables: For each LLM provider
	    
	API KEY REQUIREMENTS:
	    - SustainabilityAgent: GEMINI_API_KEY (or GOOGLE_API_KEY) for real Gemini calls
	    - IndigenousContextAgent: BACKBOARD_API_KEY for Claude via Backboard
	    - ProposalWorkflowAgent: OPENAI_API_KEY for email generation
	"""
	
	# Load configuration from environment
	provider = os.getenv("AGENT_PROVIDER", "local")  # Use "local" for testing without API keys
	cfg = AgentConfig(provider=provider, llm_model=os.getenv("LLM_MODEL"))
	
	# Create orchestrator (factory for all agents)
	orchestrator = AgentOrchestrator(config=cfg)

	print("=" * 70)
	print("SPECIALIZED AGENTS DEMO")
	print(f"Provider: {provider} (set AGENT_PROVIDER env var to change)")
	print("=" * 70)

	# ====================================================================
	# AGENT 1: SUSTAINABILITY AGENT
	# Purpose: Full sustainability analysis pipeline with LangGraph
	# Model: Gemini
	# Workflow: Analyze land -> Suggest redesign -> Generate future vision
	# ====================================================================
	print("\n[AGENT 1: SustainabilityAgent]")
	print("Purpose: Full sustainability analysis pipeline with LangGraph")
	print("Model: Gemini (via Google GenerativeAI SDK)")
	print("Workflow: analyze -> suggest_redesign -> generate_future_vision\n")

	# Create SustainabilityAgent with custom base instructions
	sustainability = orchestrator.create_sustainability_agent(
		base_prompt=(
			"Honor indigenous land stewardship practices. "
			"Prioritize water systems, biodiversity, and cultural significance."
		)
	)

	# Run full LangGraph pipeline
	# This orchestrates 3 steps through LangGraph StateGraph:
	#   Step 1: analyze_land_image(image_path)
	#   Step 2: suggest_sustainable_redesign(analysis_context)
	#   Step 3: generate_future_vision(image_path)
	print("Running full sustainability analysis pipeline...\n")
	
	# Prepare image output path if requested
	vision_output_path = None
	if output_images:
		os.makedirs(image_dir, exist_ok=True)
		vision_output_path = os.path.join(image_dir, "future_vision.png")
	
	# Run analysis with optional image output
	result = sustainability.run_full_analysis(
		"example_land.png",
		"Urban expansion near a cultural heritage site with water resources",
		vision_output_path
	)
	
	# Display analysis results
	print("ANALYSIS RESULTS:")
	print(f"  Image: {result['image_path']}")
	print(f"  Current Analysis: {result['analysis']}")
	
	# Display redesign suggestions from Gemini
	print("\nREDESIGN SUGGESTIONS (from Gemini):")
	for i, suggestion in enumerate(result['redesign_suggestions'], 1):
		print(f"  {i}. {suggestion}")
	
	# Display future vision image path
	print(f"\nFUTURE VISION IMAGE: {result['future_vision_path']}")
	if result.get('error'):
		print(f"  [!] Pipeline note: {result['error']}")
	# Optional: regenerate through Gemini with extra context for indigenous architecture
	if output_images and not result.get('error'):
		more_context = "Integrate visible indigenous architecture elements (e.g., community longhouse motifs, natural materials) while keeping the existing layout and scale subtle and realistic."
		source_img = result['future_vision_path']
		regenerated_path = os.path.join(image_dir, "future_vision_1.png")
		try:
			regen = sustainability.generate_future_vision(
				source_img,
				regenerated_path,
				extra_instructions=more_context,
			)
			print(f"  [OK] Regenerated with indigenous architecture context: {regen}")
		except Exception as e:
			print(f"  [!] Could not regenerate with indigenous architecture context: {e}")

	

	# ====================================================================
	# AGENT 2: INDIGENOUS CONTEXT AGENT
	# Purpose: Multi-turn indigenous perspectives conversation
	# Model: Claude (via Backboard.io)
	# Workflow: Chat with context -> Add proposal sections -> Build document
	# ====================================================================
	print("\n" + "=" * 70)
	print("[AGENT 2: IndigenousContextAgent]")
	print("Purpose: Provide indigenous context, build proposal documents")
	print("Model: Claude (via Backboard.io REST API)")
	print("Workflow: Multi-turn chat -> Incremental proposal building\n")

	# Create IndigenousContextAgent with regional context
	indigenous = orchestrator.create_indigenous_context_agent(
		base_prompt=(
			"Focus on Haudenosaunee land stewardship principles "
			"and Mohawk Nation history in the Toronto region. "
			"Prioritize tribal sovereignty and long-term ecological stewardship."
		)
	)

	# MULTI-TURN CONVERSATION
	# First message (creates thread_id automatically)
	query1 = "What are the key principles of indigenous land management?"
	print(f"Q1: {query1}")
	response1 = indigenous.chat_with_context(query1)
	print(f"A1: {response1}\n")
	print(f"  [Thread ID persisted for conversation continuity]\n")

	# Build proposal document incrementally
	# Each section can come from user input or Claude suggestions
	print("Building proposal document incrementally:")
	indigenous.add_proposal_section(
		"Project Overview",
		"Sustainable land development respecting indigenous sovereignty and ecological integrity."
	)
	print("  [OK] Added 'Project Overview' section")
	
	indigenous.add_proposal_section(
		"Community Consultation",
		"Early, respectful engagement with local tribes and land stewards."
	)
	print("  [OK] Added 'Community Consultation' section\n")

	# Export proposal document
	print("GENERATED PROPOSAL DOCUMENT (excerpt):")
	proposal = indigenous.build_proposal_document()
	print(proposal[:500] + "...\n")
	print("  [Full proposal includes all sections + conversation history]\n")

	# ====================================================================
	# AGENT 3: PROPOSAL WORKFLOW AGENT
	# Purpose: Submission workflow management and outreach
	# Model: OpenAI (via OpenAI SDK)
	# Workflow: Get workflow steps -> Manage contacts -> Generate emails
	# ====================================================================
	print("=" * 70)
	print("[AGENT 3: ProposalWorkflowAgent]")
	print("Purpose: Manage submission workflow, contacts, email outreach")
	print("Model: OpenAI (gpt-4o-mini)")
	print("Workflow: Workflow steps -> Contact management -> Email generation\n")

	# Create ProposalWorkflowAgent with outreach guidelines
	workflow = orchestrator.create_proposal_workflow_agent(
		base_prompt=(
			"Ensure all outreach emphasizes community-led decision-making "
			"and respect for indigenous sovereignty. "
			"Generate emails that are respectful and professional."
		)
	)

	# Display 10-step submission workflow
	print("10-STEP SUBMISSION WORKFLOW:")
	steps = workflow.get_submission_workflow("Toronto Region")
	for step in steps:
		print(f"  {step}")

	# Manage contact list
	print("\nMANAGING CONTACTS:")
	print("  Adding tribal leader...")
	workflow.add_contact(
		"Chief Maria Smith",
		"Haudenosaunee Council Leader",
		"maria@example.com",
		"+1-555-0101"
	)
	print("  [OK] Added Chief Maria Smith")
	
	print("  Adding environmental coordinator...")
	workflow.add_contact(
		"Dr. James Deer",
		"Indigenous Land Stewardship Coordinator",
		"james@example.com"
	)
	print("  [OK] Added Dr. James Deer")
	
	contacts = workflow.get_contacts()
	print(f"\nTOTAL CONTACTS: {len(contacts)}")
	for contact in contacts:
		print(f"  - {contact['name']} ({contact['role']}): {contact['email']}\n")

	# Generate respectful outreach email
	print("GENERATING OUTREACH EMAIL:")
	print("  Recipient: Chief Maria Smith")
	print("  Proposal: Sustainable Urban Green Space with Indigenous Perspectives\n")
	email = workflow.generate_outreach_email(
		"Chief Maria Smith",
		"Sustainable Urban Green Space with Indigenous Perspectives"
	)
	print("GENERATED EMAIL:")
	print("-" * 70)
	print(email)
	print("-" * 70)

	# Display workflow tracking
	print("\nWORKFLOW PROGRESS TRACKING:")
	workflow.update_submission_status(2, 10)
	status = workflow.get_submission_status()
	print(f"  Current Step: {status['step']}/{status['total_steps']}")
	print(f"  Status: Identifying and documenting tribal leaders and organizations\n")

	print("=" * 70)
	print("DEMO COMPLETE")
	print("=" * 70)
	print("\nKEY TAKEAWAYS:")
	print("  [OK] SustainabilityAgent: 3-node LangGraph pipeline for full analysis")
	print("  [OK] IndigenousContextAgent: Thread-based conversation persistence")
	print("  [OK] ProposalWorkflowAgent: 10-step workflow with email generation")
	print("  [OK] All agents: Memory system (_prompt + _history)")
	print("  [OK] Ready for FastAPI integration and database persistence")
	
	# Verify image output if requested
	if output_images:
		print(f"\nIMAGE GENERATION TEST:")
		vision_path = os.path.join(image_dir, "future_vision.png")
		if os.path.exists(vision_path):
			size = os.path.getsize(vision_path)
			print(f"  [OK] Future vision image saved: {vision_path}")
			print(f"  [OK] File size: {size} bytes")
		else:
			print(f"  [X] Image not found at {vision_path}")


if __name__ == "__main__":
	# Parse command-line arguments
	output_images = "--save-images" in sys.argv or "-s" in sys.argv
	
	if output_images:
		image_dir = "output"
		# Check if custom directory specified
		for arg in sys.argv[1:]:
			if arg.startswith("--image-dir="):
				image_dir = arg.split("=")[1]
				break
		print(f"Image output enabled: {image_dir}/\n")
		demo_specialized_agents(output_images=True, image_dir=image_dir)
	else:
		demo_specialized_agents()
