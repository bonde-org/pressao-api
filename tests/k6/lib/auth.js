import http from 'k6/http';
import { check } from 'k6';

import {
  KEYCLOAK_CLIENT_ID,
  KEYCLOAK_CLIENT_SECRET,
  KEYCLOAK_REALM,
  KEYCLOAK_URL,
} from '../config.js';

/**
 * Obtém token JWT via client credentials (Keycloak).
 *
 * TOKEN de ambiente só deve ser usado quando o usuário exporta na sessão
 * (não reutilizar JWT gravado em .env.load-test — expira em ~5 min).
 *
 * @param {{ force?: boolean }} [opts] - force=true ignora TOKEN e busca novo no Keycloak
 */
export function fetchToken(opts = {}) {
  if (!opts.force && __ENV.TOKEN && __ENV.TOKEN !== '') {
    return __ENV.TOKEN;
  }

  if (!KEYCLOAK_CLIENT_SECRET) {
    throw new Error(
      'KEYCLOAK_CLIENT_SECRET não definido. Exporte a variável ou use TOKEN=...'
    );
  }

  const tokenUrl =
    `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`;

  const payload = {
    client_id: KEYCLOAK_CLIENT_ID,
    client_secret: KEYCLOAK_CLIENT_SECRET,
    grant_type: 'client_credentials',
  };

  const res = http.post(tokenUrl, payload, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });

  check(res, {
    'token obtido': (r) => r.status === 200,
  });

  if (res.status !== 200) {
    throw new Error(`Falha ao obter token Keycloak: HTTP ${res.status} — ${res.body}`);
  }

  return res.json('access_token');
}

export function authHeaders(token) {
  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}

export function setupAuth() {
  const token = fetchToken();
  return { token };
}
