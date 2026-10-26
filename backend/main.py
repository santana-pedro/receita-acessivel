"""Receita Acessível — API FastAPI e servidor do frontend.

Stateless: nenhuma receita é gravada; tudo é processado em memória.
"""

import base64
import logging
import os
import secrets
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")

import ai  # noqa: E402  (depende do .env carregado)
from exporter import ExportError, export  # noqa: E402
from extractor import ExtractionError, extract, from_typed_text  # noqa: E402

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024

Mode = Literal["visual", "illiterate"]

logger = logging.getLogger("receita")

app = FastAPI(title="Receita Acessível")

# CORS liberado para desenvolvimento local.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Senha opcional (HTTP Basic): definida em produção para a cota do Gemini não ficar
# aberta a qualquer um com o link. Qualquer usuário serve; só a senha é conferida.
APP_PASSWORD = os.getenv("APP_PASSWORD", "")


@app.middleware("http")
async def require_password(request: Request, call_next):
    if not APP_PASSWORD or request.url.path == "/health":
        return await call_next(request)
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("basic "):
        try:
            _, _, password = base64.b64decode(auth[6:]).decode("utf-8").partition(":")
        except (ValueError, UnicodeDecodeError):
            password = ""
        if secrets.compare_digest(password.encode(), APP_PASSWORD.encode()):
            return await call_next(request)
    return Response(
        "Senha necessária.",
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="Receita Acessivel", charset="UTF-8"'},
    )


class DownloadRequest(BaseModel):
    text: str = Field(min_length=1)
    mode: Mode
    format: Literal["pdf", "docx", "txt"]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/translate")
async def translate(
    mode: Mode = Form(...),
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
):
    """Recebe a receita como arquivo ou como texto digitado (exatamente um dos dois)."""
    if (file is None) == (text is None):
        raise HTTPException(422, "Envie um arquivo ou digite a receita.")

    try:
        if file is not None:
            content = await file.read(MAX_FILE_SIZE + 1)
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(413, f"O arquivo é maior que {MAX_FILE_SIZE_MB} MB.")
            item = await run_in_threadpool(extract, file.filename, content)
        else:
            item = from_typed_text(text)
        translated = await run_in_threadpool(ai.translate, item, mode)
    except (ExtractionError, ai.AIError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        # Não registrar o conteúdo da receita: apenas o tipo do erro.
        logger.error("Falha inesperada na tradução: %s", type(exc).__name__)
        raise HTTPException(
            500, "Ocorreu um erro ao processar a receita. Tente novamente."
        ) from exc

    return {"translated_text": translated, "mode": mode}


@app.post("/api/download")
async def download(req: DownloadRequest):
    try:
        data, media_type, filename = await run_in_threadpool(
            export, req.text, req.mode, req.format
        )
    except ExportError as exc:
        raise HTTPException(503, str(exc)) from exc
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# Montado por último para não sombrear as rotas da API.
app.mount("/", StaticFiles(directory=BASE_DIR.parent / "frontend", html=True), name="frontend")
