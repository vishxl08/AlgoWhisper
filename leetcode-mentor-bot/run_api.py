"""Run FastAPI server."""

from api.main import app
from config import get_settings

if __name__ == "__main__":
    import uvicorn

    s = get_settings()
    uvicorn.run(app, host=s.api_host, port=s.api_port)
