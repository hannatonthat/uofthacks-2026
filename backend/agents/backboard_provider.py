"""Thin wrapper around Backboard.io REST for assistants, threads, and chat."""

import os
import requests
from typing import Optional, Tuple


class BackboardProvider:
	"""Create assistants, threads, and chats via Backboard REST."""

	def __init__(self):
		"""Load API key and base URL for Backboard REST calls."""
		# Load API key from environment
		self.api_key = os.getenv("BACKBOARD_API_KEY")
		
		# Backboard.io REST API base URL
		self.base_url = "https://app.backboard.io/api"
		
		# Headers with authentication
		self.headers = {"X-API-Key": self.api_key}

		# Fail fast if API key not configured
		if not self.api_key:
			raise ValueError(
				"BACKBOARD_API_KEY not set in environment. "
				"Add BACKBOARD_API_KEY=your_key to .env file or environment variables."
			)

	def create_assistant(
		self, name: str, system_prompt: str, model: str = "gpt-4o-mini"
	) -> str:
		"""Create an assistant with the given model and system prompt."""
		try:
			# Make POST request to create assistant
			response = requests.post(
				f"{self.base_url}/assistants",
				json={
					"name": name,
					"system_prompt": system_prompt,
					"model": model
				},
				headers=self.headers,
			)
			
			# Raise error if HTTP request failed
			response.raise_for_status()
			
			# Extract and return assistant_id
			return response.json()["assistant_id"]
		except Exception as e:
			raise RuntimeError(f"Failed to create Backboard assistant: {e}")

	def create_thread(self, assistant_id: str) -> str:
		"""Start a new conversation thread for an assistant."""
		try:
			# Make POST request to create thread
			response = requests.post(
				f"{self.base_url}/assistants/{assistant_id}/threads",
				json={},  # Empty body, just creates empty thread
				headers=self.headers,
			)
			
			# Raise error if HTTP request failed
			response.raise_for_status()
			
			# Extract and return thread_id
			return response.json()["thread_id"]
		except Exception as e:
			raise RuntimeError(f"Failed to create Backboard thread: {e}")

	def chat(
		self, assistant_id: str, message: str, thread_id: Optional[str] = None
	) -> Tuple[str, str]:
		"""Send a message, auto-create thread if needed, and return response with thread id."""
		# Create thread if not provided (first message of conversation)
		if not thread_id:
			thread_id = self.create_thread(assistant_id)

		try:
			# Make POST request to send message using multipart/form-data (as per API docs)
			# https://app.backboard.io/api/docs#/Threads/post_threads__thread_id__messages
			data = {
				"content": message,
				"stream": "false",  # Don't stream responses
				"memory": "Auto",   # Enable automatic memory search and write
				"send_to_llm": "true",  # Send to LLM for response
			}
			
			response = requests.post(
				f"{self.base_url}/threads/{thread_id}/messages",
				headers=self.headers,
				data=data,  # Use data (form-encoded) not json
			)
			
			# Raise error if HTTP request failed
			response.raise_for_status()
			
			# Extract response content from the response message
			response_json = response.json()
			content = response_json.get("content", "")
			
			# Return response and thread_id for continuation
			return content, thread_id
		except Exception as e:
			raise RuntimeError(f"Failed to send Backboard message: {e}")
