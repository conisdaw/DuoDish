import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import UPLOAD_DIR
from app.database import init_db

os.makedirs(UPLOAD_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="DuoDish",
    description="情侣点餐互动后端 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

TEMP_DIR = "temp"
if os.path.exists(TEMP_DIR):
    app.mount("/temp", StaticFiles(directory=TEMP_DIR), name="temp")


# ─── 统一响应格式的异常处理 ───

@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "data": None, "message": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"code": 422, "data": None, "message": f"参数校验失败: {exc.errors()}"},
    )


@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"code": 500, "data": None, "message": f"服务器内部错误: {str(exc)}"},
    )


# ─── 注册路由 ───

from app.api import auth, users, anniversaries, orders, achievements, love_bank, games, diary, extras, upload, private_kitchen  # noqa: E402

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(upload.router)
app.include_router(anniversaries.router)
app.include_router(orders.router)
app.include_router(achievements.router)
app.include_router(love_bank.router)
app.include_router(games.router)
app.include_router(diary.router)
app.include_router(extras.router)
app.include_router(private_kitchen.router)
