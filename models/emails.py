from pydantic import BaseModel, Field

class EmailTemplateParams(BaseModel):
    articles: list[dict]
    keywords: list[str]
    threshold: float = Field(default=0.5, ge=0, le=1)  