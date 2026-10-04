from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

class Source(BaseModel):
    document_id: str
    filename: str
    page: int | None = None
    passage: str
    relevance: float

class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    insufficient_context: bool
