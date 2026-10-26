# Imagem de produção (Render ou qualquer host com Docker).
FROM python:3.12-slim

# Pango: necessário para o WeasyPrint gerar PDF.
# fonts-liberation: equivalente métrico ao Arial usado nos estilos.
# Tesseract (com português): OCR de reserva para PDFs escaneados.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 \
        fonts-liberation fonts-dejavu-core \
        tesseract-ocr tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/

# Os módulos usam imports simples: o servidor roda de dentro de backend/.
WORKDIR /app/backend
# O Render define a porta em $PORT.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
