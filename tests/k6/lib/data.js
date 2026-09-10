import { CAMPANHA_ID } from '../config.js';

/**
 * Monta payload de criação de ação compatível com a API.
 */
export function buildAcaoPayload(campanhaId, alvoId, canal, vu, iteration) {
  return {
    campanha_id: campanhaId || CAMPANHA_ID,
    alvo_id: alvoId,
    canal,
    anonimo: false,
    ativista: {
      nome: `LoadTest VU${vu} I${iteration}`,
      email: `loadtest+vu${vu}i${iteration}@example.com`,
    },
  };
}

/**
 * Escolhe canal e alvo_id com pesos similares ao uso real do plugin.
 */
export function pickCanalAndAlvo(alvos) {
  const roll = Math.random();

  if (roll < 0.5 && alvos.email) {
    return { canal: 'email', alvoId: alvos.email };
  }
  if (roll < 0.7 && alvos.whatsapp) {
    return { canal: 'whatsapp', alvoId: alvos.whatsapp };
  }
  if (roll < 0.85 && alvos.instagram) {
    return { canal: 'instagram', alvoId: alvos.instagram };
  }
  if (alvos.telefone) {
    return { canal: 'telefone', alvoId: alvos.telefone };
  }
  if (alvos.email) {
    return { canal: 'email', alvoId: alvos.email };
  }

  throw new Error('Nenhum alvo disponível para o teste de carga');
}
