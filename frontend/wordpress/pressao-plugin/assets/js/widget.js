/**
 * Pressão Plugin - JavaScript
 * Com carregamento dinâmico da campanha via AJAX
 */
document.addEventListener('DOMContentLoaded', function() {
    // Inicializa widgets
    const widgets = document.querySelectorAll('.pressao-widget-container');
    widgets.forEach(function(widget) {
        initWidget(widget);
    });
    
    // Inicializa formulários
    const forms = document.querySelectorAll('.pressao-form-container');
    forms.forEach(function(form) {
        initForm(form);
    });
    
    // Inicializa listas
    const lists = document.querySelectorAll('.pressao-list-container');
    lists.forEach(function(list) {
        initList(list);
    });

    const alvosContainers = document.querySelectorAll('.pressao-alvos');
    alvosContainers.forEach(function(container) {
        initAlvos(container);
    });
});

/**
 * Inicializa um widget
 */
function initWidget(widget) {
    const widgetId = widget.dataset.widgetId;
    const campaignId = widget.dataset.campaign;
    const campaignData = widget.dataset.campaignData;
    const content = widget.querySelector('.pressao-widget-content');
    
    console.log(`Widget inicializado: ${widgetId}`, { campaignId });
    
    // Se temos dados da campanha via shortcode (já carregados)
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
    
    // Se não temos dados mas temos ID, carrega via AJAX
    if (campaignId && (!campaignData || campaignData === '')) {
        carregarCampanhaAJAX(widget, campaignId);
    }
    
    if (content) {
        content.dataset.loaded = 'false';
    }
}

/**
 * Carrega campanha via AJAX
 */
function carregarCampanhaAJAX(widget, campaignId) {
    const campaignSpan = widget.querySelector('.pressao-campaign-name');
    const separator = widget.querySelector('.pressao-campaign-separator');
    const loadingSpan = document.createElement('span');
    loadingSpan.className = 'pressao-campaign-loading';
    loadingSpan.textContent = 'carregando...';
    
    // Adiciona loading
    if (campaignSpan) {
        campaignSpan.style.display = 'none';
        campaignSpan.parentNode.insertBefore(loadingSpan, campaignSpan);
    }
    
    // Dados para AJAX
    const data = {
        action: 'pressao_get_campanha',
        campanha_id: campaignId,
        nonce: pressaoData ? pressaoData.nonce : ''
    };
    
    // Faz requisição
    fetch(pressaoData.ajaxUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams(data)
    })
    .then(response => response.json())
    .then(response => {
        // Remove loading
        if (loadingSpan.parentNode) {
            loadingSpan.remove();
        }
        
        if (response.success && response.data && response.data.data) {
            const campanha = response.data.data;
            if (campanha.nome) {
                updateCampaignName(widget, campanha.nome);
            }
        } else {
            // Esconde separador e nome se não tiver campanha
            if (separator) separator.style.display = 'none';
            if (campaignSpan) campaignSpan.style.display = 'none';
        }
    })
    .catch(function(err) {
        console.error('Erro ao carregar campanha:', err);
        // Remove loading
        if (loadingSpan.parentNode) {
            loadingSpan.remove();
        }
        // Esconde separador e nome
        if (separator) separator.style.display = 'none';
        if (campaignSpan) campaignSpan.style.display = 'none';
    });
}

/**
 * Atualiza o nome da campanha no widget
 */
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

/**
 * Inicializa um formulário
 */
function initForm(form) {
    const formId = form.id;
    const campaign = form.dataset.campaign;
    const content = form.querySelector('.pressao-form-content');
    
    console.log(`Formulário inicializado: ${formId}`, { campaign });
    
    if (content) {
        content.dataset.loaded = 'false';
    }
}

/**
 * Inicializa uma lista
 */
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

/**
 * Função para carregar conteúdo dinâmico (API)
 */
function loadWidgetContent(widgetId) {
    console.log(`Carregando conteúdo para: ${widgetId}`);
}

/**
 * Função para enviar dados do formulário
 */
function submitFormData(formId, data) {
    console.log(`Enviando dados do formulário: ${formId}`, data);
}

