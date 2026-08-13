/**
 * Pressão Plugin - JavaScript
 * Com carregamento dinâmico da campanha via AJAX
 */

// Constantes
const ACTIVIST_STORAGE_KEY = 'pressao_ativista_data';
const ACTIVIST_LAST_CONFIRM_KEY = 'pressao_ativista_last_confirm';

// ============================================
// FUNÇÕES DO ATIVISTA
// ============================================

function getAtivistaData() {
    try {
        const data = localStorage.getItem(ACTIVIST_STORAGE_KEY);
        console.log('🔍 getAtivistaData:', data);
        return data ? JSON.parse(data) : null;
    } catch (e) {
        console.error('❌ Erro no getAtivistaData:', e);
        return null;
    }
}

function saveAtivistaData(ativista) {
    console.log('💾 saveAtivistaData chamado com:', ativista);
    try {
        localStorage.setItem(ACTIVIST_STORAGE_KEY, JSON.stringify(ativista));
        localStorage.setItem(ACTIVIST_LAST_CONFIRM_KEY, String(Date.now()));
        console.log('✅ saveAtivistaData: dados salvos!');
        console.log('🔍 Verificando:', localStorage.getItem(ACTIVIST_STORAGE_KEY));
        return true;
    } catch (e) {
        console.error('❌ Erro no saveAtivistaData:', e);
        return false;
    }
}

function clearAtivistaData() {
    console.log('🧹 clearAtivistaData: limpando...');
    localStorage.removeItem(ACTIVIST_STORAGE_KEY);
    localStorage.removeItem(ACTIVIST_LAST_CONFIRM_KEY);
}

function precisaConfirmarAtivista(intervaloMinutos) {
    const ultimaConfirmacao = localStorage.getItem(ACTIVIST_LAST_CONFIRM_KEY);
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
        const data = localStorage.getItem('pressao_acoes_realizadas');
        return data ? JSON.parse(data) : {};
    } catch (e) {
        return {};
    }
}

function saveActionsToLocalStorage(acoes) {
    try {
        localStorage.setItem('pressao_acoes_realizadas', JSON.stringify(acoes));
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
    
    // Verifica o estado das ações ao carregar
    checkActionsStatus(container);
    
    // ============================================
    // BOTÃO DE AÇÃO (AGORA É O TOGGLE)
    // ============================================
    const toggles = container.querySelectorAll('.pressao-action-toggle');
    console.log(`🔘 Encontrados ${toggles.length} botões .pressao-action-toggle`);
    
    toggles.forEach(function(toggle) {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            
            const alvoId = this.dataset.alvoId;
            const campaignId = this.dataset.campaign || container.dataset.campaign;
            
            console.log(`🖱️ .pressao-action-toggle clicado para alvo: ${alvoId}`);
            
            // Verifica se tem ativista
            const ativista = getAtivistaData();
            console.log('👤 Ativista atual:', ativista);
            
            if (!ativista) {
                // Não tem dados → mostra formulário inline
                console.log('⚠️ Sem ativista, mostrando formulário inline...');
                const form = this.closest('.pressao-alvo-actions').querySelector('.pressao-ativista-form');
                if (form) {
                    form.style.display = 'block';
                }
            } else if (precisaConfirmarAtivista(confirmInterval)) {
                // Precisa confirmar → mostra modal de confirmação
                console.log('🔄 Precisa confirmar identidade');
                const toggleRef = this;
                mostrarConfirmacaoAtivista(container, ativista, function() {
                    console.log('✅ Confirmado! Executando ação...');
                    // Busca o submit para executar a ação
                    const submit = toggleRef.closest('.pressao-alvo-actions').querySelector('.pressao-action-submit');
                    if (submit) {
                        submit.click();
                    }
                });
            } else {
                // Tudo certo → executa ação diretamente
                console.log('✅ Tudo certo, executando ação...');
                // Busca o submit para executar a ação
                const submit = this.closest('.pressao-alvo-actions').querySelector('.pressao-action-submit');
                if (submit) {
                    submit.click();
                } else {
                    // Fallback: executa ação diretamente
                    realizarAcao(alvoId, campaignId, container, this, ativista);
                }
            }
        });
    });
    
    // ============================================
    // SUBMIT DO FORMULÁRIO INLINE
    // ============================================
    const submits = container.querySelectorAll('.pressao-action-submit');
    console.log(`🔘 Encontrados ${submits.length} botões .pressao-action-submit`);
    
    submits.forEach(function(submit) {
        submit.addEventListener('click', function(e) {
            e.preventDefault();
            
            console.log('🖱️ ===== .pressao-action-submit CLICADO! =====');
            
            const alvoId = this.dataset.alvoId;
            const campaignId = this.dataset.campaign || container.dataset.campaign;
            const form = this.closest('.pressao-ativista-form');
            const actionsDiv = this.closest('.pressao-alvo-actions');
            
            console.log('🎯 Alvo ID:', alvoId);
            console.log('📢 Campaign ID:', campaignId);
            
            // Verifica se já tem ativista
            const ativistaExistente = getAtivistaData();
            
            if (ativistaExistente && !precisaConfirmarAtivista(10)) {
                // Já tem ativista e está confirmado → executa ação diretamente
                console.log('✅ Ativista já existe, executando ação diretamente');
                realizarAcao(alvoId, campaignId, container, this, ativistaExistente);
                return;
            }
            
            if (!form) {
                console.error('❌ Formulário não encontrado!');
                return;
            }
            
            // Coleta dados do ativista
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
            
            // PREPARA E SALVA O ATIVISTA
            const ativista = {
                nome: nome.value.trim(),
                email: email ? email.value.trim() : '',
                telefone: telefone ? telefone.value.trim() : ''
            };
            
            console.log('📦 Ativista preparado:', ativista);
            console.log('💾 Chamando saveAtivistaData...');
            
            const saved = saveAtivistaData(ativista);
            console.log('✅ Resultado do save:', saved);
            
            const verificar = localStorage.getItem('pressao_ativista_data');
            console.log('🔍 Verificando localStorage:', verificar);
            
            if (!verificar) {
                console.error('❌ Dados NÃO foram salvos!');
                showNotification(container, 'error', 'Erro ao salvar seus dados. Tente novamente.');
                return;
            }
            
            console.log('✅ Dados confirmados no localStorage!');
            
            // Fecha o formulário inline
            if (form) {
                form.style.display = 'none';
                console.log('🗑️ Formulário inline fechado');
            }
            
            // Executa a ação
            realizarAcao(alvoId, campaignId, container, this, ativista);
        });
    });
}

