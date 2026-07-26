from fastapi import FastAPI, Request
from uuid import uuid4
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import admin, approvals, auth, costs, crm, dashboard, finance, inventory, operations, order_flow, production, purchasing, sales, support, tasks
from app.core.config import settings
from app.services import ip_ctx, request_id_ctx

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


@app.middleware("http")
async def request_audit_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    token_id = request_id_ctx.set(request_id)
    token_ip = ip_ctx.set(request.client.host if request.client else None)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        request_id_ctx.reset(token_id)
        ip_ctx.reset(token_ip)

for router in [auth.router, dashboard.router, sales.router, crm.router, order_flow.router, production.router, approvals.router, costs.router, operations.router, inventory.router, purchasing.router, finance.router, support.router, tasks.router, admin.router]:
    app.include_router(router)


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": settings.app_name, "environment": settings.environment}
