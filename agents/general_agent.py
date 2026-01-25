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
