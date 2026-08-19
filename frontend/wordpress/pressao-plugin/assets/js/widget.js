/**
 * Pressão Plugin - JavaScript
 * Com carregamento dinâmico da campanha via AJAX
 */

// Constantes
const ACTIONS_STORAGE_KEY = pressaoData?.localStorageKey || 'pressao_acoes_realizadas';
const COOKIE_USER_ID = pressaoData?.cookieUserIdKey || 'pressao_usuario_id';
const COOKIE_ACTIONS = pressaoData?.cookieActionsKey || 'pressao_acoes_realizadas';
const SESSAO_COOKIE = 'pressao_sessao_id';
const ATIVISTA_COOKIE = 'pressao_ativista_data';
const ATIVISTA_CONFIRM_COOKIE = 'pressao_ativista_last_confirm';

// ============================================
// COOKIE HELPERS
// ============================================

function setCookie(name, value, seconds) {
    let expires = '';
    if (seconds && seconds > 0) {
        const date = new Date();
        date.setTime(date.getTime() + (seconds * 1000));
        expires = '; expires=' + date.toUTCString();
    }
    document.cookie = name + '=' + encodeURIComponent(value) + expires + '; path=/; SameSite=Lax';
}

function getCookie(name) {
    const nameEQ = name + '=';
    const ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i].trim();
        if (c.indexOf(nameEQ) === 0) {
            return decodeURIComponent(c.substring(nameEQ.length));
        }
    }
    return null;
}

function getSessionDuration() {
    return parseInt(pressaoData?.sessionDuration) || 86400;
}

// ============================================
// SESSÃO
// ============================================

function getOrCreateSessaoId() {
    let sessaoId = getCookie(SESSAO_COOKIE);
    if (!sessaoId) {
        sessaoId = crypto.randomUUID();
        setCookie(SESSAO_COOKIE, sessaoId, getSessionDuration());
    }
    return sessaoId;
}

// ============================================
// CANAIS E REQUISITOS DE DADOS
// ============================================

const CANAIS_QUE_REQUEREM_ATIVISTA = {
    email: ['email'],
    telefone: ['telefone'],
    whatsapp: ['telefone'],
    instagram: []
};

function canalRequerAtivista(canal) {
    const campos = CANAIS_QUE_REQUEREM_ATIVISTA[canal];
    return campos && campos.length > 0;
}

// ============================================
// FUNÇÕES DO ATIVISTA
// ============================================

function getAtivistaData() {
    try {
        const data = getCookie(ATIVISTA_COOKIE);
        return data ? JSON.parse(data) : null;
    } catch (e) {
        return null;
    }
}

function saveAtivistaData(ativista) {
    try {
        setCookie(ATIVISTA_COOKIE, JSON.stringify(ativista), getSessionDuration());
        setCookie(ATIVISTA_CONFIRM_COOKIE, String(Date.now()), getSessionDuration());
        return true;
    } catch (e) {
        return false;
    }
}

function deleteCookie(name) {
    document.cookie = name + '=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
}

function clearPressaoUserData() {
    deleteCookie(ATIVISTA_COOKIE);
    deleteCookie(ATIVISTA_CONFIRM_COOKIE);
    deleteCookie(SESSAO_COOKIE);
    deleteCookie(COOKIE_USER_ID);
    deleteCookie(COOKIE_ACTIONS);
    localStorage.removeItem(ACTIONS_STORAGE_KEY);
}

function precisaConfirmarAtivista(intervaloMinutos) {
    const ultimaConfirmacao = getCookie(ATIVISTA_CONFIRM_COOKIE);
    if (!ultimaConfirmacao) {
        return true;
    }
    const agora = Date.now();
    const tempoDecorrido = (agora - parseInt(ultimaConfirmacao)) / (1000 * 60);
    return tempoDecorrido >= intervaloMinutos;
}

// ============================================
// FUNÇÕES DE AÇÕES (LOCALSTORAGE)
// ============================================

function getAcoesFromLocalStorage() {
    try {
        const data = localStorage.getItem(ACTIONS_STORAGE_KEY);
        return data ? JSON.parse(data) : {};
    } catch (e) {
        return {};
    }
}

function saveActionsToLocalStorage(acoes) {
    try {
        localStorage.setItem(ACTIONS_STORAGE_KEY, JSON.stringify(acoes));
    } catch (e) {
        console.warn('Não foi possível salvar no localStorage:', e);
    }
}