/**
 * Função para carregar lista de dados
 */
function loadListData(listId) {
    console.log(`Carregando lista: ${listId}`);
}

/**
 * Inicializa um container de alvos
 */
function initAlvos(container) {
    const campaignId = container.dataset.campaign;
    const nonce = container.dataset.nonce;
    
    // Verifica o estado das ações ao carregar
    checkActionsStatus(container);
    
    // Botões de ação simples
    const buttons = container.querySelectorAll('.pressao-action-button');
    buttons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const alvoId = this.dataset.alvoId;
            const campaignId = this.dataset.campaign || container.dataset.campaign;
            
            // Ação anônima (sem dados do ativista)
            realizarAcao(alvoId, campaignId, container, this, null);
        });
    });
    
    // Toggle do formulário de ativista
    const toggles = container.querySelectorAll('.pressao-action-toggle');
    toggles.forEach(function(toggle) {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            
            const form = this.closest('.pressao-alvo-actions').querySelector('.pressao-ativista-form');
            if (form) {
                form.style.display = form.style.display === 'none' ? 'block' : 'none';
            }
        });
    });
    
    // Submit do formulário de ativista
    const submits = container.querySelectorAll('.pressao-action-submit');
    submits.forEach(function(submit) {
        submit.addEventListener('click', function(e) {
            e.preventDefault();
            
            const alvoId = this.dataset.alvoId;
            const campaignId = this.dataset.campaign || container.dataset.campaign;
            const item = this.closest('.pressao-alvo-item');
            const form = this.closest('.pressao-ativista-form');
            
            // Coleta dados do ativista
            const nome = form.querySelector('.pressao-ativista-nome');
            const email = form.querySelector('.pressao-ativista-email');
            const telefone = form.querySelector('.pressao-ativista-telefone');
            
            // Validação básica
            if (!nome || !nome.value.trim()) {
                showNotification(container, 'error', 'Por favor, informe seu nome.');
                return;
            }
            
            // Prepara dados do ativista
            const ativista = {
                nome: nome.value.trim(),
                email: email ? email.value.trim() : '',
                telefone: telefone ? telefone.value.trim() : ''
            };
            
            // Ação com ativista
            realizarAcao(alvoId, campaignId, container, this, ativista);
        });
    });
}

/**
 * Verifica o status das ações para todos os alvos
 */
function checkActionsStatus(container) {
    const alvoItems = container.querySelectorAll('.pressao-alvo-item');
    const alvosIds = Array.from(alvoItems).map(function(item) {
        return item.dataset.alvoId;
    });
    
    if (alvosIds.length === 0) return;
    
    // Verifica localStorage primeiro
    const acoes = getAcoesFromLocalStorage();
    
    // Atualiza UI baseado no localStorage
    alvoItems.forEach(function(item) {
        const alvoId = item.dataset.alvoId;
        if (acoes[alvoId]) {
            marcarAcaoRealizada(item, acoes[alvoId]);
        }
    });
    
    // Opcional: Sincroniza com o servidor
    syncActionsWithServer(alvosIds, container);
}

/**
 * Obtém ações do localStorage
 */
function getAcoesFromLocalStorage() {
    try {
        const data = localStorage.getItem('pressao_acoes_realizadas');
        return data ? JSON.parse(data) : {};
    } catch (e) {
        return {};
    }
}

/**
 * Salva ações no localStorage
 */
function saveActionsToLocalStorage(acoes) {
    try {
        localStorage.setItem('pressao_acoes_realizadas', JSON.stringify(acoes));
    } catch (e) {
        console.warn('Não foi possível salvar no localStorage:', e);
    }
}

/**
 * Realiza uma ação para um alvo
 */
