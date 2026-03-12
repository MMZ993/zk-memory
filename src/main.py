from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="AI Agent Memory System",
    description="A long-term memory system for AI agents inspired by Zettelkasten",
    version="1.0.0",
)


class HealthResponse(BaseModel):
    status: str
    message: str


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AI Agent Memory System API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy", message="System is running - implementation in progress"
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
