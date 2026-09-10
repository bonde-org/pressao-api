.PHONY: help setup install dev test test-cov lint format migrate docker-build docker-up docker-down clean load-test-seed load-test load-test-report

# Variáveis
VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
UV = uv

help:
	@echo "Comandos disponíveis:"
	@echo "  setup        Cria ambiente virtual e instala dependências"
	@echo "  install      Instala dependências no ambiente virtual existente"
	@echo "  dev          Roda em modo desenvolvimento"
	@echo "  test         Roda testes"
	@echo "  test-cov     Roda testes com cobertura"
	@echo "  lint         Roda linting"
	@echo "  format       Formata código"
	@echo "  migrate      Roda migrações"
	@echo "  docker-build Build da imagem docker"
	@echo "  docker-up    Sobe containers docker"
	@echo "  docker-down  Para containers docker"
	@echo "  load-test-seed  Prepara campanha/alvos para testes k6"
	@echo "  load-test       Executa teste de carga (SCENARIO=load|smoke|stress|spike)"
	@echo "  load-test-report Gera Markdown parcial a partir do último resultado k6"
	@echo "  clean        Limpa arquivos temporários e cache"

setup:
	@echo "🐍 Criando ambiente virtual..."
	$(UV) venv
	@echo "📦 Instalando dependências..."
	$(UV) pip install -e .
	$(UV) pip install -e ".[dev]"
	@echo "✅ Setup completo!"
	@echo "👉 Para ativar o ambiente virtual: source $(VENV)/bin/activate"

install: $(VENV)
	@echo "📦 Instalando dependências..."
	$(UV) pip install -e .
	$(UV) pip install -e ".[dev]"
	@echo "✅ Dependências instaladas!"

$(VENV):
	@echo "🐍 Criando ambiente virtual..."
	$(UV) venv
	@echo "✅ Ambiente virtual criado!"

dev: $(VENV)
	@echo "🚀 Iniciando servidor de desenvolvimento..."
	PYTHONPATH=$(PWD)/src $(PYTHON) -m uvicorn pressao_api.main:app --reload --host 0.0.0.0 --port 8000

test: $(VENV)
	@echo "🧪 Executando testes..."
	$(PYTHON) -m pytest

test-cov: $(VENV)
	@echo "📊 Executando testes com cobertura..."
	$(PYTHON) -m pytest --cov=pressao_api --cov-report=html --cov-report=term

lint: $(VENV)
	@echo "🔍 Executando linting..."
	$(PYTHON) -m ruff check .
	$(PYTHON) -m mypy src

format: $(VENV)
	@echo "🎨 Formatando código..."
	$(PYTHON) -m black .
	$(PYTHON) -m ruff --fix .

migrate: $(VENV)
	@echo "📋 Executando migrações..."
	PYTHONPATH=$(PWD)/src $(PYTHON) -m alembic upgrade head

docker-build:
	@echo "🐳 Build da imagem Docker..."
	docker compose -f docker/docker-compose.yml build

docker-up:
	@echo "🐳 Subindo containers..."
	docker compose -f docker/docker-compose.yml up -d
	@echo "✅ Containers em execução!"
	@echo "📊 Swagger: http://localhost:8000/api/docs"
	@echo "📊 Keycloak: http://localhost:8080 (admin/admin123)"
	@echo "📊 Grafana: http://localhost:3000 (admin/admin)"
	@echo "📊 Prometheus: http://localhost:9090"

docker-down:
	@echo "🐳 Parando containers..."
	docker compose -f docker/docker-compose.yml down
	@echo "✅ Containers parados!"

docker-logs:
	@echo "📋 Logs dos containers..."
	docker compose -f docker/docker-compose.yml logs -f

load-test-seed:
	@./scripts/load-test-seed.sh

load-test:
	@SCENARIO="$(SCENARIO)" VUS="$(VUS)" DURATION="$(DURATION)" RPS="$(RPS)" \
		SKIP_THRESHOLDS="$(SKIP_THRESHOLDS)" \
		BASE_URL="$(BASE_URL)" KEYCLOAK_URL="$(KEYCLOAK_URL)" \
		KEYCLOAK_REALM="$(KEYCLOAK_REALM)" KEYCLOAK_CLIENT_ID="$(KEYCLOAK_CLIENT_ID)" \
		KEYCLOAK_CLIENT_SECRET="$(KEYCLOAK_CLIENT_SECRET)" \
		./scripts/run-load-test.sh

load-test-report:
	@RESULT_DIR="$(RESULT_DIR)" OUTPUT_FILE="$(OUTPUT_FILE)" ./scripts/generate-load-test-report.sh

clean:
	@echo "🧹 Limpando arquivos temporários..."
	rm -rf __pycache__
	rm -rf */__pycache__
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✅ Limpeza concluída!"

clean-all: clean
	@echo "🧹 Removendo ambiente virtual..."
	rm -rf $(VENV)
	@echo "✅ Limpeza completa!"