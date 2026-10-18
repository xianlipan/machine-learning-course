import logging
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException as StarletteHTTPException

from .database import initialize, leaderboard, record, check_limit, SubmissionLimitReached
from .evaluator import MAX_BYTES, evaluate, load_labels

ROOT = Path(__file__).resolve().parent


def create_app(labels_path=None, db_path=None):
    labels_path = Path(labels_path or os.getenv('CHALLENGE_LABELS_PATH', str(ROOT / 'data' / '04_北京房价_测试集标签_教师保留.csv')))
    db_path = Path(db_path or os.getenv('CHALLENGE_DB_PATH', str(ROOT / 'leaderboard.db')))

    @asynccontextmanager
    async def lifespan(app):
        app.state.labels = None
        try:
            app.state.labels = load_labels(labels_path)
        except FileNotFoundError:
            logging.warning('教师尚未配置标签，服务已启动，评测暂未开放。')
        except (OSError, ValueError):
            raise RuntimeError('隐藏标签不可读取或格式错误，请教师检查服务器配置。') from None
        initialize(db_path)
        yield

    app = FastAPI(title='北京房价预测挑战', lifespan=lifespan)
    origins = os.getenv('CHALLENGE_ALLOWED_ORIGINS', 'https://xianlipan.github.io,http://127.0.0.1:8000,http://localhost:8000')
    app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in origins.split(',')],
                       allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])

    @app.exception_handler(StarletteHTTPException)
    async def request_error(request, error):
        detail = error.detail
        if error.status_code == 400 and (not isinstance(detail, str) or not any('\u4e00' <= c <= '\u9fff' for c in detail)):
            detail = '上传表单格式错误，请重新选择 CSV 文件后提交。'
        return JSONResponse({'detail': detail}, status_code=error.status_code, headers=error.headers)

    # Bound the entire multipart stream, including requests without Content-Length.
    @app.middleware('http')
    async def limit_body(request: Request, call_next):
        if request.method == 'POST':
            size = 0
            body = bytearray()
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_BYTES + 64 * 1024:
                    return JSONResponse({'detail': '上传请求过大，CSV 文件不能超过 10 MB。'}, status_code=413)
                # Keep a bounded body for multipart parsing.
                body.extend(chunk)
            request._body = bytes(body)
        return await call_next(request)

    @app.exception_handler(Exception)
    async def unexpected_error(request, error):
        logging.error('Challenge request failed: %s', type(error).__name__)
        return JSONResponse({'detail': '服务器暂时无法完成评测，请稍后重试。'}, status_code=500)

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'evaluation_ready': app.state.labels is not None}

    @app.get('/api/leaderboard')
    def get_leaderboard():
        return {'leaderboard': leaderboard(db_path)}

    @app.post('/api/evaluate')
    async def submit(request: Request):
        if app.state.labels is None:
            raise HTTPException(503, '教师尚未配置测试标签，评测暂未开放，请稍后再试。')
        if not request.headers.get('content-type', '').startswith('multipart/form-data'):
            raise HTTPException(415, '请使用表单上传 submission.csv。')
        try:
            async with request.form(max_files=1, max_fields=2, max_part_size=4096) as form:
                if set(form.keys()) != {'name', 'student_id', 'file'} or any(len(form.getlist(k)) != 1 for k in form):
                    raise ValueError('请提供姓名、学号和一个 CSV 文件。')
                name, student_id, file = form['name'], form['student_id'], form['file']
                if not isinstance(name, str) or not 1 <= len(name.strip()) <= 60 or any(ord(c) < 32 for c in name):
                    raise ValueError('请填写有效姓名（1–60 字）。')
                if not isinstance(student_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', student_id.strip()):
                    raise ValueError('学号须为 1–64 位字母、数字、下划线或短横线。')
                if not isinstance(file, UploadFile) or not (file.filename or '').lower().endswith('.csv'):
                    raise ValueError('只能上传 CSV 文件。')
                await run_in_threadpool(check_limit, db_path, student_id.strip(), name.strip())
                content = await file.read(MAX_BYTES + 1)
                if len(content) > MAX_BYTES:
                    raise HTTPException(413, '文件不能超过 10 MB。')
                rmse = await run_in_threadpool(evaluate, content, app.state.labels)
                result = await run_in_threadpool(record, db_path, student_id.strip(), name.strip(), rmse)
                return {'success': True, 'name': name.strip(), 'student_id': student_id.strip(), 'rmse': rmse, **result}
        except SubmissionLimitReached as error:
            raise HTTPException(429, str(error)) from None
        except ValueError as error:
            raise HTTPException(400, str(error)) from None

    return app


app = create_app()
