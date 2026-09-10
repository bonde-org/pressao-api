# Testes de carga (k6)

Suíte de testes de carga da **pressao-api**, simulando o fluxo do plugin WordPress contra a API REST.

## Pré-requisitos

- [k6](https://grafana.com/docs/k6/latest/set-up/install-k6/) — `brew install k6` (macOS)
- `curl`, `jq`
- API e Keycloak em execução (`make docker-up`)
- `KEYCLOAK_CLIENT_SECRET` exportado

## Comandos rápidos

```bash
cd pressao-api
export KEYCLOAK_CLIENT_SECRET=seu-secret

# Preparar dados (campanha + alvos + templates)
make load-test-seed

# Cenários
make load-test SCENARIO=smoke
make load-test SCENARIO=load      # baseline MVP (~200 VUs, 5 min)
make load-test SCENARIO=stress    # default 500 VUs
make load-test SCENARIO=spike

# Teste maior — só mudar parâmetros
make load-test SCENARIO=stress VUS=500 DURATION=10m
make load-test SCENARIO=load RPS=50 VUS=300 DURATION=5m

# Relatório parcial (Markdown)
make load-test-report
```

## Estrutura

```
tests/k6/
├── config.js              # Defaults e thresholds
├── lib/
│   ├── auth.js            # Token Keycloak
│   ├── data.js            # Payloads
│   └── user-journey.js    # Fluxo simulado
├── scenarios/
│   ├── smoke.js
│   ├── load.js
│   ├── stress.js
│   └── spike.js
├── results/               # gitignored — JSON + logs por execução
└── .env.load-test         # gitignored — IDs gerados pelo seed
```

## Variáveis de ambiente

| Variável | Default | Descrição |
|----------|---------|-----------|
| `SCENARIO` | `load` | smoke, load, stress, spike |
| `BASE_URL` | `http://localhost:8000` | URL da API |
| `KEYCLOAK_URL` | `http://localhost:8080` | URL do Keycloak |
| `KEYCLOAK_REALM` | `pressao` | Realm |
| `KEYCLOAK_CLIENT_ID` | `pressao-api` | Client M2M |
| `KEYCLOAK_CLIENT_SECRET` | — | **Obrigatório** |
| `VUS` | por cenário | Usuários virtuais |
| `DURATION` | por cenário | Duração da fase estável |
| `RPS` | — | Se definido, usa taxa fixa de req/s |
| `CAMPANHA_ID` | do seed | UUID da campanha de teste |
| `ALVO_*_ID` | do seed | UUIDs dos alvos por canal |
| `TOKEN` | opcional | JWT **só nesta sessão**; não grave em `.env.load-test` (expira ~5 min) |
| `THRESHOLD_P95` | `500` | Limite p95 em ms |
| `THRESHOLD_P99` | `1000` | Limite p99 em ms |
| `SKIP_THRESHOLDS` | — | `1` desabilita thresholds (ambiente local lento) |

## Troubleshooting

### 100% de falha HTTP / checks em 0%

Quase sempre **401 Unauthorized** por JWT expirado:

1. O Keycloak local emite access tokens com TTL curto (~5 min).
2. Versões antigas do seed gravavam `TOKEN=...` em `.env.load-test`; o runner reutilizava esse valor depois.
3. Sintoma típico: latência baixa (~2–5 ms) e `http_req_failed: 100%`.

**Correção:** remova qualquer linha `TOKEN=` de `tests/k6/.env.load-test`, exporte `KEYCLOAK_CLIENT_SECRET` e rode de novo. O k6 busca token fresco no `setup` e renova em caso de 401.

```bash
jq -r 'select(.type=="Point" and .metric=="http_reqs") | .data.tags.status' \
  tests/k6/results/<timestamp>-smoke/metrics.json | sort | uniq -c
```

## Homologação

```bash
export BASE_URL=https://sua-api-homolog.example.com
export KEYCLOAK_URL=https://seu-keycloak.example.com
export KEYCLOAK_CLIENT_SECRET=...
make load-test SCENARIO=load
```

## Documentação para o cliente

Ver [`docs/04-performance-e-escalabilidade.md`](../../docs/04-performance-e-escalabilidade.md) no repositório pai.

## Fluxo simulado

1. `GET /api/v1/alvos/campanha/{id}`
2. `POST /api/v1/acoes/` (email ~50%, whatsapp ~20%, instagram ~15%, telefone ~15%)
3. `PATCH /api/v1/acoes/{id}/confirmar` (canais manuais)
4. `GET /api/v1/campanhas/{id}` (~10% das iterações)

## Thresholds default

- p95 < 500 ms
- p99 < 1000 ms
- erros HTTP < 1%
- checks > 95%