// ============================================
// INICIALIZAÇÃO
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Pressão Plugin carregado!');
    console.log('📊 pressaoData:', pressaoData);
    
    document.querySelectorAll('.pressao-widget-container').forEach(function(widget) {
        initWidget(widget);
    });
    
    document.querySelectorAll('.pressao-form-container').forEach(function(form) {
        initForm(form);
    });
    
    document.querySelectorAll('.pressao-list-container').forEach(function(list) {
        initList(list);
    });

    document.querySelectorAll('.pressao-alvos').forEach(function(container) {
        initAlvos(container);
    });
});

// ============================================
// WIDGET
// ============================================

function initWidget(widget) {
    const widgetId = widget.dataset.widgetId;
    const campaignId = widget.dataset.campaign;
    const campaignData = widget.dataset.campaignData;
    const content = widget.querySelector('.pressao-widget-content');
    
    console.log(`Widget inicializado: ${widgetId}`, { campaignId });
    
    if (campaignData && campaignData !== '') {
        try {
            const data = JSON.parse(campaignData);
            if (data && data.nome) {
                updateCampaignName(widget, data.nome);
            }
        } catch (e) {
            console.log('Erro ao processar dados da campanha:', e);
        }
    }
    
    if (campaignId && (!campaignData || campaignData === '')) {
        carregarCampanhaAJAX(widget, campaignId);
    }
    
    if (content) {
        content.dataset.loaded = 'false';
    }
}

function carregarCampanhaAJAX(widget, campaignId) {
    const campaignSpan = widget.querySelector('.pressao-campaign-name');
    const separator = widget.querySelector('.pressao-campaign-separator');
    const loadingSpan = document.createElement('span');
    loadingSpan.className = 'pressao-campaign-loading';
    loadingSpan.textContent = 'carregando...';
    
    if (campaignSpan) {
        campaignSpan.style.display = 'none';
        campaignSpan.parentNode.insertBefore(loadingSpan, campaignSpan);
    }
    
    const data = {
        action: 'pressao_get_campanha',
        campanha_id: campaignId,
        nonce: pressaoData ? pressaoData.nonce : ''
    };
    
    fetch(pressaoData.ajaxUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams(data)
    })
    .then(response => response.json())
    .then(response => {
        if (loadingSpan.parentNode) {
            loadingSpan.remove();
        }
        if (response.success && response.data && response.data.data) {
            const campanha = response.data.data;
            if (campanha.nome) {
                updateCampaignName(widget, campanha.nome);
            }
        } else {
            if (separator) separator.style.display = 'none';
            if (campaignSpan) campaignSpan.style.display = 'none';
        }
    })
    .catch(function(err) {
        console.error('Erro ao carregar campanha:', err);
        if (loadingSpan.parentNode) {
            loadingSpan.remove();
        }
        if (separator) separator.style.display = 'none';
        if (campaignSpan) campaignSpan.style.display = 'none';
    });
}

function updateCampaignName(widget, nome) {
    const campaignSpan = widget.querySelector('.pressao-campaign-name');
    const separator = widget.querySelector('.pressao-campaign-separator');
    if (campaignSpan) {
        campaignSpan.textContent = nome;
        campaignSpan.style.display = 'inline';
    }
    if (separator) {
        separator.style.display = 'inline';
    }
}

function initForm(form) {
    const formId = form.id;
    const campaign = form.dataset.campaign;
    const content = form.querySelector('.pressao-form-content');
    console.log(`Formulário inicializado: ${formId}`, { campaign });
    if (content) {
        content.dataset.loaded = 'false';
    }
}

function initList(list) {
    const listId = list.id;
    const campaign = list.dataset.campaign;
    const limit = list.dataset.limit;
    const content = list.querySelector('.pressao-list-content');
    console.log(`Lista inicializada: ${listId}`, { campaign, limit });
    if (content) {
        content.dataset.loaded = 'false';
    }
}

// ============================================
// ALVOS
// ============================================

function initAlvos(container) {
    console.log('🚀 initAlvos: inicializando container...');
    
    const campaignId = container.dataset.campaign;
    const nonce = container.dataset.nonce;
    const confirmInterval = parseInt(container.dataset.confirmInterval) || 
                           parseInt(pressaoData?.confirmInterval) || 10;
    
    console.log('📋 Config:', { campaignId, nonce, confirmInterval });

    snapshotAlvosActionsUI(container);
    checkActionsStatus(container);
    bindAlvoActionListeners(container);
}

