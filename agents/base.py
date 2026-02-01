from abc import ABC, abstractmethod
from typing import List, Dict, Any
import yaml
from langchain_openai import AzureChatOpenAI

from app.core.config import settings
from schemas.request import ServiceRequest
from schemas.response import ServiceResponse

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.llm = AzureChatOpenAI(
            azure_deployment=settings.azure_openai_deployment_name,
            openai_api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            temperature=0.0
        )
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
