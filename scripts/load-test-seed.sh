#!/usr/bin/env bash
# Prepara campanha, alvos e templates para testes de carga k6.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/tests/k6/.env.load-test"

BASE_URL="${BASE_URL:-http://localhost:8000}"
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
KEYCLOAK_REALM="${KEYCLOAK_REALM:-pressao}"
KEYCLOAK_CLIENT_ID="${KEYCLOAK_CLIENT_ID:-pressao-api}"
KEYCLOAK_CLIENT_SECRET="${KEYCLOAK_CLIENT_SECRET:-}"
EMAIL_ALVOS_COUNT="${EMAIL_ALVOS_COUNT:-20}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Erro: '$1' não encontrado. Instale antes de continuar." >&2
    exit 1
  fi
}

require_cmd curl
require_cmd jq

if [[ -z "${KEYCLOAK_CLIENT_SECRET}" ]]; then
  echo "Erro: defina KEYCLOAK_CLIENT_SECRET (ex.: export KEYCLOAK_CLIENT_SECRET=...)" >&2
  exit 1
fi

echo "Obtendo token Keycloak..."
TOKEN="$(
  curl -sf -X POST \
    "${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token" \
    -d "client_id=${KEYCLOAK_CLIENT_ID}" \
    -d "client_secret=${KEYCLOAK_CLIENT_SECRET}" \
    -d "grant_type=client_credentials" \
    | jq -r '.access_token'
)"

if [[ -z "${TOKEN}" || "${TOKEN}" == "null" ]]; then
  echo "Erro: não foi possível obter token Keycloak." >&2
  exit 1
fi

AUTH_HEADER="Authorization: Bearer ${TOKEN}"
JSON_HEADER="Content-Type: application/json"

api_post() {
  local endpoint="$1"
  local payload="$2"
  curl -sf -X POST "${BASE_URL}${endpoint}" \
    -H "${AUTH_HEADER}" \
    -H "${JSON_HEADER}" \
    -d "${payload}"
}

api_get() {
  local endpoint="$1"
  curl -sf -X GET "${BASE_URL}${endpoint}" \
    -H "${AUTH_HEADER}"
}

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
CAMPANHA_NOME="Campanha Load Test ${TIMESTAMP}"

echo "Criando campanha '${CAMPANHA_NOME}'..."
CAMPANHA_ID="$(
  api_post "/api/v1/campanhas/" \
    "$(jq -nc --arg nome "${CAMPANHA_NOME}" '{nome: $nome, descricao: "Dados para testes de carga k6", ativa: true}')" \
    | jq -r '.id'
)"

echo "Criando ${EMAIL_ALVOS_COUNT} alvos de e-mail..."
for i in $(seq 1 "${EMAIL_ALVOS_COUNT}"); do
  api_post "/api/v1/alvos/" \
    "$(jq -nc \
      --arg campanha_id "${CAMPANHA_ID}" \
      --arg nome "Alvo Email ${i}" \
      --arg contato "alvo${i}@loadtest.example.com" \
      '{campanha_id: $campanha_id, nome: $nome, contato: $contato, tipo_contato: "email"}')" \
    >/dev/null
done

echo "Criando alvos individuais (whatsapp, instagram, telefone)..."
ALVO_WHATSAPP_ID="$(
  api_post "/api/v1/alvos/" \
    "$(jq -nc \
      --arg campanha_id "${CAMPANHA_ID}" \
      '{campanha_id: $campanha_id, nome: "Alvo WhatsApp", contato: "+5511999990001", tipo_contato: "whatsapp"}')" \
    | jq -r '.id'
)"

ALVO_INSTAGRAM_ID="$(
  api_post "/api/v1/alvos/" \
    "$(jq -nc \
      --arg campanha_id "${CAMPANHA_ID}" \
      '{campanha_id: $campanha_id, nome: "Alvo Instagram", contato: "@loadtest_perfil", tipo_contato: "instagram"}')" \
    | jq -r '.id'
)"

ALVO_TELEFONE_ID="$(
  api_post "/api/v1/alvos/" \
    "$(jq -nc \
      --arg campanha_id "${CAMPANHA_ID}" \
      '{campanha_id: $campanha_id, nome: "Alvo Telefone", contato: "(11) 98888-7777", tipo_contato: "telefone"}')" \
    | jq -r '.id'
)"

echo "Resolvendo alvo agregado de e-mail..."
ALVO_EMAIL_ID="$(
  api_get "/api/v1/alvos/campanha/${CAMPANHA_ID}" \
    | jq -r '.[] | select(.modo == "agregado") | .id' \
    | head -n 1
)"

if [[ -z "${ALVO_EMAIL_ID}" ]]; then
  echo "Erro: alvo agregado de e-mail não encontrado." >&2
  exit 1
fi

echo "Criando templates por canal..."
for spec in "email:Assunto Load Test:Corpo do e-mail de pressão {nome}." \
            "whatsapp:Mensagem WhatsApp:Olá, mensagem de pressão via WhatsApp." \
            "instagram:Mensagem Instagram:Texto de pressão para Instagram." \
            "telefone:Script Telefone:Roteiro de ligação de pressão."; do
  IFS=':' read -r canal titulo conteudo <<< "${spec}"
  api_post "/api/v1/templates/" \
    "$(jq -nc \
      --arg campanha_id "${CAMPANHA_ID}" \
      --arg canal "${canal}" \
      --arg titulo "${titulo}" \
      --arg conteudo "${conteudo}" \
      '{campanha_id: $campanha_id, canal: $canal, titulo: $titulo, conteudo: $conteudo, ativo: true}')" \
    >/dev/null
done

mkdir -p "$(dirname "${ENV_FILE}")"
cat > "${ENV_FILE}" <<EOF
# Gerado por scripts/load-test-seed.sh em $(date -Iseconds)
BASE_URL=${BASE_URL}
KEYCLOAK_URL=${KEYCLOAK_URL}
KEYCLOAK_REALM=${KEYCLOAK_REALM}
KEYCLOAK_CLIENT_ID=${KEYCLOAK_CLIENT_ID}
KEYCLOAK_CLIENT_SECRET=${KEYCLOAK_CLIENT_SECRET}
CAMPANHA_ID=${CAMPANHA_ID}
ALVO_EMAIL_ID=${ALVO_EMAIL_ID}
ALVO_WHATSAPP_ID=${ALVO_WHATSAPP_ID}
ALVO_INSTAGRAM_ID=${ALVO_INSTAGRAM_ID}
ALVO_TELEFONE_ID=${ALVO_TELEFONE_ID}
EOF

echo ""
echo "Seed concluído."
echo "  Campanha:  ${CAMPANHA_ID}"
echo "  Alvo email (agregado): ${ALVO_EMAIL_ID}"
echo "  Alvo whatsapp:         ${ALVO_WHATSAPP_ID}"
echo "  Alvo instagram:        ${ALVO_INSTAGRAM_ID}"
echo "  Alvo telefone:         ${ALVO_TELEFONE_ID}"
echo "  Arquivo:               ${ENV_FILE}"
