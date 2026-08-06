FROM python:3.11-slim AS builder

WORKDIR /app

# Instala dependências de sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala uv
RUN pip install uv

# Copia arquivos de configuração
COPY pyproject.toml setup.py README.md ./

# Copia o código fonte
COPY src/ src/

# Instala dependências
RUN uv venv && \
    uv pip install --no-cache .

# Final image
FROM python:3.11-slim

WORKDIR /app

# Instala libpq
RUN apt-get update && apt-get install -y \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia ambiente virtual
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/pyproject.toml /app/
COPY --from=builder /app/setup.py /app/

# Copia código fonte
COPY src/ src/
COPY migrations/ migrations/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

EXPOSE 8000

CMD ["uvicorn", "pressao_api.main:app", "--host", "0.0.0.0", "--port", "8000"]