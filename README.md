# 🚀 Pressão API - Orquestrador Multicanal de Ações de Pressão

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-24.0+-blue.svg)](https://www.docker.com/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

API para orquestração de ações de pressão multicanal, suportando canais automáticos (e-mail, telefone) e manuais (WhatsApp, Instagram) com rastreabilidade imutável e métricas de qualidade.

## 📋 Índice

- [Visão Geral](#🎯-visão-geral)
- [Arquitetura](#️🏗️-arquitetura)
- [Funcionalidades](#✨-funcionalidades)
- [Tecnologias](#️🛠️-tecnologias)
- [Pré-requisitos](#📦-pré-requisitos)
- [Instalação Rápida](#🚀-instalação-rápida)
- [Configuração](#️⚙️-configuração)
- [Endpoints da API](#📡-endpoints-da-api)
- [Fluxo de Trabalho](#🔄-fluxo-de-trabalho)
- [Testes](#🧪-testes)
- [Monitoramento](#📊-monitoramento)
- [Deploy](#🐳-deploy)
- [Contribuição](#🤝-contribuição)
- [Licença](#📝-licença)
- [Recursos Adicionais](#📚-recursos-adicionais)

## 🎯 Visão Geral

O sistema é um orquestrador de ações de pressão que gerencia múltiplos canais de comunicação:

- **Automáticos (API):** E-mail (SendGrid) e Telefone (Twilio) - disparo imediato com resposta via webhook
- **Manuais (Interação Humana):** WhatsApp e Instagram - geração de link/texto com confirmação manual

Cada ação é registrada de forma imutável e rastreável, garantindo auditoria completa e métricas de qualidade baseadas no tempo de resposta.

## 🏗️ Arquitetura

```text
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                       │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTPS + JWT
                      ▼
┌────────────────────────────────────────────────────────────┐
│                    FastAPI (Backend)                       │
│  ┌──────────────┬──────────────┬───────────────────────┐   │
│  │  Endpoints   │  Services    │    Repositories       │   │
│  │  - /acoes    │  - Orquestrador │  - AcaoRepository  │   │
│  │  - /status   │  - Canais    │    - Campanha         │   │
│  │  - /confirmar│  - Metricas  │    - Alvo             │   │
│  └──────────────┴──────────────┴───────────────────────┘   │
└─────────┬────────────────┬─────────────────┬───────────────┘
          │                │                 │
          ▼                ▼                 ▼
┌─────────────────┐ ┌──────────────┐ ┌──────────────────┐
│   PostgreSQL    │ │   Keycloak   │ │   Providers      │
│   (Dados)       │ │   (SSO)      │ │   - SendGrid     │
│                 │ │              │ │   - Twilio       │
└─────────────────┘ └──────────────┘ └──────────────────┘
          │                │                 │
          ▼                ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    Monitoramento                            │
│  ┌──────────────┬──────────────┬───────────────────────┐    │
│  │  Prometheus  │   Grafana    │    Structured Logs    │    │
│  └──────────────┴──────────────┴───────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## ✨ Funcionalidades

### Core

- ✅ Registro Imutável: Cada ação é registrada com timestamp e não pode ser alterada
- ✅ Multi-canal: Suporte a e-mail, telefone, WhatsApp e Instagram
- ✅ Dual Mode: Execução síncrona (API) e assíncrona (manual)
- ✅ Métricas de Qualidade: Classificação automática da qualidade da ação
- ✅ Rastreabilidade Completa: Histórico completo de cada ação

### Segurança

- 🔐 SSO com Keycloak: Autenticação via JWT com Keycloak
- 🔐 RBAC: Controle de acesso baseado em papéis (admin/ativista)
- 🔐 Validação de Permissões: Ativistas só veem suas próprias ações

### Monitoramento

- 📊 Métricas Prometheus: Coleta automática de métricas
- 📊 Grafana: Dashboards pré-configurados
- 📊 Logs Estruturados: Logs em JSON para fácil análise
- 📊 Health Checks: Endpoints de saúde da aplicação

## 🛠️ Tecnologias

### Backend

- Python 3.11+ - Linguagem principal
- FastAPI - Framework web assíncrono
- SQLAlchemy 2.0 - ORM assíncrono
- Alembic - Migrações de banco de dados
- Pydantic - Validação de dados
- UV - Gerenciador de pacotes rápido

### Infraestrutura

- PostgreSQL 15+ - Banco de dados principal
- Keycloak - SSO e gerenciamento de identidade
- Docker & Docker Compose - Containerização
- Prometheus - Coleta de métricas
- Grafana - Visualização de métricas

### Qualidade

- Pytest - Framework de testes
- Black - Formatação de código
- Ruff - Linting rápido
- Mypy - Type checking estático

## 📦 Pré-requisitos

- Python 3.11 ou superior
- PostgreSQL 15 ou superior
- Docker e Docker Compose (opcional)
- Git
- Make (opcional, para comandos facilitados)

## 🚀 Instalação Rápida

### Com Docker (Recomendado)

```bash
# Clone o repositório
git clone https://github.com/bonde-org/pressao-api.git
cd pressao-api

# Configure as variáveis de ambiente
cp .env.example .env

# Suba todos os serviços
make docker-up

# Acesse a API
# Swagger: http://localhost:8000/api/docs
# Health: http://localhost:8000/api/health
# Keycloak Admin: http://localhost:8080 (admin/admin123)
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
```

### Sem Docker (Desenvolvimento)

```bash
# Clone o repositório
git clone https://github.com/bonde-org/pressao-api.git
cd pressao-api

# Configure as variáveis de ambiente
cp .env.example .env

# Setup inicial (cria ambiente virtual e instala dependências)
make setup

# Ative o ambiente virtual (necessário apenas uma vez por sessão)
source .venv/bin/activate

# Rode as migrações do banco de dados
make migrate

# Inicie o servidor em modo desenvolvimento
make dev
```

### Comandos Úteis para Desenvolvimento

```bash
# Ver todos os comandos disponíveis
make help

# Instalar/atualizar dependências (se já tiver venv)
make install

# Executar testes
make test

# Executar testes com cobertura
make test-cov

# Rodar linters (ruff + mypy)
make lint

# Formatar código automaticamente
make format

# Limpar arquivos temporários
make clean

# Limpar tudo (incluindo venv)
make clean-all

# Ver logs dos containers Docker
make docker-logs

# Parar containers Docker
make docker-down
```

## ⚙️ Configuração

### Variáveis de Ambiente

| Variável | Descrição | Exemplo |
|----|----|----|
| `APP_ENV` | Ambiente da aplicação | `development` / `production` |
| `SECRET_KEY` | Chave secreta para JWT | `sua-chave-secreta-aqui` |
| `DATABASE_URL` | URL de conexão PostgreSQL | `postgresql://user:pass@localhost:5432/pressao` |
| `KEYCLOAK_URL` | 	URL do Keycloak | `http://localhost:8080` |
| `KEYCLOAK_REALM` | Realm do Keycloak | `pressao` |
| `KEYCLOAK_CLIENT_ID` | Client ID do Keycloak | `pressao-api` |
| `KEYCLOAK_CLIENT_SECRET` | Client Secret do Keycloak | `seu-secret` |
| `SENDGRID_API_KEY` | API Key do SendGrid | `SG.xxxxx` |
| `TWILIO_ACCOUNT_SID` | SID da conta Twilio | `ACxxxxx` |
| `TWILIO_AUTH_TOKEN` | Token de autenticação Twilio | `xxxxx` |
| `LOG_LEVEL` | Nível de log | `INFO` / `DEBUG` |

### Configuração do Keycloak

1. Acesse o Keycloak em http://localhost:8080
2. Faça login com admin/admin123
3. Crie um Realm chamado pressao
4. Crie um Client chamado pressao-api
5. Configure:
    - Access Type: bearer-only
    - Service Accounts Enabled: On
6. Crie usuários e atribua roles (admin, ativista)

## 📡 Endpoints da API

### Swagger Documentation

- Documentação Interativa: `http://localhost:8000/api/docs`
- Documentação ReDoc: `http://localhost:8000/api/redoc`

### Endpoints Principais

**Criar Nova Ação**

```http
POST /api/v1/acoes/
Authorization: Bearer {token_jwt}
Content-Type: application/json

{
    "campanha_id": "550e8400-e29b-41d4-a716-446655440000",
    "alvo_id": "550e8400-e29b-41d4-a716-446655440001",
    "canal": "whatsapp",
    "template_id": "550e8400-e29b-41d4-a716-446655440002"  // Opcional
}
```

**Resposta para WhatsApp (Manual)**

```json
{
    "acao_id": "550e8400-e29b-41d4-a716-446655440003",
    "ativista_id": "user-123",
    "campanha_id": "550e8400-e29b-41d4-a716-446655440000",
    "alvo_id": "550e8400-e29b-41d4-a716-446655440001",
    "status_atual": "AGUARDANDO_ACAO_HUMANA",
    "proximo_passo": {
        "tipo": "REDIRECIONAR_LINK",
        "instrucao": "Clique no link para enviar a mensagem no WhatsApp",
        "dados": {
            "link": "https://wa.me/5511999999999?text=Ol%C3%A1",
            "texto": "Olá, esta é uma mensagem de pressão"
        }
    }
}
```

**Obter Detalhes da Ação**

```http
GET /api/v1/acoes/{acao_id}
Authorization: Bearer {token_jwt}
```

**Obter Status da Ação**

```http
GET /api/v1/acoes/{acao_id}/status
Authorization: Bearer {token_jwt}
```

**Resposta**

```json
{
    "id": "550e8400-e29b-41d4-a716-446655440003",
    "status": "CONCLUIDA",
    "metrica_qualidade": "alta",
    "confirmado_em": "2026-08-04T14:30:00Z"
}
```

**Confirmar Ação Manual**

```http
PATCH /api/v1/acoes/{acao_id}/confirmar
Authorization: Bearer {token_jwt}
Content-Type: application/json

{}  // Corpo vazio
```

### Health Check

```http
GET /api/health
```

```json
{
    "status": "ok",
    "environment": "development"
}
```

### Métricas Prometheus

```http
GET /api/metrics
```

## 🔄 Fluxo de Trabalho

### Fluxo Automático (E-mail/Telefone)

```text
Ativista → POST /api/acoes → Backend registra → Chama provider →
→ Aguarda webhook → Atualiza status → Concluído
```

### Fluxo Manual (WhatsApp/Instagram)

```text
Ativista → POST /api/acoes → Backend registra → Gera link/texto →
→ Retorna próximo passo → Ativista executa manualmente →
→ PATCH /confirmar → Calcula métrica → Concluído
```

### Matriz de Canais

| Canal | Modo | Resposta | Confirmação | Tempo Esperado |
|-------|------|----------|-------------|----------------|
| E-mail | API (SendGrid) | `WEBHOOK_AGUARDAR` | Automática (webhook) | ≤ 5s |
| Telefone | API (Twilio) | `WEBHOOK_AGUARDAR` | Automática (webhook) | ≤ 5s |
| WhatsApp | Manual (Link) | `REDIRECIONAR_LINK` | Manual (PATCH /confirmar) | 5s - 60s |
| Instagram | Manual (Texto) | `EXIBIR_TEXTO_E_ABRIR_PERFIL` | Manual (PATCH /confirmar) | 5s - 60s |

### Métricas de Qualidade

| Tempo de Resposta | Classificação | Significado |
|----|----|----|
| < 5s | **suspeita** | Provavelmente automatizado |
| 5s - 60s | **alta** | Resposta rápida e humana |
| 60s - 120s | **media** | Resposta dentro do esperado |
| > 120s | **baixa** | Resposta lenta |

## 🧪 Testes

### Executar Testes

```bash
# Todos os testes
make test

# Testes com cobertura
make test-cov

# Testes específicos
pytest tests/unit/test_acoes.py -v
```

### Cobertura de Testes

- ✅ Testes unitários de serviços
- ✅ Testes de integração com API
- ✅ Testes de repositórios
- ✅ Testes de segurança
- ✅ Testes de validação

## 📊 Monitoramento

### Logs Estruturados

Todos os logs são emitidos em formato JSON para fácil integração com ferramentas de observabilidade:

```json
{
    "timestamp": "2026-08-04T14:30:00Z",
    "level": "info",
    "logger": "app.services.orquestrador",
    "message": "Ação executada com sucesso",
    "acao_id": "550e8400-e29b-41d4-a716-446655440003",
    "canal": "whatsapp",
    "status": "AGUARDANDO_ACAO_HUMANA"
}
```

### Métricas Coletadas

- ✅ Tempo de resposta por endpoint
- ✅ Taxa de sucesso/falha por canal
- ✅ Distribuição de qualidade das ações
- ✅ Tempo médio de confirmação manual
- ✅ Uso de recursos (CPU, memória)

### Endpoints de Monitoramento

- **Health Check:** `/api/health`
- **Métricas:** `/api/metrics` (Prometheus)
- **Logs:** Saída JSON para stdout

## 🐳 Deploy

### Construir Imagem Docker

```bash
make docker-build
```

### Subir em Produção

```bash
# Configure variáveis de produção
export APP_ENV=production
export DATABASE_URL=postgresql://user:pass@prod-db:5432/pressao

# Suba os serviços
docker-compose -f docker/docker-compose.yml up -d
```

### Migrações em Produção

```bash
# Dentro do container
docker exec -it pressao-api-1 alembic upgrade head
```

### Variáveis de Produção Necessárias

- `APP_ENV=production`
- `DEBUG=false`
- `ALLOWED_ORIGINS` = Lista de domínios permitidos
- Certificados SSL/HTTPS configurados
- Variáveis de banco de dados de produção

## 🤝 Contribuição

### Setup de Desenvolvimento

```bash
# Clone o repo
git clone https://github.com/bonde-org/pressao-api.git
cd pressao-api

# Instale dependências de desenvolvimento
make install

# Configure pre-commit hooks
pre-commit install

# Execute os testes
make test
```

### Padrões de Código

- ✅ Seguir PEP 8
- ✅ Usar Black para formatação (`make format`)
- ✅ Type hints com mypy (`make lint`)
- ✅ Documentação de funções e classes
- ✅ Testes para novas funcionalidades
- ✅ Seguir princípios SOLID

### Fluxo de Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (git checkout -b feature/nova-funcionalidade)
3. Faça commit das alterações (git commit -m 'Adiciona nova funcionalidade')
4. Push para a branch (git push origin feature/nova-funcionalidade)
5. Abra um Pull Request

## 📝 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](./LICENSE) para detalhes.

## 📚 Recursos Adicionais

- [Documentação FastAPI](https://fastapi.tiangolo.com)
- [Documentação Keycloak](https://www.keycloak.org/documentation)
- [Documentação SQLAlchemy](https://docs.sqlalchemy.org/en/20/)
- [Documentação Docker](https://docs.docker.com)

----

Feito com ❤️ para ativistas e causas sociais