function realizarAcao(alvoId, campaignId, container, button, ativista) {
    const nonce = container.dataset.nonce;
    const originalText = button.textContent;
    const canal = container.dataset.canal || 'email';
    const templateId = container.dataset.templateId || '';
    
    // Desabilita botão
    button.disabled = true;
    button.textContent = 'Processando...';
    
    // Dados para o AJAX
    const data = {
        action: 'pressao_realizar_acao',
        alvo_id: alvoId,
        campanha_id: campaignId,
        canal: canal,
        template_id: templateId,
        nonce: nonce
    };
    
    // Adiciona dados do ativista se fornecidos
    if (ativista) {
        data.ativista_nome = ativista.nome;
        data.ativista_email = ativista.email || '';
        data.ativista_telefone = ativista.telefone || '';
    }
    
    // Faz requisição
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
            // Salva no localStorage
            const acoes = getAcoesFromLocalStorage();
            acoes[alvoId] = {
                timestamp: response.data.timestamp || Math.floor(Date.now() / 1000),
                user_id: response.data.user_id || null,
                ativista: ativista || null
            };
            saveActionsToLocalStorage(acoes);
            
            // Atualiza UI
            const item = button.closest('.pressao-alvo-item');
            marcarAcaoRealizada(item, acoes[alvoId]);
            
            // Mostra feedback
            showNotification(container, 'success', response.data.message || 'Ação realizada!');
            
            // Fecha formulário se estiver aberto
            const form = button.closest('.pressao-alvo-actions')?.querySelector('.pressao-ativista-form');
            if (form) {
                form.style.display = 'none';
            }
        } else {
            // Restaura botão
            button.disabled = false;
            button.textContent = originalText;
            
            showNotification(container, 'error', response.data.message || 'Erro ao realizar ação');
        }
    })
    .catch(function(error) {
        console.error('Erro:', error);
        button.disabled = false;
        button.textContent = originalText;
        showNotification(container, 'error', 'Erro ao realizar ação. Tente novamente.');
    });
}

/**
 * Marca um alvo como ação realizada
 */
function marcarAcaoRealizada(item, actionData) {
    const actionsDiv = item.querySelector('.pressao-alvo-actions');
    if (!actionsDiv) return;
    
    const timestamp = actionData.timestamp || actionData;
    const timeText = formatActionTime(timestamp);
    
    // Substitui botão pelo status
    actionsDiv.innerHTML = `
        <span class="pressao-action-done">
            Ação realizada ✓
            <span class="pressao-action-time">${timeText}</span>
        </span>
    `;
    
    // Adiciona classe
    item.classList.add('action-done');
}

/**
 * Sincroniza ações com o servidor (opcional)
 */
function syncActionsWithServer(alvosIds, container) {
    // Pega ações do localStorage
    const acoes = getAcoesFromLocalStorage();
    const acoesAlvos = Object.keys(acoes);
    
    // Verifica se algum alvo tem ação no localStorage mas não no servidor
    const alvosParaSincronizar = alvosIds.filter(function(id) {
        return acoesAlvos.includes(id);
    });
    
    if (alvosParaSincronizar.length === 0) return;
    
    // TODO: Sincronizar com o servidor se necessário
    // Por enquanto, apenas usa o localStorage
}

/**
 * Formata o tempo da ação para exibição
 */
function formatActionTime(timestamp) {
    const now = Math.floor(Date.now() / 1000);
    const diff = now - timestamp;
    
    if (diff < 60) {
        return 'agora';
    } else if (diff < 3600) {
        const minutes = Math.floor(diff / 60);
        return minutes + ' min' + (minutes > 1 ? 's' : '');
    } else if (diff < 86400) {
        const hours = Math.floor(diff / 3600);
        return hours + ' h' + (hours > 1 ? 's' : '');
    } else {
        const days = Math.floor(diff / 86400);
        return days + ' d' + (days > 1 ? 's' : '');
    }
}

/**
 * Mostra notificação na interface
 */
function showNotification(container, type, message) {
    // Remove notificações anteriores
    const oldNotifications = container.querySelectorAll('.pressao-notification');
    oldNotifications.forEach(function(el) {
        el.remove();
    });
    
    // Cria nova notificação
    const notification = document.createElement('div');
    notification.className = 'pressao-notification pressao-notification-' + type;
    notification.textContent = message;
    
    container.prepend(notification);
    
    // Remove após alguns segundos
    setTimeout(function() {
        notification.style.opacity = '0';
        setTimeout(function() {
            notification.remove();
        }, 300);
    }, 4000);
}