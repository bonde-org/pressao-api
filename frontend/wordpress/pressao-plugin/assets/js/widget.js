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