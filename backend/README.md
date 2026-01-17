# Backend Agents

This backend provides a simple class of AI agents for:
- Workflow planning (LangGraph with OpenAI/Gemini/Claude, fallback local)
- Image generation (OpenAI with local Pillow placeholder)

## Quick Start

1. Create and activate a venv:
```zsh
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:
```zsh
pip install -r requirements.txt
```

3. Run demo:
```zsh
python main.py
```
This runs in `local` mode by default and should generate `generated.png` without any API keys.

## Optional: Use OpenAI, Gemini, or Claude

Set environment variables and rerun:
```zsh
# OpenAI
export OPENAI_API_KEY="<your-key>"
export AGENT_PROVIDER="openai"
export LLM_MODEL="gpt-4o-mini"  # or another model

# Gemini
export GEMINI_API_KEY="<your-key>"
export AGENT_PROVIDER="gemini"
export LLM_MODEL="gemini-1.5-flash"

# Claude
export ANTHROPIC_API_KEY="<your-key>"
export AGENT_PROVIDER="claude"   # or "anthropic"
export LLM_MODEL="claude-3-5-sonnet-20240620"
```

Notes:
- Gemini and Claude here are used for text planning; image generation falls back to a local placeholder.
- OpenAI image generation uses `gpt-image-1`. If unavailable, it will fall back to local image.

## Extending
- Add more prompt variables like `self.prompt2`, `self.system_instructions`.
- Create additional agent classes for domain-specific tasks.
- Consider adding FastAPI endpoints to expose orchestrator methods.
