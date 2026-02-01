from langchain_core.prompts import ChatPromptTemplate

from agents.base import BaseAgent
from schemas.request import ServiceRequest
from schemas.response import ServiceResponse

class GeneralAgent(BaseAgent):
    def __init__(self):
        super().__init__("general_agent")
    
    async def execute(self, request: ServiceRequest) -> ServiceResponse:
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.prompt_config),
            ("user", "{input}")
        ])
        chain = prompt | self.llm
        res = await chain.ainvoke({"input": request.query})
        return ServiceResponse(answer=res.content) # type: ignore

    def run(self, prompt: str) -> str:
        """
        Simple synchronous interface for agent execution.
        
        Delegates to the underlying LLM chain with the configured prompt.
        """
        chat_prompt = ChatPromptTemplate.from_messages([
            ("system", self.prompt_config),
            ("user", "{input}")
        ])
        chain = chat_prompt | self.llm
        result = chain.invoke({"input": prompt})
        return result.content  # type: ignore
