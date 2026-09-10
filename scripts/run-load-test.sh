#!/usr/bin/env bash
# Orquestra seed + execução k6 e salva resultados em tests/k6/results/.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

SCENARIO="${SCENARIO:-load}"
BASE_URL="${BASE_URL:-http://localhost:8000}"
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
KEYCLOAK_REALM="${KEYCLOAK_REALM:-pressao}"
KEYCLOAK_CLIENT_ID="${KEYCLOAK_CLIENT_ID:-pressao-api}"
KEYCLOAK_CLIENT_SECRET="${KEYCLOAK_CLIENT_SECRET:-}"
ENV_FILE="${ROOT_DIR}/tests/k6/.env.load-test"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
RESULT_DIR="${ROOT_DIR}/tests/k6/results/${TIMESTAMP}-${SCENARIO}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Erro: '$1' não encontrado." >&2
    echo "Instale k6: brew install k6 (macOS) ou https://grafana.com/docs/k6/latest/set-up/install-k6/" >&2
    exit 1
  fi
}

require_cmd k6
require_cmd curl
require_cmd jq

SCENARIO_FILE="${ROOT_DIR}/tests/k6/scenarios/${SCENARIO}.js"
if [[ ! -f "${SCENARIO_FILE}" ]]; then
  echo "Erro: cenário '${SCENARIO}' não existe (${SCENARIO_FILE})." >&2
  echo "Cenários disponíveis: smoke, load, stress, spike" >&2
  exit 1
fi

# TOKEN do .env.load-test NÃO deve ser reutilizado (JWT Keycloak expira em ~5 min).
# Só respeita TOKEN se o usuário exportou na sessão atual.
USER_TOKEN="${TOKEN:-}"

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "${ENV_FILE}"
  set +a
fi

if [[ -n "${USER_TOKEN}" ]]; then
  TOKEN="${USER_TOKEN}"
else
  unset TOKEN
fi

if [[ -z "${CAMPANHA_ID:-}" ]]; then
  echo "CAMPANHA_ID não definido — executando seed..."
  export BASE_URL KEYCLOAK_URL KEYCLOAK_REALM KEYCLOAK_CLIENT_ID KEYCLOAK_CLIENT_SECRET
  "${ROOT_DIR}/scripts/load-test-seed.sh"
  # shellcheck disable=SC1090
  set -a
  source "${ENV_FILE}"
  set +a
  unset TOKEN
fi

if [[ -z "${KEYCLOAK_CLIENT_SECRET:-}" && -z "${TOKEN:-}" ]]; then
  echo "Erro: defina KEYCLOAK_CLIENT_SECRET (ou TOKEN) antes de rodar o teste." >&2
  exit 1
fi

mkdir -p "${RESULT_DIR}"

K6_ENV=(
  -e "BASE_URL=${BASE_URL}"
  -e "KEYCLOAK_URL=${KEYCLOAK_URL}"
  -e "KEYCLOAK_REALM=${KEYCLOAK_REALM}"
  -e "KEYCLOAK_CLIENT_ID=${KEYCLOAK_CLIENT_ID}"
  -e "KEYCLOAK_CLIENT_SECRET=${KEYCLOAK_CLIENT_SECRET}"
  -e "CAMPANHA_ID=${CAMPANHA_ID}"
  -e "ALVO_EMAIL_ID=${ALVO_EMAIL_ID}"
  -e "ALVO_WHATSAPP_ID=${ALVO_WHATSAPP_ID}"
  -e "ALVO_INSTAGRAM_ID=${ALVO_INSTAGRAM_ID}"
  -e "ALVO_TELEFONE_ID=${ALVO_TELEFONE_ID:-}"
)

# Só passa TOKEN se o usuário exportou explicitamente nesta sessão.
if [[ -n "${USER_TOKEN}" ]]; then
  K6_ENV+=(-e "TOKEN=${USER_TOKEN}")
fi
if [[ -n "${VUS:-}" ]]; then
  K6_ENV+=(-e "VUS=${VUS}")
fi
if [[ -n "${DURATION:-}" ]]; then
  K6_ENV+=(-e "DURATION=${DURATION}")
fi
if [[ -n "${RPS:-}" ]]; then
  K6_ENV+=(-e "RPS=${RPS}")
fi
if [[ -n "${THRESHOLD_P95:-}" ]]; then
  K6_ENV+=(-e "THRESHOLD_P95=${THRESHOLD_P95}")
fi
if [[ -n "${THRESHOLD_P99:-}" ]]; then
  K6_ENV+=(-e "THRESHOLD_P99=${THRESHOLD_P99}")
fi
if [[ -n "${THRESHOLD_ERROR_RATE:-}" ]]; then
  K6_ENV+=(-e "THRESHOLD_ERROR_RATE=${THRESHOLD_ERROR_RATE}")
fi

META_FILE="${RESULT_DIR}/meta.env"
cat > "${META_FILE}" <<EOF
SCENARIO=${SCENARIO}
BASE_URL=${BASE_URL}
TIMESTAMP=${TIMESTAMP}
CAMPANHA_ID=${CAMPANHA_ID}
VUS=${VUS:-default}
DURATION=${DURATION:-default}
RPS=${RPS:-default}
EOF

echo "Executando k6 cenário '${SCENARIO}' contra ${BASE_URL}"
echo "Resultados em: ${RESULT_DIR}"
if [[ "${SKIP_THRESHOLDS:-}" == "1" ]]; then
  echo "SKIP_THRESHOLDS=1 — thresholds desabilitados (útil em ambiente local lento)"
fi
echo ""

K6_ARGS=()
if [[ "${SKIP_THRESHOLDS:-}" == "1" ]]; then
  K6_ARGS+=(--no-thresholds)
fi

k6 run \
  "${K6_ARGS[@]}" \
  "${K6_ENV[@]}" \
  --summary-export="${RESULT_DIR}/summary.json" \
  --out "json=${RESULT_DIR}/metrics.json" \
  "${SCENARIO_FILE}" \
  | tee "${RESULT_DIR}/console.log"

echo ""
echo "Teste concluído."
echo "  Resumo JSON: ${RESULT_DIR}/summary.json"
echo "  Métricas:    ${RESULT_DIR}/metrics.json"
echo "  Console:     ${RESULT_DIR}/console.log"
echo ""
echo "Para gerar trecho Markdown: make load-test-report RESULT_DIR=${RESULT_DIR}"
