"""Integração com o Google Gemini (SDK google-genai)."""

import os
import time

import httpx
from google import genai
from google.genai import errors, types

from extractor import Extracted, ExtractionError, ocr_fallback
from prompts import UNREADABLE_MARKER, build_prompt

DEFAULT_MODEL = "gemini-3.8-flash"

# Espera (s) após cada tentativa; o último valor não é usado (última tentativa).
RETRY_DELAYS = (1, 3, 0)

# Tempo máximo de cada chamada ao Gemini. Sem isso, uma conexão travada deixa o
# usuário esperando para sempre. Respostas normais já levaram até ~40 s.
GEMINI_TIMEOUT_MS = 60_000


class AIError(Exception):
    """Erro com mensagem amigável para o usuário."""


_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise AIError("Servidor sem chave da IA configurada (GEMINI_API_KEY).")
        _client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS)
        )
    return _client


def translate(item: Extracted, mode: str) -> str:
    prompt = build_prompt(mode)
    if not item.is_binary:
        return _generate([prompt, item.text])

    try:
        part = types.Part.from_bytes(data=item.data, mime_type=item.mime_type)
        return _generate([prompt, part])
    except AIError:
        raise
    except errors.ClientError:
        # O Gemini rejeitou o PDF escaneado: tenta OCR local.
        try:
            text = ocr_fallback(item)
        except ExtractionError as exc:
            raise AIError(str(exc)) from exc
        return _generate([prompt, text])


def _call_with_retry(client: genai.Client, model: str, contents):
    """Repete em sobrecarga temporária (5xx/429), respeitando a meta de < 15 s."""
    for attempt, delay in enumerate(RETRY_DELAYS):
        try:
            return client.models.generate_content(model=model, contents=contents)
        except errors.APIError as exc:
            transient = isinstance(exc, errors.ServerError) or exc.code == 429
            if not transient or attempt == len(RETRY_DELAYS) - 1:
                raise
            time.sleep(delay)


def _generate(contents) -> str:
    model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
    client = _get_client()
    try:
        response = _call_with_retry(client, model, contents)
    except errors.ServerError as exc:
        raise AIError(
            "O serviço de inteligência artificial está indisponível. Tente novamente em instantes."
        ) from exc
    except errors.ClientError as exc:
        if exc.code in (401, 403):
            raise AIError("Chave da IA inválida. Verifique a GEMINI_API_KEY.") from exc
        if exc.code == 404:
            raise AIError("Modelo da IA não encontrado. Verifique a GEMINI_MODEL.") from exc
        if exc.code == 429:
            raise AIError("Limite de uso da IA atingido. Aguarde um pouco e tente novamente.") from exc
        raise
    except httpx.TimeoutException as exc:
        raise AIError(
            "O serviço de inteligência artificial demorou demais para responder. "
            "Tente novamente em instantes."
        ) from exc
    except Exception as exc:
        raise AIError(
            "Não foi possível conectar ao serviço de inteligência artificial."
        ) from exc

    text = (response.text or "").strip()
    if not text or UNREADABLE_MARKER in text:
        raise AIError(
            "Não conseguimos ler a receita. Tente enviar outra versão do documento, mais nítida."
        )
    return text
