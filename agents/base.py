"""
Base Agent

Abstract base class for all agents. Does NOT create LLM instances.
Execution agents that need LLM should use llm/langchain_adapter.py.

DESIGN RULE: LangChain is encapsulated in the adapter only.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import yaml

from app.core.config import settings
from schemas.request import ServiceRequest
from schemas.response import ServiceResponse


class BaseAgent(ABC):
    """
    Abstract base for all agents.
    
    NOTE: Does NOT instantiate LLM. Execution agents that need LLM
    should import and use llm.langchain_adapter.generate() directly.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.prompt_config = self._load_prompt()
        
    def _load_prompt(self) -> str:
        # Load from YAML
        with open(f"{settings.prompts_dir}/agents.yaml", "r") as f:
            data = yaml.safe_load(f)
            return data.get(self.name, {}).get("system", "")

    @abstractmethod
    async def execute(self, request: ServiceRequest) -> ServiceResponse:
        """
        Execute agent with full request context.
        
        Args:
            request: Structured service request with query and context
            
        Returns:
            ServiceResponse: Structured response with answer and metadata
        """
        pass

    @abstractmethod
    def run(self, prompt: str) -> str:
        """
        Simple synchronous interface for agent execution.
        
        This is the minimal typed contract that all agents must implement.
        
        Args:
            prompt: The user's prompt/query
            
        Returns:
            str: The agent's response
        """
        pass