function snapshotAlvosActionsUI(container) {
    container.querySelectorAll('.pressao-alvo-item').forEach(function(item) {
        const actionsDiv = item.querySelector('.pressao-alvo-actions');
        if (actionsDiv && !actionsDiv.dataset.originalHtml) {
            actionsDiv.dataset.originalHtml = actionsDiv.innerHTML;
        }
    });
}

function resetAlvosActionsUI(container) {
    container.querySelectorAll('.pressao-alvo-item').forEach(function(item) {
        item.classList.remove('action-done');
        const actionsDiv = item.querySelector('.pressao-alvo-actions');
        if (actionsDiv && actionsDiv.dataset.originalHtml) {
            actionsDiv.innerHTML = actionsDiv.dataset.originalHtml;
        }
    });
    bindAlvoActionListeners(container);
}

function bindAlvoActionListeners(container) {
    const confirmInterval = parseInt(container.dataset.confirmInterval) ||
                           parseInt(pressaoData?.confirmInterval) || 10;

    container.querySelectorAll('.pressao-action-confirm').forEach(function(button) {
        if (button.dataset.bound === 'true') {
            return;
        }
        button.dataset.bound = 'true';
        button.addEventListener('click', function(e) {
            e.preventDefault();

            const alvoId = this.dataset.alvoId;
            const acaoId = this.dataset.acaoId;
            const campaignId = this.dataset.campaign || container.dataset.campaign;
            const canal = this.dataset.canal || this.closest('.pressao-alvo-item')?.dataset.canal || 'email';

            console.log(`🖱️ .pressao-action-confirm clicado para alvo: ${alvoId}, canal: ${canal}`);

            confirmarAcao(alvoId, acaoId, campaignId, container, this);
        });
    });

    const toggles = container.querySelectorAll('.pressao-action-toggle');
    console.log(`🔘 Encontrados ${toggles.length} botões .pressao-action-toggle`);

    toggles.forEach(function(toggle) {
        if (toggle.dataset.bound === 'true') {
            return;
        }
        toggle.dataset.bound = 'true';
        toggle.addEventListener('click', function(e) {
            e.preventDefault();

            const alvoId = this.dataset.alvoId;
            const campaignId = this.dataset.campaign || container.dataset.campaign;
            const canal = this.dataset.canal || 'email';

            const ativista = getAtivistaData();

            if (!canalRequerAtivista(canal)) {
                realizarAcao(alvoId, campaignId, container, this, null, canal);
                return;
            }

            if (!ativista) {
                const form = this.closest('.pressao-alvo-actions').querySelector('.pressao-ativista-form');
                if (form) {
                    form.style.display = 'block';
                    form.dataset.canal = canal;
                }
            } else if (precisaConfirmarAtivista(confirmInterval)) {
                const toggleRef = this;
                mostrarConfirmacaoAtivista(container, ativista, function() {
                    const submit = toggleRef.closest('.pressao-alvo-actions').querySelector('.pressao-action-submit');
                    if (submit) {
                        submit.click();
                    }
                }, toggleRef);
            } else {
                const submit = this.closest('.pressao-alvo-actions').querySelector('.pressao-action-submit');
                if (submit) {
                    submit.click();
                } else {
                    realizarAcao(alvoId, campaignId, container, this, ativista, canal);
                }
            }
        });
    });

    const submits = container.querySelectorAll('.pressao-action-submit');
    console.log(`🔘 Encontrados ${submits.length} botões .pressao-action-submit`);

    submits.forEach(function(submit) {
        if (submit.dataset.bound === 'true') {
            return;
        }
        submit.dataset.bound = 'true';
        submit.addEventListener('click', function(e) {
            e.preventDefault();

            console.log('🖱️ ===== .pressao-action-submit CLICADO! =====');

            const alvoId = this.dataset.alvoId;
            const campaignId = this.dataset.campaign || container.dataset.campaign;
            const canal = this.dataset.canal ||
            this.closest('.pressao-ativista-form')?.dataset.canal ||
            this.closest('.pressao-alvo-item')?.dataset.canal ||
            'email';
            const form = this.closest('.pressao-ativista-form');

            console.log('🎯 Alvo ID:', alvoId);
            console.log('📢 Campaign ID:', campaignId);

            const ativistaExistente = getAtivistaData();

            if (ativistaExistente && !precisaConfirmarAtivista(10)) {
                console.log('✅ Ativista já existe, executando ação diretamente');
                realizarAcao(alvoId, campaignId, container, this, ativistaExistente, canal);
                return;
            }

            if (!form) {
                console.error('❌ Formulário não encontrado!');
                return;
            }

            const nome = form.querySelector('.pressao-ativista-nome');
            const email = form.querySelector('.pressao-ativista-email');
            const telefone = form.querySelector('.pressao-ativista-telefone');

            console.log('📝 Campos encontrados:');
            console.log('  Nome:', nome ? '✅' : '❌', nome ? nome.value : 'não encontrado');
            console.log('  Email:', email ? '✅' : '❌', email ? email.value : 'não encontrado');
            console.log('  Telefone:', telefone ? '✅' : '❌', telefone ? telefone.value : 'não encontrado');

            if (!nome || !nome.value.trim()) {
                console.log('⚠️ Nome vazio');
                showNotification(container, 'error', 'Por favor, informe seu nome.');
                return;
            }

            const ativista = {
                nome: nome.value.trim(),
                email: email ? email.value.trim() : '',
                telefone: telefone ? telefone.value.trim() : ''
            };

            console.log('📦 Ativista preparado:', ativista);
            console.log('💾 Chamando saveAtivistaData...');

            const saved = saveAtivistaData(ativista);
            console.log('✅ Resultado do save:', saved);

            const verificar = getCookie(ATIVISTA_COOKIE);

            if (!verificar) {
                showNotification(container, 'error', 'Erro ao salvar seus dados. Tente novamente.');
                return;
            }

            if (form) {
                form.style.display = 'none';
                console.log('🗑️ Formulário inline fechado');
            }

            realizarAcao(alvoId, campaignId, container, this, ativista, canal);
        });
    });
}

