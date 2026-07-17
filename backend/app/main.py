from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import admin, approvals, auth, costs, crm, dashboard, finance, inventory, operations, purchasing, sales, support, tasks
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in [auth.router, dashboard.router, sales.router, crm.router, approvals.router, costs.router, operations.router, inventory.router, purchasing.router, finance.router, support.router, tasks.router, admin.router]:
    app.include_router(router)


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": settings.app_name, "environment": settings.environment}
