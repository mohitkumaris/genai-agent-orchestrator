"""
Retrieval Tool

MCP-style retrieval tool for RAG.
Returns structured documents, not user-facing strings.

DESIGN RULES:
- No hardcoded vector DB (mock for now)
- Returns structured output with documents
- Retrieval is a tool detail, not orchestration logic
"""

from typing import Any, Dict, List
from mcp.tools.base import Tool, ToolResult


class RetrievalTool(Tool):
    """
    Document retrieval tool for RAG.
    
    Searches a document store and returns relevant chunks.
    Currently uses mock data - production would connect to vector DB.
    """
    
    @property
    def name(self) -> str:
        return "retrieval"
    
    @property
    def description(self) -> str:
        return "Search and retrieve relevant documents for a query. Returns top-k most relevant document chunks."
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to find relevant documents",
                },
                "k": {
                    "type": "integer",
                    "description": "Number of documents to retrieve (default: 3)",
                    "default": 3,
                },
            },
            "required": ["query"],
        }
    
    def run(self, input: Dict[str, Any]) -> ToolResult:
        """
        Execute document retrieval.
        
        Args:
            input: {"query": "...", "k": 3}
            
        Returns:
            ToolResult with {"documents": [{"id": "...", "content": "...", "score": 0.82}]}
        """
        query = input.get("query", "")
        k = input.get("k", 3)
        
        if not query:
            return ToolResult.fail("Missing 'query' in input")
        
        # Mock retrieval - production would call vector DB
        documents = self._mock_retrieve(query, k)
        
        return ToolResult.ok({
            "documents": documents,
            "query": query,
            "total_retrieved": len(documents),
        })
    
    def _mock_retrieve(self, query: str, k: int) -> List[Dict[str, Any]]:
        """
        Mock document retrieval.
        
        In production, this would:
        1. Embed the query
        2. Search vector DB
        3. Return top-k results
        """
        # Mock knowledge base with some sample documents
        mock_docs = [
            {
                "id": "doc_001",
                "content": "Python is a high-level, interpreted programming language known for its simplicity and readability.",
                "source": "programming_guide.md",
                "score": 0.92,
            },
            {
                "id": "doc_002", 
                "content": "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
                "source": "ai_fundamentals.md",
                "score": 0.88,
            },
            {
                "id": "doc_003",
                "content": "FastAPI is a modern, fast web framework for building APIs with Python based on standard type hints.",
                "source": "web_frameworks.md",
                "score": 0.85,
            },
            {
                "id": "doc_004",
                "content": "Vector databases store embeddings and enable semantic search over unstructured data.",
                "source": "databases.md",
                "score": 0.82,
            },
            {
                "id": "doc_005",
                "content": "LangChain is a framework for developing applications powered by language models.",
                "source": "llm_tools.md",
                "score": 0.79,
            },
        ]
        
        # Simple keyword matching for demo (production uses embeddings)
        query_lower = query.lower()
        scored_docs = []
        
        for doc in mock_docs:
            content_lower = doc["content"].lower()
            # Boost score if query terms appear in content
            if any(term in content_lower for term in query_lower.split()):
                scored_docs.append({**doc, "score": min(0.95, doc["score"] + 0.05)})
            else:
                scored_docs.append(doc)
        
        # Sort by score and return top-k
        scored_docs.sort(key=lambda x: x["score"], reverse=True)
        return scored_docs[:k]