// ============================================
// MODAL DE CONFIRMAÇÃO (APENAS NOME - LGPD)
// ============================================

function mostrarConfirmacaoAtivista(container, ativista, callback, contextElement) {
    console.log('🔄 Mostrando confirmação para:', ativista.nome);
    
    const message = container.dataset.confirmMessage || 
                   pressaoData?.ativistaConfirmMessage || 
                   'Confirmar identidade';
    const yesText = container.dataset.confirmYes || 
                   pressaoData?.ativistaConfirmYes || 
                   'Sou eu';
    const noText = container.dataset.confirmNo || 
                  pressaoData?.ativistaConfirmNo || 
                  'Não sou eu';
    
    const overlay = document.createElement('div');
    overlay.className = 'pressao-modal-overlay pressao-modal-confirm';
    overlay.id = 'pressao-modal-confirm';
    
    overlay.innerHTML = `
        <div class="pressao-modal pressao-modal-small">
            <div class="pressao-modal-header">
                <h3>${message}</h3>
            </div>
            <div class="pressao-modal-body">
                <div class="pressao-ativista-info">
                    <p><strong>${escapeHtml(ativista.nome)}</strong></p>
                </div>
                <div class="pressao-modal-actions">
                    <button class="pressao-modal-btn pressao-modal-btn-no" id="pressao-confirm-no">
                        ${noText}
                    </button>
                    <button class="pressao-modal-btn pressao-modal-btn-yes" id="pressao-confirm-yes">
                        ${yesText}
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(overlay);
    
    overlay.addEventListener('click', function(e) {
        if (e.target === this) {
            overlay.remove();
        }
    });
    
    overlay.querySelector('#pressao-confirm-no').addEventListener('click', function() {
        console.log('👤 "Não sou eu" clicado');
        const alvoId = contextElement?.dataset.alvoId ||
                       contextElement?.closest('.pressao-alvo-item')?.dataset.alvoId;
        clearPressaoUserData();
        resetAlvosActionsUI(container);
        overlay.remove();
        if (alvoId) {
            const item = container.querySelector(`.pressao-alvo-item[data-alvo-id="${alvoId}"]`);
            const form = item?.querySelector('.pressao-ativista-form');
            if (form) {
                form.style.display = 'block';
            }
        }
    });
    
    overlay.querySelector('#pressao-confirm-yes').addEventListener('click', function() {
        console.log('✅ "Sou eu" clicado');
        setCookie(ATIVISTA_CONFIRM_COOKIE, String(Date.now()), getSessionDuration());
        overlay.remove();
        if (callback && typeof callback === 'function') {
            callback();
        }
    });
}

// ============================================
// AÇÃO PRINCIPAL
// ============================================

function realizarAcao(alvoId, campaignId, container, button, ativista, canal) {
    console.log('🚀 realizarAcao:', { alvoId, campaignId, canal });
    
    if (!ativista) {
        ativista = getAtivistaData();
    }

    // Se não tem canal, tenta buscar do item
    if (!canal) {
        const item = button.closest('.pressao-alvo-item');
        canal = item?.dataset?.canal || 'email';
    }
    
    console.log('📡 Canal sendo usado:', canal);
    
    const nonce = container.dataset.nonce;
    const originalText = button.textContent;
    const templateId = container.dataset.templateId || '';
    
    button.disabled = true;
    button.textContent = 'Processando...';
    
    const data = {
        action: 'pressao_realizar_acao',
        alvo_id: alvoId,
        campanha_id: campaignId,
        canal: canal,
        template_id: templateId,
        nonce: nonce,
        sessao_id: getOrCreateSessaoId(),
        ativista_nome: ativista?.nome || '',
        ativista_email: ativista?.email || '',
        ativista_telefone: ativista?.telefone || ''
    };
    
    fetch(pressaoData.ajaxUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams(data)
    })
    .then(function(response) {
        const contentType = response.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) {
            return response.text().then(function(text) {
                throw new Error('Resposta inválida do servidor (esperado JSON).');
            });
        }
        return response.json();
    })
    .then(function(response) {
        console.log('response', response);
        if (response.success) {
            const acoes = getAcoesFromLocalStorage();
            const apiData = response.data?.data || {};
            const acaoData = {
                timestamp: response.data?.timestamp || Math.floor(Date.now() / 1000),
                user_id: response.data?.user_id || null,
                ativista: ativista || null,
                acao_id: response.data?.acao_id || apiData.acao_id || null,
                status: response.data?.status || apiData.status_atual || 'CONCLUIDA',
            };
            acoes[alvoId] = acaoData;
            saveActionsToLocalStorage(acoes);
            
            if (acaoData.status === 'AGUARDANDO_ACAO_HUMANA') {
                console.log('🔄 Ação aguardando confirmação manual');
                
                const actionsDiv = button.closest('.pressao-alvo-actions');
                mostrarBotaoConfirmacao(actionsDiv, alvoId, acaoData.acao_id, campaignId, container);
                showNotification(container, 'info', 'Ação iniciada! Confirme quando concluir.');
                
            } else {
                console.log('✅ Ação concluída automaticamente');
                
                const item = button.closest('.pressao-alvo-item');
                marcarAcaoRealizada(item, acoes[alvoId]);
                showNotification(container, 'success', response.data?.message || 'Ação realizada!');
                
                const form = button.closest('.pressao-alvo-actions')?.querySelector('.pressao-ativista-form');
                if (form) {
                    form.style.display = 'none';
                }
            }
            
        } else {
            button.disabled = false;
            button.textContent = originalText;
            showNotification(container, 'error', response.data?.message || 'Erro ao realizar ação');
        }
    })
    .catch(function(error) {
        console.error('Erro:', error);
        button.disabled = false;
        button.textContent = originalText;
        showNotification(container, 'error', 'Erro ao realizar ação. Tente novamente.');
    });
}

// ============================================
// CONFIRMAÇÃO DE AÇÃO MANUAL
// ============================================

function confirmarAcao(alvoId, acaoId, campaignId, container, button) {
    console.log('✅ confirmarAcao:', { alvoId, acaoId, campaignId });

    if (!acaoId) {
        showNotification(container, 'error', 'ID da ação não encontrado. Tente agir novamente.');
        return;
    }

    const nonce = container.dataset.nonce;
    const originalText = button.textContent;

    button.disabled = true;
    button.textContent = 'Confirmando...';

    const data = {
        action: 'pressao_confirmar_acao',
        acao_id: acaoId,
        alvo_id: alvoId,
        campanha_id: campaignId || '',
        nonce: nonce
    };

    fetch(pressaoData.ajaxUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams(data)
    })
    .then(function(response) {
        const contentType = response.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) {
            return response.text().then(function() {
                throw new Error('Resposta inválida do servidor (esperado JSON).');
            });
        }
        return response.json();
    })
    .then(function(response) {
        console.log('confirmarAcao response', response);
        if (response.success) {
            const acoes = getAcoesFromLocalStorage();
            acoes[alvoId] = {
                ...(acoes[alvoId] || {}),
                timestamp: response.data?.timestamp || Math.floor(Date.now() / 1000),
                acao_id: acaoId,
                status: response.data?.status || 'CONCLUIDA'
            };
            saveActionsToLocalStorage(acoes);

            const item = button.closest('.pressao-alvo-item');
            marcarAcaoRealizada(item, acoes[alvoId]);
            showNotification(container, 'success', response.data?.message || 'Ação confirmada!');
        } else {
            button.disabled = false;
            button.textContent = originalText;
            showNotification(container, 'error', response.data?.message || 'Erro ao confirmar ação');
        }
    })
    .catch(function(error) {
        console.error('Erro ao confirmar ação:', error);
        button.disabled = false;
        button.textContent = originalText;
        showNotification(container, 'error', 'Erro ao confirmar ação. Tente novamente.');
    });
}

function mostrarBotaoConfirmacao(actionsDiv, alvoId, acaoId, campaignId, container) {
    if (!actionsDiv) {
        return;
    }

    actionsDiv.innerHTML = `
        <button type="button"
                class="pressao-action-confirm"
                data-alvo-id="${alvoId}"
                data-acao-id="${acaoId || ''}"
                data-campaign="${campaignId || ''}">
            Confirmar ação ✓
        </button>
        <span class="pressao-action-pending" style="font-size:12px;color:#856404;display:block;">
            Aguardando confirmação manual
        </span>
    `;

    const confirmBtn = actionsDiv.querySelector('.pressao-action-confirm');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', function(e) {
            e.preventDefault();
            confirmarAcao(
                this.dataset.alvoId,
                this.dataset.acaoId,
                this.dataset.campaign || container.dataset.campaign,
                container,
                this
            );
        });
    }
}

// ============================================
// FUNÇÕES AUXILIARES
// ============================================

function checkActionsStatus(container) {
    const alvoItems = container.querySelectorAll('.pressao-alvo-item');
    const acoes = getAcoesFromLocalStorage();
    alvoItems.forEach(function(item) {
        const alvoId = item.dataset.alvoId;
        const acao = acoes[alvoId];
        if (!acao) {
            return;
        }

        if (acao.status === 'AGUARDANDO_ACAO_HUMANA' && acao.acao_id) {
            mostrarBotaoConfirmacao(
                item.querySelector('.pressao-alvo-actions'),
                alvoId,
                acao.acao_id,
                container.dataset.campaign,
                container
            );
            return;
        }

        marcarAcaoRealizada(item, acao);
    });
}

function marcarAcaoRealizada(item, actionData) {
    const actionsDiv = item.querySelector('.pressao-alvo-actions');
    if (!actionsDiv) return;
    const timestamp = actionData.timestamp || actionData;
    const timeText = formatActionTime(timestamp);
    const doneLabel = pressaoData?.actionDoneLabel || 'Ação realizada ✓';
    actionsDiv.innerHTML = `
        <span class="pressao-action-done">
            ${doneLabel}
            <span class="pressao-action-time">${timeText}</span>
        </span>
    `;
    item.classList.add('action-done');
}

function formatActionTime(timestamp) {
    const now = Math.floor(Date.now() / 1000);
    const diff = now - timestamp;
    if (diff < 60) return 'agora';
    if (diff < 3600) {
        const minutes = Math.floor(diff / 60);
        return minutes + ' min' + (minutes > 1 ? 's' : '');
    }
    if (diff < 86400) {
        const hours = Math.floor(diff / 3600);
        return hours + ' h' + (hours > 1 ? 's' : '');
    }
    const days = Math.floor(diff / 86400);
    return days + ' d' + (days > 1 ? 's' : '');
}

function showNotification(container, type, message) {
    const oldNotifications = container.querySelectorAll('.pressao-notification');
    oldNotifications.forEach(function(el) { el.remove(); });
    const notification = document.createElement('div');
    notification.className = 'pressao-notification pressao-notification-' + type;
    notification.textContent = message;
    container.prepend(notification);
    setTimeout(function() {
        notification.style.opacity = '0';
        setTimeout(function() { notification.remove(); }, 300);
    }, 4000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}