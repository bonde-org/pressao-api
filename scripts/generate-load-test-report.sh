#!/usr/bin/env bash
# Gera trecho Markdown a partir do summary.json exportado pelo k6.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS_ROOT="${ROOT_DIR}/tests/k6/results"
OUTPUT_FILE="${OUTPUT_FILE:-${ROOT_DIR}/tests/k6/results/latest-report.md}"

if [[ -n "${RESULT_DIR:-}" ]]; then
  TARGET_DIR="${RESULT_DIR}"
else
  TARGET_DIR="$(find "${RESULTS_ROOT}" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort | tail -n 1 || true)"
fi

if [[ -z "${TARGET_DIR}" || ! -d "${TARGET_DIR}" ]]; then
  echo "Erro: nenhum diretório de resultados encontrado. Execute 'make load-test' primeiro." >&2
  exit 1
fi

SUMMARY_FILE="${TARGET_DIR}/summary.json"
META_FILE="${TARGET_DIR}/meta.env"

if [[ ! -f "${SUMMARY_FILE}" ]]; then
  echo "Erro: ${SUMMARY_FILE} não encontrado." >&2
  exit 1
fi

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Erro: '$1' não encontrado." >&2
    exit 1
  fi
}

require_cmd jq

SCENARIO="desconhecido"
BASE_URL="desconhecido"
TIMESTAMP="desconhecido"
CAMPANHA_ID="desconhecido"

if [[ -f "${META_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${META_FILE}"
fi

HTTP_REQS="$(jq -r '.metrics.http_reqs.count // .metrics.http_reqs.values.count // 0' "${SUMMARY_FILE}")"
HTTP_FAILED_RATE="$(jq -r '.metrics.http_req_failed.value // .metrics.http_req_failed.values.rate // 0' "${SUMMARY_FILE}")"
HTTP_DURATION_AVG="$(jq -r '.metrics.http_req_duration.avg // .metrics.http_req_duration.values.avg // 0' "${SUMMARY_FILE}")"
HTTP_DURATION_P50="$(jq -r '.metrics.http_req_duration.med // .metrics.http_req_duration.values.med // 0' "${SUMMARY_FILE}")"
HTTP_DURATION_P90="$(jq -r '.metrics.http_req_duration["p(90)"] // .metrics.http_req_duration.values["p(90)"] // 0' "${SUMMARY_FILE}")"
HTTP_DURATION_P95="$(jq -r '.metrics.http_req_duration["p(95)"] // .metrics.http_req_duration.values["p(95)"] // 0' "${SUMMARY_FILE}")"
HTTP_DURATION_P99="$(jq -r '.metrics.http_req_duration["p(99)"] // .metrics.http_req_duration.values["p(99)"] // 0' "${SUMMARY_FILE}")"
HTTP_DURATION_MAX="$(jq -r '.metrics.http_req_duration.max // .metrics.http_req_duration.values.max // 0' "${SUMMARY_FILE}")"
CHECKS_RATE="$(jq -r '.metrics.checks.value // .metrics.checks.values.rate // 0' "${SUMMARY_FILE}")"
ITERATIONS="$(jq -r '.metrics.iterations.count // .metrics.iterations.values.count // 0' "${SUMMARY_FILE}")"
VUS_MAX="$(jq -r '.metrics.vus_max.max // .metrics.vus_max.value // .metrics.vus_max.values.max // 0' "${SUMMARY_FILE}")"
DATA_RECEIVED="$(jq -r '.metrics.data_received.count // .metrics.data_received.values.count // 0' "${SUMMARY_FILE}")"
DATA_SENT="$(jq -r '.metrics.data_sent.count // .metrics.data_sent.values.count // 0' "${SUMMARY_FILE}")"
TEST_DURATION="$(jq -r '.state.testRunDurationMs // 0' "${SUMMARY_FILE}")"
HTTP_RPS="$(jq -r '.metrics.http_reqs.rate // .metrics.http_reqs.values.rate // 0' "${SUMMARY_FILE}")"

format_ms() {
  awk -v ms="$1" 'BEGIN { printf "%.2f", ms }'
}

format_pct() {
  awk -v rate="$1" 'BEGIN { printf "%.2f", rate * 100 }'
}

format_bytes() {
  awk -v bytes="$1" 'BEGIN {
    if (bytes >= 1048576) printf "%.2f MB", bytes / 1048576;
    else if (bytes >= 1024) printf "%.2f KB", bytes / 1024;
    else printf "%.0f B", bytes;
  }'
}

mkdir -p "$(dirname "${OUTPUT_FILE}")"

cat > "${OUTPUT_FILE}" <<EOF
## Resultado do teste — ${SCENARIO}

> Gerado automaticamente em $(date -Iseconds) a partir de \`${TARGET_DIR}\`

| Campo | Valor |
|-------|-------|
| Cenário | ${SCENARIO} |
| Ambiente (BASE_URL) | ${BASE_URL} |
| Campanha | ${CAMPANHA_ID} |
| Timestamp | ${TIMESTAMP} |
| Duração do teste | $(format_ms "${TEST_DURATION}") ms |
| VUs máximos | ${VUS_MAX} |
| Iterações | ${ITERATIONS} |
| Requisições HTTP | ${HTTP_REQS} |
| Throughput HTTP | $(format_ms "${HTTP_RPS}") req/s |
| Taxa de falha HTTP | $(format_pct "${HTTP_FAILED_RATE}")% |
| Taxa de checks OK | $(format_pct "${CHECKS_RATE}")% |
| Dados recebidos | $(format_bytes "${DATA_RECEIVED}") |
| Dados enviados | $(format_bytes "${DATA_SENT}") |

### Latência HTTP (ms)

| Métrica | Valor (ms) |
|---------|------------|
| Média | $(format_ms "${HTTP_DURATION_AVG}") |
| p50 | $(format_ms "${HTTP_DURATION_P50}") |
| p90 | $(format_ms "${HTTP_DURATION_P90}") |
| p95 | $(format_ms "${HTTP_DURATION_P95}") |
| p99 | $(format_ms "${HTTP_DURATION_P99}") |
| Máximo | $(format_ms "${HTTP_DURATION_MAX}") |

### Observações para análise

- Correlacionar p95/p99 com \`pressao_api_http_request_duration_seconds\` no Grafana durante o mesmo intervalo.
- Verificar \`pressao_api_db_connections_active\` para identificar saturação de pool PostgreSQL.
- Em homologação/produção, registrar número de réplicas da API (HPA) durante o teste.

EOF

echo "Relatório parcial gerado: ${OUTPUT_FILE}"
