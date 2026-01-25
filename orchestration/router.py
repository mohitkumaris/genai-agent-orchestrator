from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import AzureChatOpenAI

from app.core.config import settings

class RouteDecision(BaseModel):
    destination: Literal["retrieval_agent", "general_agent", "planner"] = Field(..., description="The expert agent to route to.")
    reasoning: str = Field(..., description="Reason for the decision.")

class Router:
    """
    Decides which agent to invoke based on the query.
    """
    def __init__(self):
        self.llm = AzureChatOpenAI(
            azure_deployment=settings.azure_openai_deployment_name,
            openai_api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            temperature=0.0
        )
        self.parser = PydanticOutputParser(pydantic_object=RouteDecision)
        
    async def route(self, query: str) -> RouteDecision:
        template = """You are the Dispatcher for the GenAI Platform.
Select the best agent for the task.

Agents:
- retrieval_agent: External knowledge, document search, policy lookup.
- general_agent: Chat, greetings, simple logic.
- planner: Complex tasks requiring multi-step breakdown.

{format_instructions}

User Query: {query}
"""
        prompt = ChatPromptTemplate.from_messages([("human", template)])
        chain = prompt | self.llm | self.parser
        
        try:
            return await chain.ainvoke({
                "query": query,
                "format_instructions": self.parser.get_format_instructions()
            })
        except Exception as e:
            # Safe Fallback
            return RouteDecision(destination="general_agent", reasoning=f"Routing error: {e}")
