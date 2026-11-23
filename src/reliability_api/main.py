from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from .config import settings
from .db import Base, engine, get_db
from .dependencies import require_api_key
from .routers import rules, analyses, approvals, curves, audit
from . import models  # noqa: F401 - register ORM metadata

def create_app(database_engine=None, create_tables: bool=False):
    app=FastAPI(title=settings.service_name,version=settings.service_version,description="Reliability TRI API: rule lifecycle, deterministic analysis and audit contracts",openapi_url="/openapi.json")
    if create_tables:
        Base.metadata.create_all(bind=database_engine or engine)
    if database_engine is not None:
        from sqlalchemy.orm import sessionmaker
        TestingSession=sessionmaker(bind=database_engine,autoflush=False,expire_on_commit=False)
        def override_db():
            db=TestingSession()
            try: yield db
            finally: db.close()
        app.dependency_overrides[get_db]=override_db
    app.include_router(rules.router,dependencies=[Depends(require_api_key)])
    app.include_router(analyses.router,dependencies=[Depends(require_api_key)])
    app.include_router(approvals.router,dependencies=[Depends(require_api_key)])
    app.include_router(curves.router,dependencies=[Depends(require_api_key)])
    app.include_router(audit.router,dependencies=[Depends(require_api_key)])
    @app.get("/health",tags=["system"])
    def health(): return {"status":"ok","service":settings.service_name,"version":settings.service_version}
    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        return JSONResponse(status_code=500,content={"error_code":"INTERNAL_ERROR","message":"Unexpected server error"})
    return app

app=create_app()
