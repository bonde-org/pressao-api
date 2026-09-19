#!/usr/bin/env bash
# Upsert de um candidato apoiador via REST do plugin Pressão.
#
# Pré-requisito: Application Password (Usuários → Perfil) de um admin (manage_options).
#
# Uso:
#   export WP_URL="https://seu-site.exemplo"
#   export WP_USER="admin"
#   export WP_APP_PASSWORD="xxxx xxxx xxxx xxxx xxxx xxxx"
#   ./upsert-candidato-apoiador.sh
#
# Variáveis opcionais: NOME, CARGO, PARTIDO, DESCRICAO, INSTAGRAM, IMAGEM_ID, IMAGEM_URL, FOTO_PATH

set -euo pipefail

: "${WP_URL:?Defina WP_URL (ex: https://seu-site.exemplo)}"
: "${WP_USER:?Defina WP_USER}"
: "${WP_APP_PASSWORD:?Defina WP_APP_PASSWORD (Application Password)}"

NOME="${NOME:-Fulana de Tal}"
CARGO="${CARGO:-Vereadora}"
PARTIDO="${PARTIDO:-PT}"
DESCRICAO="${DESCRICAO:-Exemplo via API REST}"
INSTAGRAM="${INSTAGRAM:-@fulanadetal}"
IMAGEM_ID="${IMAGEM_ID:-}"
IMAGEM_URL="${IMAGEM_URL:-}"
FOTO_PATH="${FOTO_PATH:-}"

AUTH=(-u "${WP_USER}:${WP_APP_PASSWORD}")
BASE="${WP_URL%/}/wp-json"

# 1) (opcional) upload de foto local via REST core → imagem_id
if [[ -n "${FOTO_PATH}" ]]; then
  if [[ ! -f "${FOTO_PATH}" ]]; then
    echo "Arquivo não encontrado: ${FOTO_PATH}" >&2
    exit 1
  fi
  echo "Enviando mídia: ${FOTO_PATH}"
  MEDIA_RESP=$(curl -sS "${AUTH[@]}" \
    -F "file=@${FOTO_PATH}" \
    "${BASE}/wp/v2/media")
  IMAGEM_ID=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("id",""))' <<<"${MEDIA_RESP}" 2>/dev/null || true)
  if [[ -z "${IMAGEM_ID}" ]]; then
    echo "Falha no upload de mídia:" >&2
    echo "${MEDIA_RESP}" >&2
    exit 1
  fi
  echo "imagem_id=${IMAGEM_ID}"
fi

# 2) Monta JSON do upsert (imagem_id e imagem_url são opcionais)
PAYLOAD=$(IMAGEM_ID="${IMAGEM_ID}" IMAGEM_URL="${IMAGEM_URL}" \
  NOME="${NOME}" CARGO="${CARGO}" PARTIDO="${PARTIDO}" \
  DESCRICAO="${DESCRICAO}" INSTAGRAM="${INSTAGRAM}" \
  python3 - <<'PY'
import json, os
body = {
    "nome": os.environ["NOME"],
    "cargo": os.environ["CARGO"],
    "partido": os.environ["PARTIDO"],
    "descricao": os.environ["DESCRICAO"],
    "instagram": os.environ["INSTAGRAM"],
}
img_id = os.environ.get("IMAGEM_ID", "").strip()
img_url = os.environ.get("IMAGEM_URL", "").strip()
if img_id:
    body["imagem_id"] = int(img_id)
elif img_url:
    body["imagem_url"] = img_url
print(json.dumps(body, ensure_ascii=False))
PY
)

echo "PUT ${BASE}/pressao/v1/candidatos-apoiadores"
curl -sS "${AUTH[@]}" \
  -H "Content-Type: application/json" \
  -X PUT \
  -d "${PAYLOAD}" \
  "${BASE}/pressao/v1/candidatos-apoiadores"
echo
