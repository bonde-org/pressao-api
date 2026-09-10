import http from 'k6/http';
import { check, sleep } from 'k6';

import { BASE_URL, CAMPANHA_ID, getAlvoIds } from '../config.js';
import { authHeaders, fetchToken } from './auth.js';
import { buildAcaoPayload, pickCanalAndAlvo } from './data.js';

const MANUAL_CHANNELS = ['whatsapp', 'instagram'];

// Token por VU (setup data é imutável; JWT Keycloak local expira ~5 min)
let vuToken;

function ensureToken(initialToken) {
  if (!vuToken) {
    vuToken = initialToken;
  }
  return vuToken;
}

function refreshToken() {
  vuToken = fetchToken({ force: true });
  return vuToken;
}

/**
 * Fluxo simulado do plugin WordPress:
 * listar alvos → criar ação → confirmar (canais manuais) → ler contador (ocasional).
 *
 * Em 401, renova o token Keycloak uma vez e repete a chamada.
 */
export function executeUserJourney(initialToken) {
  let token = ensureToken(initialToken);
  let headers = authHeaders(token);
  const campanhaId = CAMPANHA_ID;
  const alvos = getAlvoIds();

  let listRes = http.get(`${BASE_URL}/api/v1/alvos/campanha/${campanhaId}`, { headers });
  if (listRes.status === 401) {
    token = refreshToken();
    headers = authHeaders(token);
    listRes = http.get(`${BASE_URL}/api/v1/alvos/campanha/${campanhaId}`, { headers });
  }
  check(listRes, {
    'listar alvos status 200': (r) => r.status === 200,
  });

  const { canal, alvoId } = pickCanalAndAlvo(alvos);
  const payload = JSON.stringify(
    buildAcaoPayload(campanhaId, alvoId, canal, __VU, __ITER)
  );

  let createRes = http.post(`${BASE_URL}/api/v1/acoes/`, payload, { headers });
  if (createRes.status === 401) {
    token = refreshToken();
    headers = authHeaders(token);
    createRes = http.post(`${BASE_URL}/api/v1/acoes/`, payload, { headers });
  }
  check(createRes, {
    'criar acao status 201': (r) => r.status === 201,
  });

  if (createRes.status === 201 && MANUAL_CHANNELS.includes(canal)) {
    const acaoId = createRes.json('acao_id');
    sleep(1);

    let confirmRes = http.patch(
      `${BASE_URL}/api/v1/acoes/${acaoId}/confirmar`,
      null,
      { headers }
    );
    if (confirmRes.status === 401) {
      token = refreshToken();
      headers = authHeaders(token);
      confirmRes = http.patch(
        `${BASE_URL}/api/v1/acoes/${acaoId}/confirmar`,
        null,
        { headers }
      );
    }
    check(confirmRes, {
      'confirmar acao status 200': (r) => r.status === 200,
    });
  }

  if (Math.random() < 0.1) {
    let campanhaRes = http.get(`${BASE_URL}/api/v1/campanhas/${campanhaId}`, { headers });
    if (campanhaRes.status === 401) {
      token = refreshToken();
      headers = authHeaders(token);
      campanhaRes = http.get(`${BASE_URL}/api/v1/campanhas/${campanhaId}`, { headers });
    }
    check(campanhaRes, {
      'ler campanha status 200': (r) => r.status === 200,
    });
  }

  sleep(0.3 + Math.random() * 0.7);
}
