from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tutor.api.auth_routes import router as auth_router
from tutor.api.doubt_routes import router as doubt_router
from tutor.api.evaluation_routes import router as evaluation_router
from tutor.api.learner_routes import router as learner_router
from tutor.api.path_routes import router as path_router
from tutor.api.reward_routes import router as reward_router
from tutor.api.revision_routes import router as revision_router
from tutor.api.schemas import api_response
from tutor.api.tutor_routes import router as tutor_router
from tutor.api.xai_routes import router as xai_router
from tutor.api.integration_routes import router as integration_router


app = FastAPI(
    title="Cognition-Adaptive AI Tutor API",
    version="0.2.0",
    description="Thin FastAPI wrappers around the evaluated Cognition-Adaptive AI Tutor backend services.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return api_response(module="TutorAPI", data={"api_ready": True})


app.include_router(auth_router)
app.include_router(learner_router)
app.include_router(tutor_router)
app.include_router(evaluation_router)
app.include_router(doubt_router)
app.include_router(revision_router)
app.include_router(reward_router)
app.include_router(xai_router)
app.include_router(path_router)
app.include_router(integration_router)
