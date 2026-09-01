/**
 * Configuração centralizada dos testes de carga k6.
 * Sobrescreva via variáveis de ambiente (make load-test VUS=500 ...).
 */

export const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export const KEYCLOAK_URL = __ENV.KEYCLOAK_URL || 'http://localhost:8080';
export const KEYCLOAK_REALM = __ENV.KEYCLOAK_REALM || 'pressao';
export const KEYCLOAK_CLIENT_ID = __ENV.KEYCLOAK_CLIENT_ID || 'pressao-api';
export const KEYCLOAK_CLIENT_SECRET = __ENV.KEYCLOAK_CLIENT_SECRET || '';

export const CAMPANHA_ID = __ENV.CAMPANHA_ID || '';
export const ALVO_EMAIL_ID = __ENV.ALVO_EMAIL_ID || '';
export const ALVO_WHATSAPP_ID = __ENV.ALVO_WHATSAPP_ID || '';
export const ALVO_INSTAGRAM_ID = __ENV.ALVO_INSTAGRAM_ID || '';
export const ALVO_TELEFONE_ID = __ENV.ALVO_TELEFONE_ID || '';

const DEFAULT_VUS = {
  smoke: 5,
  load: 200,
  stress: 500,
  spike: 300,
};

const DEFAULT_DURATION = {
  smoke: '1m',
  load: '5m',
  stress: '10m',
  spike: '3m',
};

function parseIntEnv(name, fallback) {
  const value = __ENV[name];
  if (value === undefined || value === '') {
    return fallback;
  }
  const parsed = parseInt(value, 10);
  return Number.isNaN(parsed) ? fallback : parsed;
}

function parseDurationEnv(name, fallback) {
  const value = __ENV[name];
  return value && value !== '' ? value : fallback;
}

export function getThresholds() {
  const p95 = __ENV.THRESHOLD_P95 || '500';
  const p99 = __ENV.THRESHOLD_P99 || '1000';
  const errorRate = __ENV.THRESHOLD_ERROR_RATE || '0.01';

  return {
    http_req_duration: [`p(95)<${p95}`, `p(99)<${p99}`],
    http_req_failed: [`rate<${errorRate}`],
    checks: ['rate>0.95'],
  };
}

export function buildStages(scenario) {
  const vus = parseIntEnv('VUS', DEFAULT_VUS[scenario] || 200);
  const duration = parseDurationEnv('DURATION', DEFAULT_DURATION[scenario] || '5m');
  const rps = parseIntEnv('RPS', 0);

  if (rps > 0) {
    return null;
  }

  switch (scenario) {
    case 'smoke':
      return [
        { duration: '15s', target: vus },
        { duration, target: vus },
        { duration: '15s', target: 0 },
      ];
    case 'stress':
      return [
        { duration: '2m', target: Math.floor(vus * 0.2) },
        { duration: '3m', target: Math.floor(vus * 0.5) },
        { duration: '3m', target: vus },
        { duration: duration, target: vus },
        { duration: '2m', target: 0 },
      ];
    case 'spike':
      return [
        { duration: '30s', target: 10 },
        { duration: '30s', target: vus },
        { duration: '1m', target: vus },
        { duration: '30s', target: 10 },
        { duration: '30s', target: 0 },
      ];
    case 'load':
    default:
      return [
        { duration: '30s', target: Math.floor(vus * 0.25) },
        { duration: '1m', target: Math.floor(vus * 0.5) },
        { duration: '30s', target: vus },
        { duration, target: vus },
        { duration: '30s', target: 0 },
      ];
  }
}

export function buildOptions(scenario) {
  const vus = parseIntEnv('VUS', DEFAULT_VUS[scenario] || 200);
  const duration = parseDurationEnv('DURATION', DEFAULT_DURATION[scenario] || '5m');
  const rps = parseIntEnv('RPS', 0);
  const stages = buildStages(scenario);

  if (rps > 0) {
    return {
      scenarios: {
        constant_load: {
          executor: 'constant-arrival-rate',
          rate: rps,
          timeUnit: '1s',
          duration,
          preAllocatedVUs: Math.min(vus, 50),
          maxVUs: vus,
        },
      },
      thresholds: getThresholds(),
    };
  }

  return {
    stages,
    thresholds: getThresholds(),
  };
}

export function getAlvoIds() {
  return {
    email: ALVO_EMAIL_ID,
    whatsapp: ALVO_WHATSAPP_ID,
    instagram: ALVO_INSTAGRAM_ID,
    telefone: ALVO_TELEFONE_ID,
  };
}

export function validateConfig() {
  const missing = [];
  if (!CAMPANHA_ID) missing.push('CAMPANHA_ID');
  if (!ALVO_EMAIL_ID) missing.push('ALVO_EMAIL_ID');
  if (!ALVO_WHATSAPP_ID) missing.push('ALVO_WHATSAPP_ID');
  if (!ALVO_INSTAGRAM_ID) missing.push('ALVO_INSTAGRAM_ID');

  if (missing.length > 0) {
    throw new Error(
      `Variáveis obrigatórias ausentes: ${missing.join(', ')}. ` +
        'Execute "make load-test-seed" ou defina-as manualmente.'
    );
  }
}
