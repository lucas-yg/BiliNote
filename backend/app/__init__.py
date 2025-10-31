from fastapi import FastAPI

from .routers import note, provider, model, config



def create_app(lifespan) -> FastAPI:
    app = FastAPI(title="BiliNote",lifespan=lifespan)
    app.include_router(note.router, prefix="/api")
    app.include_router(provider.router, prefix="/api")
    app.include_router(model.router,prefix="/api")
    app.include_router(config.router,  prefix="/api")
    # app.include_router(scheduled_tasks.router, prefix="/api")  # 暂时注释

    # 添加健康检查端点
    @app.get("/health")
    @app.get("/api/health")
    async def health_check():
        return {"status": "healthy", "service": "bilinote-backend"}

    return app