// ============================================
// MODAL DE CONFIRMAÇÃO (APENAS NOME - LGPD)
// ============================================

function mostrarConfirmacaoAtivista(container, ativista, callback) {
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
        clearAtivistaData();
        overlay.remove();
        // Mostra formulário inline novamente
        const alvoId = container.querySelector('.pressao-action-toggle')?.dataset.alvoId;
        if (alvoId) {
            const form = container.querySelector(`.pressao-ativista-form[data-alvo-id="${alvoId}"]`);
            if (form) {
                form.style.display = 'block';
            }
        }
    });
    
    overlay.querySelector('#pressao-confirm-yes').addEventListener('click', function() {
        console.log('✅ "Sou eu" clicado');
        localStorage.setItem(ACTIVIST_LAST_CONFIRM_KEY, String(Date.now()));
        overlay.remove();
        if (callback && typeof callback === 'function') {
            callback();
        }
    });
}

// ============================================
// AÇÃO PRINCIPAL
// ============================================

function realizarAcao(alvoId, campaignId, container, button, ativista) {
    console.log('🚀 realizarAcao:', { alvoId, campaignId });
    
    if (!ativista) {
        ativista = getAtivistaData();
        console.log('📦 Ativista do localStorage:', ativista);
    }
    
    if (!ativista) {
        console.log('❌ Nenhum ativista encontrado');
        const form = container.querySelector(`.pressao-ativista-form[data-alvo-id="${alvoId}"]`);
        if (form) {
            form.style.display = 'block';
        }
        return;
    }
    
    console.log('✅ Ativista encontrado:', ativista);
    
    const nonce = container.dataset.nonce;
    const originalText = button.textContent;
    const canal = container.dataset.canal || 'email';
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
        ativista_nome: ativista.nome || '',
        ativista_email: ativista.email || '',
        ativista_telefone: ativista.telefone || ''
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
        if (response.success) {
            const acoes = getAcoesFromLocalStorage();
            acoes[alvoId] = {
                timestamp: response.data?.timestamp || Math.floor(Date.now() / 1000),
                user_id: response.data?.user_id || null,
                ativista: ativista || null
            };
            saveActionsToLocalStorage(acoes);
            
            const item = button.closest('.pressao-alvo-item');
            marcarAcaoRealizada(item, acoes[alvoId]);
            showNotification(container, 'success', response.data?.message || 'Ação realizada!');
            
            const form = button.closest('.pressao-alvo-actions')?.querySelector('.pressao-ativista-form');
            if (form) {
                form.style.display = 'none';
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
// FUNÇÕES AUXILIARES
// ============================================

function checkActionsStatus(container) {
    const alvoItems = container.querySelectorAll('.pressao-alvo-item');
    const acoes = getAcoesFromLocalStorage();
    alvoItems.forEach(function(item) {
        const alvoId = item.dataset.alvoId;
        if (acoes[alvoId]) {
            marcarAcaoRealizada(item, acoes[alvoId]);
        }
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