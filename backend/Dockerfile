# Stage 1: Builder
FROM python:3.10-slim AS builder

WORKDIR /app

# Bağımlılıkları önce kopyala
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.10-slim AS runtime

# Non-root user oluştur
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Builder'dan sadece yüklenen paketleri al
COPY --from=builder /root/.local /home/appuser/.local

# Uygulama kodunu kopyala
COPY main.py .

# Sahipliği appuser'a ver
RUN chown -R appuser:appuser /app

USER appuser

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]