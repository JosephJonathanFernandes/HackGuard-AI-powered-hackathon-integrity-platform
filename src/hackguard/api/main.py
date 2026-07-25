from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from hackguard.api.routes import analysis
from config.settings import settings

def create_app() -> FastAPI:
    app = FastAPI(
        title="HackGuard API",
        description="Hackathon repository risk scoring engine.",
        version="1.0.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(analysis.router, tags=["analysis"])

    @app.get("/health", tags=["system"])
    def health():
        return {"status": "ok"}

    return app

app = create_app()
