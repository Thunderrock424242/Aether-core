import uvicorn
from aether_sidecar.app import app
from aether_sidecar.config import settings

if __name__ == "__main__":
    uvicorn.run(app, host=settings.host, port=settings.port)
