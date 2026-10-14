/**
 * Widget padrão multicanal ([pressao_multicanal]).
 * Depende de window.PressaoCore (pressao-core.js).
 */
(function () {
    'use strict';

    var Core = window.PressaoCore;
    if (!Core) {
        return;
    }

    var esc = Core.escapeHtml;
    var escAttr = Core.escapeAttr;

    var NAOUSO_PREFIX = '__naouso_';
    var LEAD_KEY = '__lead';
    var SHARE_KEY = '__compartilhar';
    var FEEDBACK_MS = 1000;
    var ABRIR_SEM_CONTAGEM_MS = 1500;
    var TRANSICAO_MS = 280;
    var CHIPS_VISIVEIS = 3;
    var DESKTOP_MQ = window.matchMedia('(min-width: 768px)');

    var CANAL_TEXTOS = {
        instagram: {
            nome: 'Instagram',
            dica: 'É só colar nos comentários da publicação da campanha no Instagram.',
            nota: 'O comentário será publicado com seu perfil do Instagram',
            copiar: 'Copiar e abrir no Instagram',
            naoUso: 'Não uso Instagram',
            passo: 'Copiar o texto e abrir Instagram',
            pergunta: 'Tudo certo com o seu comentário?'
        },
        tiktok: {
            nome: 'TikTok',
            dica: 'É só colar nos comentários do vídeo da campanha no TikTok.',
            nota: 'O comentário será publicado com seu perfil do TikTok',
            copiar: 'Copiar e abrir no TikTok',
            naoUso: 'Não uso TikTok',
            passo: 'Copiar o texto e abrir TikTok',
            pergunta: 'Tudo certo com o seu comentário?'
        },
        email: {
            nome: 'Email',
            naoUso: 'Não uso email'
        },
        telefone: {
            nome: 'Telefone'
        }
    };

    var LIGACAO_STORAGE_PREFIX = 'pressao_mc_ligacao_';
    var LIGACAO_POLL_MS = 2000;
    var LIGACAO_POLL_LENTO_MS = 5000;
    var LIGACAO_POLL_LENTO_APOS_MS = 60000;
    var LIGACAO_FECHAR_APOS_MS = 90000;
    var SEU_NOME = '[seu nome]';

    /** Textos das telas de erro do Figma por origem/motivo da falha. */
    function erroLigacaoTextos(origem, motivo, alvoNome) {
        var alvo = alvoNome || 'o alvo';
        if (origem === 'alvo' && motivo === 'no-answer') {
            return {
                titulo: 'Ninguém atendeu a ligação',
                texto: 'Não conseguimos contato com ' + alvo + '. Você pode aguardar alguns minutos e tentar novamente a qualquer momento.',
                doAlvo: true
            };
        }
        if (origem === 'alvo' && motivo === 'busy') {
            return {
                titulo: 'A linha estava ocupada',
                texto: 'Não conseguimos completar a ligação porque o número de ' + alvo + ' estava ocupado. Você pode aguardar alguns minutos e tentar novamente mais tarde.',
                doAlvo: true
            };
        }
        if (origem === 'ativista' && motivo === 'no-answer') {
            return {
                titulo: 'A ligação não foi atendida',
                texto: 'Tentamos te ligar, mas a chamada não foi atendida. Mas tudo bem, você pode iniciar a ligação novamente a qualquer momento.'
            };
        }
        if (origem === 'ativista' && motivo === 'canceled') {
            return {
                titulo: 'A ligação foi interrompida',
                texto: 'Isso pode acontecer por instabilidade na rede ou encerramento da chamada. Mas tudo bem, você pode tentar novamente a qualquer momento.'
            };
        }
        return {
            titulo: 'A ligação não foi completada',
            texto: 'Isso pode acontecer por instabilidade na rede ou número incorreto. Confirme seu número abaixo e tente novamente.'
        };
    }

    function telefoneValido(digitos) {
        return digitos.length === 10 || digitos.length === 11;
    }

    // ------------------------------------------------------------------
    // Helpers de markup (sem estado)
    // ------------------------------------------------------------------

    function ico(nome) {
        return '<span class="pressao-mc-ico pressao-mc-ico--' + escAttr(nome) + '" aria-hidden="true"></span>';
    }

    function avatarHtml(imagem, extraClass) {
        var cls = 'pressao-mc-chip-avatar' + (extraClass ? ' ' + extraClass : '');
        return imagem
            ? '<span class="' + cls + '" style="background-image:url(\'' + escAttr(imagem) + '\')"></span>'
            : '<span class="' + cls + ' is-empty"></span>';
    }

    /** Chips com os N primeiros visíveis e um botão "+N" / "Mostrar +N" que expande e recolhe. */
    function chipsHtml(itens) {
        var extra = Math.max(0, itens.length - CHIPS_VISIVEIS);
        var chips = itens
            .map(function (item, i) {
                return (
                    '<span class="pressao-mc-chip' + (i >= CHIPS_VISIVEIS ? ' is-extra' : '') + '">' +
                    avatarHtml(item.imagem) +
                    '<span class="pressao-mc-chip-label">' + esc(item.label) + '</span></span>'
                );
            })
            .join('');
        var toggle = extra > 0
            ? '<button type="button" class="pressao-mc-chips-toggle" data-mc-chips-toggle aria-expanded="false">' +
              '<span class="pressao-mc-chips-more">' +
              '<span class="pressao-mc-mobile-only">+' + extra + '</span>' +
              '<span class="pressao-mc-desktop-only">Mostrar +' + extra + '</span></span>' +
              '<span class="pressao-mc-chips-less">Mostrar menos</span></button>'
            : '';
        return '<div class="pressao-mc-chips" data-mc-chips>' + chips + toggle + '</div>';
    }

    function progressHtml(feitos, total, variante) {
        var pct = total > 0 ? Math.min(100, Math.round((feitos / total) * 100)) : 0;
        return (
            '<div class="pressao-mc-progress' + (variante ? ' pressao-mc-progress--' + variante : '') + '" data-mc-progress>' +
            '<div class="pressao-mc-progress-head">' +
            '<span class="pressao-mc-progress-label">Etapas que você já fez</span>' +
            '<span class="pressao-mc-progress-value"><span class="pressao-mc-raio" aria-hidden="true"></span>' +
            '<span data-mc-progress-text>' + feitos + ' de ' + total + '</span></span></div>' +
            '<div class="pressao-mc-progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="' + total +
            '" aria-valuenow="' + feitos + '" data-mc-progress-bar>' +
            '<span class="pressao-mc-progress-fill" style="width:' + pct + '%" data-mc-progress-fill></span></div></div>'
        );
    }

    function modalHeaderHtml(titulo, dismissable) {
        return (
            '<header class="pressao-mc-modal-header">' +
            '<h3 class="pressao-mc-modal-title">' + esc(titulo) + '</h3>' +
            (dismissable === false
                ? ''
                : '<button type="button" class="pressao-mc-icon-btn" data-mc-close-modal aria-label="Fechar">' + ico('fechar') + '</button>') +
            '</header>'
        );
    }

    function feedbackHtml(titulo, texto, extraHtml) {
        return (
            '<div class="pressao-mc-feedback">' +
            '<span class="pressao-mc-feedback-icon" aria-hidden="true">' + ico('check') + '</span>' +
            '<h3 class="pressao-mc-feedback-title">' + esc(titulo) + '</h3>' +
            (texto ? '<p class="pressao-mc-feedback-text" data-mc-feedback-text>' + esc(texto) + '</p>' : '') +
            '</div>' +
            (extraHtml || '')
        );
    }

    function camposAtivistaHtml(ativista) {
        ativista = ativista || {};
        function value(v) {
            return v ? ' value="' + escAttr(v) + '"' : '';
        }
        return (
            '<label class="pressao-mc-field"><span class="pressao-mc-field-label">Nome <span class="pressao-mc-required">*</span></span>' +
            '<input type="text" name="nome" required autocomplete="name" placeholder="Seu nome"' + value(ativista.nome) + ' /></label>' +
            '<label class="pressao-mc-field"><span class="pressao-mc-field-label">Email <span class="pressao-mc-required">*</span></span>' +
            '<input type="email" name="email" required autocomplete="email" placeholder="Seu melhor email"' + value(ativista.email) + ' /></label>' +
            '<label class="pressao-mc-field"><span class="pressao-mc-field-label">Whatsapp (opcional)</span>' +
            '<input type="tel" name="telefone" inputmode="numeric" autocomplete="tel" placeholder="(00) 00000-0000" data-mc-telefone' +
            value(ativista.telefone ? Core.formatPhoneMask(ativista.telefone) : '') + ' /></label>'
        );
    }

    /** Lê e valida nome/e-mail/telefone de um form. Retorna { ativista } ou { erro }. */
    function lerAtivista(form) {
        var nome = (form.elements.nome.value || '').trim();
        var email = (form.elements.email.value || '').trim();
        var telefone = Core.digitsOnly(form.elements.telefone.value || '');
        if (!nome || !email) {
            return { erro: 'Preencha nome e email.' };
        }
        if (!Core.isEmailValido(email)) {
            return { erro: 'Informe um email válido.' };
        }
        return { ativista: { nome: nome, email: email, telefone: telefone } };
    }

    /** Lê e valida o formulário de telefone. Telefone com DDD obrigatório; e-mail conforme `emailCampo`. */
    function lerAtivistaTelefone(form, emailCampo) {
        var nome = (form.elements.nome.value || '').trim();
        var telefone = Core.digitsOnly(form.elements.telefone.value || '');
        var email = form.elements.email ? (form.elements.email.value || '').trim() : '';
        if (!nome) {
            return { erro: 'Preencha seu nome.' };
        }
        if (!telefoneValido(telefone)) {
            return { erro: 'Informe seu telefone com DDD.' };
        }
        if (emailCampo === 'obrigatorio' && !email) {
            return { erro: 'Preencha seu email.' };
        }
        if (email && !Core.isEmailValido(email)) {
            return { erro: 'Informe um email válido.' };
        }
        return { ativista: { nome: nome, email: email, telefone: telefone } };
    }

    function cargoPartido(membro) {
        return [membro && membro.cargo, membro && membro.partido].filter(Boolean).join(' · ');
    }

    function textoParaExibicao(texto) {
        return String(texto || '').replace(/\{alvo_nome\}/g, '[nome do destinatário]');
    }

    // ------------------------------------------------------------------
    // Widget
    // ------------------------------------------------------------------

    function Widget(root) {
        var config;
        try {
            config = JSON.parse(root.getAttribute('data-pressao-mc') || '{}');
        } catch (e) {
            return;
        }

        var canais = Array.isArray(config.canais) ? config.canais : [];
        var canaisPorId = {};
        canais.forEach(function (c) {
            canaisPorId[c.canal] = c;
        });
        var candidatos = Array.isArray(config.candidatos) ? config.candidatos : [];
        var campanhaNome = config.campanha_nome || 'campanha';

        var panel = root.querySelector('[data-mc-panel]');
        var home = root.querySelector('[data-mc-home]');
        var screen = root.querySelector('[data-mc-screen]');
        var modal = root.querySelector('[data-mc-modal]');
        var dialog = root.querySelector('[data-mc-modal-dialog]');

        var modalStack = [];
        var screenCanal = null;
        var focoAoFecharTela = null;
        var aoFecharTela = null;

        // ---------------- Estado (cookie) ----------------

        function canalState(canal) {
            var c = canaisPorId[canal];
            if (!c) {
                return '';
            }
            var actions = Core.readActions();
            if (Core.isAcaoRealizada(actions[c.alvo_id])) {
                return 'done';
            }
            if (actions[NAOUSO_PREFIX + canal]) {
                return 'skipped';
            }
            return '';
        }

        function progresso() {
            var feitos = 0;
            var total = 0;
            canais.forEach(function (c) {
                var s = canalState(c.canal);
                if (s !== 'skipped') {
                    total++;
                }
                if (s === 'done') {
                    feitos++;
                }
            });
            return { feitos: feitos, total: total };
        }

        function pendentes(excluir) {
            return canais.filter(function (c) {
                return c.canal !== excluir && canalState(c.canal) === '';
            });
        }

        function proximoCanal(excluir) {
            var lista = pendentes(excluir);
            return lista.length ? lista[0] : null;
        }

        function marcarNaoUso(canal) {
            Core.saveActionCookie(NAOUSO_PREFIX + canal, { timestamp: Math.floor(Date.now() / 1000), status: 'NAO_USO' });
        }

        function desfazerNaoUso(canal) {
            Core.removeActionCookie(NAOUSO_PREFIX + canal);
        }

        function marcarLead() {
            Core.saveActionCookie(LEAD_KEY, { timestamp: Math.floor(Date.now() / 1000), status: 'CONCLUIDA' });
        }

        /** Lead só se ainda não pedimos e-mail: sem flag, sem e-mail salvo e canal de e-mail não feito. */
        function precisaLead() {
            if (Core.readActions()[LEAD_KEY]) {
                return false;
            }
            var ativista = Core.getAtivista();
            if (ativista && ativista.email) {
                return false;
            }
            return !(canaisPorId.email && canalState('email') === 'done');
        }

        // ---------------- Home ----------------

        function refreshHome() {
            var proximo = proximoCanal();
            var algumFeito = false;
            root.querySelectorAll('[data-mc-cards] [data-mc-canal]').forEach(function (card) {
                var canal = card.getAttribute('data-mc-canal');
                var s = canalState(canal);
                algumFeito = algumFeito || s === 'done';
                card.classList.toggle('is-done', s === 'done');
                card.classList.toggle('is-skipped', s === 'skipped');
                card.classList.toggle('is-next', !!proximo && proximo.canal === canal);
                var status = card.querySelector('[data-mc-canal-status]');
                if (status) {
                    status.textContent = s === 'done' ? 'Feito' : s === 'skipped' ? 'Pulado' : '';
                }
            });

            var titulo = root.querySelector('[data-mc-home-title]');
            if (titulo) {
                titulo.textContent = titulo.getAttribute(algumFeito ? 'data-titulo-continuar' : 'data-titulo-inicio');
            }

            var p = progresso();
            root.querySelectorAll('[data-mc-progress]').forEach(function (el) {
                var text = el.querySelector('[data-mc-progress-text]');
                var bar = el.querySelector('[data-mc-progress-bar]');
                var fill = el.querySelector('[data-mc-progress-fill]');
                if (text) {
                    text.textContent = p.feitos + ' de ' + p.total;
                }
                if (bar) {
                    bar.setAttribute('aria-valuemax', p.total);
                    bar.setAttribute('aria-valuenow', p.feitos);
                }
                if (fill) {
                    fill.style.width = (p.total > 0 ? Math.min(100, Math.round((p.feitos / p.total) * 100)) : 0) + '%';
                }
            });

            root.classList.toggle('is-all-done', !proximo);
        }

        function homeCardClone(canal) {
            var card = root.querySelector('[data-mc-cards] [data-mc-canal="' + canal + '"]');
            return card ? card.outerHTML : '';
        }

        // ---------------- Bloqueio de rolagem ----------------

        function syncScrollLock() {
            var lock = modalStack.length > 0 || (screenCanal !== null && !DESKTOP_MQ.matches);
            document.documentElement.classList.toggle('pressao-mc-lock', lock);
        }

        // ---------------- Modais (pilha) ----------------

        function focusables(container) {
            return Array.prototype.filter.call(
                container.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), textarea, select, summary, [tabindex]:not([tabindex="-1"])'),
                function (el) {
                    return el.offsetParent !== null;
                }
            );
        }

        function renderModalTop() {
            var top = modalStack[modalStack.length - 1];
            if (!top) {
                modal.hidden = true;
                modal.classList.remove('is-open');
                dialog.innerHTML = '';
                dialog.className = 'pressao-mc-modal-dialog';
                syncScrollLock();
                return;
            }
            dialog.className = 'pressao-mc-modal-dialog' + (top.className ? ' ' + top.className : '');
            dialog.innerHTML = top.html;
            dialog.setAttribute('aria-label', top.label || '');
            modal.hidden = false;
            requestAnimationFrame(function () {
                modal.classList.add('is-open');
            });
            if (typeof top.onMount === 'function') {
                top.onMount(dialog);
            }
            var first = focusables(dialog)[0];
            (first || dialog).focus({ preventScroll: true });
            syncScrollLock();
        }

        /**
         * opts: { html | template, label, className, dismissable (default true), onMount(dialog), onClose() }
         */
        function openModal(opts) {
            var html = opts.html;
            if (!html && opts.template) {
                var tpl = root.querySelector('template[data-mc-template="' + opts.template + '"]');
                html = tpl ? tpl.innerHTML : '';
            }
            modalStack.push({
                html: html,
                label: opts.label,
                className: opts.className,
                dismissable: opts.dismissable !== false,
                onMount: opts.onMount,
                onClose: opts.onClose,
                returnFocus: document.activeElement
            });
            renderModalTop();
        }

        function closeModal() {
            var top = modalStack.pop();
            if (!top) {
                return;
            }
            renderModalTop();
            if (typeof top.onClose === 'function') {
                top.onClose();
            }
            if (!modalStack.length && top.returnFocus && document.contains(top.returnFocus)) {
                top.returnFocus.focus({ preventScroll: true });
            }
        }

        function closeAllModals() {
            while (modalStack.length) {
                closeModal();
            }
        }

        // ---------------- Telas (painel direito / drawer) ----------------

        function openScreen(html, canal, onMount) {
            var jaAberta = screenCanal !== null;
            if (!jaAberta) {
                focoAoFecharTela = document.activeElement;
            }
            screenCanal = canal || '';
            screen.innerHTML = html;
            screen.hidden = false;
            screen.classList.remove('is-leaving');
            root.classList.add('is-screen-open');
            if (!jaAberta) {
                screen.classList.add('is-entering');
                setTimeout(function () {
                    screen.classList.remove('is-entering');
                }, TRANSICAO_MS);
            }
            screen.scrollTop = 0;
            if (typeof onMount === 'function') {
                onMount(screen);
            }
            var titulo = screen.querySelector('[data-mc-screen-title]');
            if (titulo) {
                titulo.focus({ preventScroll: true });
            }
            if (DESKTOP_MQ.matches && panel) {
                var rect = panel.getBoundingClientRect();
                if (rect.top < 0) {
                    panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }
            syncScrollLock();
        }

        function closeScreen() {
            if (screenCanal === null) {
                return;
            }
            screenCanal = null;
            if (typeof aoFecharTela === 'function') {
                var fn = aoFecharTela;
                aoFecharTela = null;
                fn();
            }
            refreshHome();
            screen.classList.add('is-leaving');
            setTimeout(function () {
                if (screenCanal !== null) {
                    return;
                }
                screen.hidden = true;
                screen.classList.remove('is-leaving');
                screen.innerHTML = '';
                root.classList.remove('is-screen-open');
            }, TRANSICAO_MS);
            syncScrollLock();
            if (focoAoFecharTela && document.contains(focoAoFecharTela)) {
                focoAoFecharTela.focus({ preventScroll: true });
            }
        }

        function navHtml(canal, titulo) {
            return (
                '<header class="pressao-mc-nav">' +
                '<button type="button" class="pressao-mc-icon-btn pressao-mc-back" data-mc-back aria-label="Voltar">' + ico('seta-voltar') + '</button>' +
                '<h3 class="pressao-mc-nav-title" tabindex="-1" data-mc-screen-title>' +
                (canal ? ico(canal) : '') + '<span>' + esc(titulo) + '</span></h3>' +
                '<button type="button" class="pressao-mc-help-btn pressao-mc-help-btn--nav" data-mc-open-modal="ajuda" aria-label="Como funciona?">' +
                ico('interrogacao') + '</button>' +
                '</header>'
            );
        }

        /** Banner "Você já fez essa ação." com sugestão do próximo canal ou do compartilhar. */
        function bannerFeitoHtml(canal) {
            if (canalState(canal) !== 'done') {
                return '';
            }
            var proximo = proximoCanal(canal);
            var link = proximo
                ? '<button type="button" class="pressao-mc-banner-link" data-mc-goto="' + escAttr(proximo.canal) + '">Continue no ' +
                  esc((CANAL_TEXTOS[proximo.canal] || {}).nome || proximo.titulo) + ' ' + ico('seta-circulo-verde') + '</button>'
                : '<button type="button" class="pressao-mc-banner-link" data-mc-open-share>Compartilhe para impactar de outras formas ' +
                  ico('seta-circulo-verde') + '</button>';
            return '<div class="pressao-mc-banner" role="status"><p>Você já fez essa ação.</p>' + link + '</div>';
        }

        function erroHtml() {
            return '<p class="pressao-mc-error" data-mc-error role="alert" hidden></p>';
        }

        function mostrarErro(container, msg) {
            var el = container.querySelector('[data-mc-error]');
            if (el) {
                el.textContent = msg || '';
                el.hidden = !msg;
            }
        }

        function setLoading(btn, loading) {
            if (!btn) {
                return;
            }
            btn.disabled = loading;
            btn.classList.toggle('is-loading', loading);
            btn.setAttribute('aria-busy', loading ? 'true' : 'false');
        }

        // ---------------- Canais sociais ----------------

        function handlesItens() {
            return candidatos.map(function (c) {
                return { label: c.instagram, imagem: c.imagem };
            });
        }

        function mensagemSocial(c) {
            return Core.montarMensagemComHandles(
                candidatos.map(function (x) {
                    return x.instagram;
                }),
                c.mensagem
            );
        }

        function socialCopiarHtml(c) {
            var t = CANAL_TEXTOS[c.canal];
            return (
                '<div class="pressao-mc-screen-body">' +
                bannerFeitoHtml(c.canal) +
                (candidatos.length
                    ? '<section class="pressao-mc-block"><h4 class="pressao-mc-block-title">Candidatos selecionados</h4>' +
                      chipsHtml(handlesItens()) + '</section><hr class="pressao-mc-divider" />'
                    : '') +
                '<section class="pressao-mc-block">' +
                '<h4 class="pressao-mc-block-title">Copie o texto</h4>' +
                '<p class="pressao-mc-hint">' + esc(t.dica) + '</p>' +
                '<div class="pressao-mc-message" tabindex="0">' + esc(mensagemSocial(c)) + '</div>' +
                '<p class="pressao-mc-footnote">' + esc(t.nota) + '</p>' +
                '</section>' +
                erroHtml() +
                '<div class="pressao-mc-actions">' +
                '<button type="button" class="pressao-mc-btn pressao-mc-btn-primary" data-mc-copiar>' + esc(t.copiar) + ico('abrir-externo') + '</button>' +
                '<button type="button" class="pressao-mc-btn pressao-mc-btn-secondary" data-mc-naouso>' + esc(t.naoUso) + '</button>' +
                '</div></div>'
            );
        }

        function socialConfirmarHtml(c) {
            var t = CANAL_TEXTOS[c.canal];
            return (
                '<div class="pressao-mc-screen-body">' +
                '<ol class="pressao-mc-stepper">' +
                '<li class="pressao-mc-step is-done"><span class="pressao-mc-step-dot" aria-hidden="true">' + ico('check') + '</span>' +
                '<strong class="pressao-mc-step-title">' + esc(t.passo) + '</strong></li>' +
                '<li class="pressao-mc-step is-current"><span class="pressao-mc-step-dot" aria-hidden="true"></span>' +
                '<div><strong class="pressao-mc-step-title">' + esc(t.pergunta) + '</strong>' +
                '<p class="pressao-mc-step-text">Confirme aqui para somar a sua voz ao total de pressões dessa campanha e mostrar a nossa força para os candidatos.</p></div></li>' +
                '</ol>' +
                erroHtml() +
                '<div class="pressao-mc-actions pressao-mc-actions--inline">' +
                '<button type="button" class="pressao-mc-btn pressao-mc-btn-primary" data-mc-confirmar>' + ico('check-circulo') + 'Sim, já publiquei!</button>' +
                '<button type="button" class="pressao-mc-btn pressao-mc-btn-secondary" data-mc-tentar>Tentar novamente</button>' +
                '</div></div>'
            );
        }

        function abrirSocial(c, passo) {
            var t = CANAL_TEXTOS[c.canal];
            var corpo = passo === 'confirmar' ? socialConfirmarHtml(c) : socialCopiarHtml(c);
            openScreen(navHtml(c.canal, t.nome) + corpo, c.canal);
        }

        function copiarEAbrir(c, btn) {
            var t = CANAL_TEXTOS[c.canal];
            setLoading(btn, true);
            Core.copyText(mensagemSocial(c)).then(function () {
                var segundos = parseInt(config.countdown, 10) || 0;
                openModal({
                    label: 'Mensagem copiada',
                    className: 'pressao-mc-modal-dialog--feedback',
                    dismissable: false,
                    html: feedbackHtml(
                        'Mensagem copiada! Abrindo o ' + t.nome + '...',
                        segundos > 0
                            ? 'Abrindo em ' + segundos + '... Agora é só colar nos comentários e voltar aqui para confirmar.'
                            : 'Agora é só colar nos comentários e voltar aqui para confirmar.'
                    )
                });
                var espera = segundos > 0
                    ? Core.countdown(segundos, function (n) {
                          var el = dialog.querySelector('[data-mc-feedback-text]');
                          if (el) {
                              el.textContent = 'Abrindo em ' + n + '... Agora é só colar nos comentários e voltar aqui para confirmar.';
                          }
                      })
                    : Core.wait(ABRIR_SEM_CONTAGEM_MS);
                return espera.then(function () {
                    Core.openAppUrl(c.contato_url, c.canal);
                    closeAllModals();
                    setLoading(btn, false);
                    abrirSocial(c, 'confirmar');
                });
            });
        }

        // ---------------- Lead ----------------

        function leadHtml() {
            return (
                '<form class="pressao-mc-lead" data-mc-lead-form novalidate>' +
                '<header class="pressao-mc-lead-header">' +
                '<h3 class="pressao-mc-lead-title" tabindex="-1" data-mc-screen-title>Quer acompanhar os próximos passos?</h3>' +
                '<button type="button" class="pressao-mc-help-btn" data-mc-open-modal="ajuda" aria-label="Como funciona?">' + ico('interrogacao') + '</button>' +
                '</header>' +
                '<p class="pressao-mc-lead-text">Receba atualizações sobre a campanha e novas formas de pressionar pela ' + esc(campanhaNome) + '.</p>' +
                '<div class="pressao-mc-fields">' + camposAtivistaHtml(Core.getAtivista()) + '</div>' +
                erroHtml() +
                '<div class="pressao-mc-actions">' +
                '<button type="submit" class="pressao-mc-btn pressao-mc-btn-primary" data-mc-lead-sim>Quero receber atualizações</button>' +
                '<button type="button" class="pressao-mc-btn pressao-mc-btn-secondary" data-mc-lead-nao>Agora não</button>' +
                '</div></form>'
            );
        }

        /** Mostra o lead (modal no desktop, tela cheia no mobile); resolve com o ativista ou null. */
        function pedirLead(c) {
            return new Promise(function (resolve) {
                var resolvido = false;
                function finalizar(ativista) {
                    if (resolvido) {
                        return;
                    }
                    resolvido = true;
                    marcarLead();
                    if (ativista) {
                        Core.saveAtivista(ativista);
                    }
                    resolve(ativista);
                }
                function bind(container) {
                    var form = container.querySelector('[data-mc-lead-form]');
                    if (!form) {
                        return;
                    }
                    Core.bindPhoneMask(form.querySelector('[data-mc-telefone]'));
                    form.addEventListener('submit', function (e) {
                        e.preventDefault();
                        var r = lerAtivista(form);
                        if (r.erro) {
                            mostrarErro(form, r.erro);
                            return;
                        }
                        mostrarErro(form, '');
                        finalizar(r.ativista);
                    });
                    form.querySelector('[data-mc-lead-nao]').addEventListener('click', function () {
                        finalizar(null);
                    });
                }

                if (DESKTOP_MQ.matches) {
                    openModal({
                        label: 'Quer acompanhar os próximos passos?',
                        className: 'pressao-mc-modal-dialog--lead',
                        dismissable: false,
                        html: leadHtml(),
                        onMount: bind
                    });
                } else {
                    openScreen('<div class="pressao-mc-screen-body pressao-mc-screen-body--lead">' + leadHtml() + '</div>', c.canal, bind);
                }
            });
        }

        // ---------------- Registro da ação ----------------

        function salvarAcaoFeita(c, acaoId) {
            Core.saveActionCookie(c.alvo_id, {
                timestamp: Math.floor(Date.now() / 1000),
                acao_id: acaoId || null,
                status: 'CONCLUIDA'
            });
            desfazerNaoUso(c.canal);
        }

        function contadorDe(response) {
            var v = response && response.data ? response.data.acoes_confirmadas : null;
            return typeof v === 'number' ? v : undefined;
        }

        /** Feedback (padrão "Legal, sua pressão já está valendo!") e volta para a home (ou compartilhar se acabou). */
        function concluirComFeedback(titulo) {
            titulo = titulo || 'Legal, sua pressão já está valendo!';
            refreshHome();
            var p = progresso();
            openModal({
                label: titulo,
                className: 'pressao-mc-modal-dialog--feedback',
                dismissable: false,
                html: feedbackHtml(titulo, '', config.progresso ? progressHtml(p.feitos, p.total, 'light') : '')
            });
            return Core.wait(FEEDBACK_MS).then(function () {
                closeAllModals();
                if (proximoCanal()) {
                    closeScreen();
                } else {
                    abrirShare();
                }
            });
        }

        function registrarSocial(c, ativista, btn) {
            setLoading(btn, true);
            return Core.criarEConfirmarAcao({
                root: root,
                alvoId: c.alvo_id,
                campanhaId: config.campanha_id,
                canal: c.canal,
                templateId: c.template_id,
                ativista: ativista
            })
                .then(function (result) {
                    salvarAcaoFeita(c, result.acaoId);
                    Core.updateCounter(config.campanha_id, contadorDe(result.confirm));
                    return concluirComFeedback();
                })
                .catch(function (err) {
                    closeAllModals();
                    abrirSocial(c, 'confirmar');
                    mostrarErro(screen, (err && err.message) || 'Não foi possível registrar sua pressão. Tente novamente.');
                })
                .finally(function () {
                    setLoading(btn, false);
                });
        }

        function confirmarSocial(c, btn) {
            if (precisaLead()) {
                pedirLead(c).then(function (ativista) {
                    if (DESKTOP_MQ.matches) {
                        closeAllModals();
                    } else {
                        abrirSocial(c, 'confirmar');
                    }
                    registrarSocial(c, ativista, screen.querySelector('[data-mc-confirmar]'));
                });
                return;
            }
            registrarSocial(c, Core.getAtivista(), btn);
        }

        // ---------------- E-mail ----------------

        function candidatoPorNome(nome) {
            var alvo = String(nome || '').trim().toLowerCase();
            for (var i = 0; i < candidatos.length; i++) {
                if (String(candidatos[i].nome || '').trim().toLowerCase() === alvo) {
                    return candidatos[i];
                }
            }
            return null;
        }

        function destinatariosItens(c) {
            var membros = Array.isArray(c.membros) ? c.membros : [];
            if (!membros.length) {
                var total = c.total_membros || 1;
                return [{ label: total + (total === 1 ? ' destinatário' : ' destinatários'), imagem: '' }];
            }
            return membros.map(function (nome) {
                var cand = candidatoPorNome(nome);
                return { label: nome, imagem: cand ? cand.imagem : '' };
            });
        }

        function emailHtml(c) {
            return (
                navHtml('email', CANAL_TEXTOS.email.nome) +
                '<div class="pressao-mc-screen-body">' +
                bannerFeitoHtml('email') +
                '<dl class="pressao-mc-email-meta">' +
                '<div class="pressao-mc-meta-row"><dt>Para:</dt><dd>' + chipsHtml(destinatariosItens(c)) + '</dd></div>' +
                (c.assunto
                    ? '<div class="pressao-mc-meta-row"><dt>Assunto:</dt><dd><span class="pressao-mc-chip pressao-mc-chip--texto">' + esc(c.assunto) + '</span></dd></div>'
                    : '') +
                '</dl>' +
                (c.mensagem
                    ? '<details class="pressao-mc-accordion"><summary>Ver Texto' + ico('chevron') + '</summary>' +
                      '<div class="pressao-mc-accordion-body">' + esc(textoParaExibicao(c.mensagem)) + '</div></details>'
                    : '') +
                '<form class="pressao-mc-email-form" data-mc-email-form novalidate>' +
                '<h4 class="pressao-mc-block-title pressao-mc-block-title--help">Preencha as informações:' +
                '<button type="button" class="pressao-mc-help-mini" data-mc-open-modal="ajuda" aria-label="Como funciona?">' + ico('interrogacao') + '</button></h4>' +
                '<div class="pressao-mc-fields">' + camposAtivistaHtml(Core.getAtivista()) + '</div>' +
                erroHtml() +
                '<div class="pressao-mc-actions">' +
                '<button type="submit" class="pressao-mc-btn pressao-mc-btn-primary" data-mc-enviar-email>Enviar email</button>' +
                '</div>' +
                '<p class="pressao-mc-footnote">Seus dados são usados apenas para enviar este e-mail e não serão compartilhados.</p>' +
                '</form></div>'
            );
        }

        function abrirEmail(c) {
            openScreen(emailHtml(c), 'email', function (container) {
                var form = container.querySelector('[data-mc-email-form]');
                Core.bindPhoneMask(form.querySelector('[data-mc-telefone]'));
                form.addEventListener('submit', function (e) {
                    e.preventDefault();
                    var r = lerAtivista(form);
                    if (r.erro) {
                        mostrarErro(form, r.erro);
                        return;
                    }
                    mostrarErro(form, '');
                    enviarEmail(c, r.ativista, form.querySelector('[data-mc-enviar-email]'), form);
                });
            });
        }

        function enviarEmail(c, ativista, btn, form) {
            Core.saveAtivista(ativista);
            marcarLead();
            setLoading(btn, true);
            var base = { root: root, alvoId: c.alvo_id, campanhaId: config.campanha_id, canal: 'email', templateId: c.template_id, ativista: ativista };
            Core.realizarAcao(base)
                .then(function (create) {
                    var status = create.data && create.data.status;
                    var acaoId = create.data && (create.data.acao_id || (create.data.data && create.data.data.acao_id));
                    if (status === 'AGUARDANDO_ACAO_HUMANA' && acaoId) {
                        return Core.confirmarAcao({ root: root, acaoId: acaoId, alvoId: c.alvo_id, campanhaId: config.campanha_id }).then(function (confirm) {
                            return { acaoId: acaoId, contador: contadorDe(confirm) };
                        });
                    }
                    return { acaoId: acaoId, contador: undefined };
                })
                .then(function (r) {
                    salvarAcaoFeita(c, r.acaoId);
                    Core.updateCounter(config.campanha_id, r.contador);
                    return concluirComFeedback();
                })
                .catch(function (err) {
                    mostrarErro(form, (err && err.message) || 'Não foi possível enviar o email. Tente novamente.');
                })
                .finally(function () {
                    setLoading(btn, false);
                });
        }

        // ---------------- Telefone ----------------

        /** Ligação acompanhada agora: { salvo, poller }. `salvo` também vai para o sessionStorage. */
        var ligacao = null;

        function ligacaoStorageKey(c) {
            return LIGACAO_STORAGE_PREFIX + c.alvo_id;
        }

        function salvarLigacao(c, salvo) {
            try {
                window.sessionStorage.setItem(ligacaoStorageKey(c), JSON.stringify(salvo));
            } catch (e) { /* sem sessionStorage: só não retoma ao reabrir */ }
        }

        function lerLigacao(c) {
            try {
                var raw = window.sessionStorage.getItem(ligacaoStorageKey(c));
                var salvo = raw ? JSON.parse(raw) : null;
                return salvo && salvo.acaoId ? salvo : null;
            } catch (e) {
                return null;
            }
        }

        function limparLigacao(c) {
            try {
                window.sessionStorage.removeItem(ligacaoStorageKey(c));
            } catch (e) { /* ignore */ }
        }

        function pararAcompanhamento() {
            if (ligacao && ligacao.poller) {
                ligacao.poller.stop();
            }
            ligacao = null;
        }

        function membroPorId(c, id) {
            var membros = Array.isArray(c.membros) ? c.membros : [];
            for (var i = 0; i < membros.length; i++) {
                if (membros[i].id === id) {
                    return membros[i];
                }
            }
            return null;
        }

        function roteiroTexto(texto, alvoNome, ativistaNome) {
            return String(texto || '')
                .replace(/\{alvo_nome\}/g, alvoNome || '[nome do alvo]')
                .replace(/\{campanha_nome\}/g, campanhaNome)
                .replace(/\{ativista_nome\}/g, ativistaNome || SEU_NOME);
        }

        function infoHtml(texto) {
            return '<p class="pressao-mc-tel-info">' + ico('info') + '<span>' + esc(texto) + '</span></p>';
        }

        function roteiroHtml(texto, aberto) {
            return (
                '<details class="pressao-mc-accordion pressao-mc-tel-roteiro" data-mc-tel-roteiro' + (aberto ? ' open' : '') + (texto ? '' : ' hidden') + '>' +
                '<summary>Não sabe o que falar? Utilize esse roteiro' + ico('chevron') + '</summary>' +
                '<div class="pressao-mc-accordion-body" data-mc-tel-roteiro-texto>' + esc(texto) + '</div></details>'
            );
        }

        function telefoneIntroHtml(c) {
            var passos = [
                ['lapis', 'Você informa seus dados telefônicos'],
                ['telefone-entrada', 'Você recebe uma ligação nossa em instantes'],
                ['pessoas', 'A gente te conecta com a equipe do alvo']
            ];
            return (
                navHtml('telefone', CANAL_TEXTOS.telefone.nome) +
                '<div class="pressao-mc-screen-body">' +
                bannerFeitoHtml('telefone') +
                '<h4 class="pressao-mc-block-title">Como funciona</h4>' +
                '<ol class="pressao-mc-tel-passos">' +
                passos
                    .map(function (p) {
                        return '<li class="pressao-mc-tel-passo"><span class="pressao-mc-tel-passo-icon">' + ico(p[0]) + '</span><span>' + esc(p[1]) + '</span></li>';
                    })
                    .join('') +
                '</ol>' +
                (c.selecao === 'escolher'
                    ? ''
                    : infoHtml('Na próxima ligação, você pode ser direcionado para outro alvo. Assim, equilibramos as ligações entre todos os candidatos da campanha.')) +
                '<div class="pressao-mc-actions">' +
                '<button type="button" class="pressao-mc-btn pressao-mc-btn-primary" data-mc-tel-preencher>Preencher dados telefônicos</button>' +
                '</div></div>'
            );
        }

        function telefoneFormHtml(c) {
            var ativista = Core.getAtivista() || {};
            var emailCampo = c.email_campo || 'obrigatorio';
            var membros = Array.isArray(c.membros) ? c.membros : [];
            function value(v) {
                return v ? ' value="' + escAttr(v) + '"' : '';
            }

            var alvoHtml = c.selecao === 'escolher'
                ? '<label class="pressao-mc-field"><span class="pressao-mc-field-label">Escolha para quem ligar <span class="pressao-mc-required">*</span></span>' +
                  '<select name="membro_id" required data-mc-tel-membro><option value="">Selecione um candidato</option>' +
                  membros
                      .map(function (m) {
                          var meta = cargoPartido(m);
                          return '<option value="' + escAttr(m.id) + '">' + esc(m.nome + (meta ? ' · ' + meta : '')) + '</option>';
                      })
                      .join('') +
                  '</select></label>'
                : '<div class="pressao-mc-tel-alvo" data-mc-tel-alvo aria-busy="true">' +
                  '<span class="pressao-mc-tel-alvo-icon" aria-hidden="true">' + ico('telefone') + '</span>' +
                  '<span class="pressao-mc-tel-alvo-copy"><strong data-mc-tel-alvo-nome>Carregando o alvo da vez...</strong>' +
                  '<span data-mc-tel-alvo-meta></span></span>' +
                  '<span class="pressao-mc-tel-badge">Alvo da vez</span></div>';

            var campoEmail = emailCampo === 'oculto'
                ? ''
                : '<label class="pressao-mc-field"><span class="pressao-mc-field-label">Email ' +
                  (emailCampo === 'obrigatorio' ? '<span class="pressao-mc-required">*</span>' : '(opcional)') + '</span>' +
                  '<input type="email" name="email"' + (emailCampo === 'obrigatorio' ? ' required' : '') +
                  ' autocomplete="email" placeholder="Seu melhor email"' + value(ativista.email) + ' /></label>';

            var privacidade = emailCampo === 'oculto'
                ? ''
                : '<p class="pressao-mc-footnote">Ao continuar, você concorda em receber atualizações por e-mail, conforme a ' +
                  (config.privacidade_url
                      ? '<a href="' + escAttr(config.privacidade_url) + '" target="_blank" rel="noopener">Política de Privacidade</a>'
                      : 'Política de Privacidade') +
                  '.</p>';

            return (
                navHtml('telefone', CANAL_TEXTOS.telefone.nome) +
                '<div class="pressao-mc-screen-body">' +
                '<form class="pressao-mc-tel-form" data-mc-tel-form novalidate>' +
                '<h4 class="pressao-mc-block-title">Preencha seus dados para gente te ligar:</h4>' +
                '<section class="pressao-mc-block"><p class="pressao-mc-tel-label">Você vai ligar para:</p>' + alvoHtml + '</section>' +
                roteiroHtml(c.roteiro || '', false) +
                '<div class="pressao-mc-fields">' +
                '<label class="pressao-mc-field"><span class="pressao-mc-field-label">Nome completo <span class="pressao-mc-required">*</span></span>' +
                '<input type="text" name="nome" required autocomplete="name" placeholder="Seu nome completo"' + value(ativista.nome) + ' /></label>' +
                '<label class="pressao-mc-field"><span class="pressao-mc-field-label">Telefone <span class="pressao-mc-required">*</span></span>' +
                '<input type="tel" name="telefone" required inputmode="numeric" autocomplete="tel" placeholder="(00) 00000-0000" data-mc-telefone' +
                value(ativista.telefone ? Core.formatPhoneMask(ativista.telefone) : '') + ' /></label>' +
                campoEmail +
                '</div>' +
                erroHtml() +
                '<div class="pressao-mc-actions">' +
                '<button type="submit" class="pressao-mc-btn pressao-mc-btn-primary" data-mc-tel-ligar>' + ico('telefone') + 'Já pode me ligar</button>' +
                '</div>' +
                privacidade +
                '</form></div>'
            );
        }

        function abrirTelefone(c) {
            openScreen(telefoneIntroHtml(c), 'telefone', function (container) {
                container.querySelector('[data-mc-tel-preencher]').addEventListener('click', function () {
                    abrirTelefoneForm(c);
                });
            });
            var salvo = lerLigacao(c);
            if (salvo) {
                acompanharLigacao(c, salvo, true);
            }
        }

        function abrirTelefoneForm(c) {
            var estado = { membro: null, roteiro: c.roteiro || '', templateId: c.template_id || '' };
            openScreen(telefoneFormHtml(c), 'telefone', function (container) {
                var form = container.querySelector('[data-mc-tel-form]');
                var btn = form.querySelector('[data-mc-tel-ligar]');
                var select = form.querySelector('[data-mc-tel-membro]');
                Core.bindPhoneMask(form.querySelector('[data-mc-telefone]'));

                function atualizarRoteiro() {
                    var det = form.querySelector('[data-mc-tel-roteiro]');
                    det.hidden = !estado.roteiro;
                    det.querySelector('[data-mc-tel-roteiro-texto]').textContent = roteiroTexto(
                        estado.roteiro,
                        estado.membro && estado.membro.nome,
                        (form.elements.nome.value || '').trim()
                    );
                }
                form.elements.nome.addEventListener('input', atualizarRoteiro);

                if (select) {
                    if (!select.options || select.options.length <= 1) {
                        btn.disabled = true;
                        mostrarErro(form, 'Nenhum candidato disponível para ligação no momento.');
                    }
                    select.addEventListener('change', function () {
                        estado.membro = membroPorId(c, select.value);
                        atualizarRoteiro();
                    });
                } else {
                    btn.disabled = true;
                    Core.proximoMembro({ root: root, alvoId: c.alvo_id })
                        .then(function (r) {
                            if (!r.membro) {
                                throw new Error('Nenhum candidato disponível para ligação no momento.');
                            }
                            estado.membro = r.membro;
                            if (r.roteiro) {
                                estado.roteiro = r.roteiro;
                                estado.templateId = r.template_id || '';
                            }
                            var box = form.querySelector('[data-mc-tel-alvo]');
                            box.removeAttribute('aria-busy');
                            box.querySelector('[data-mc-tel-alvo-nome]').textContent = r.membro.nome;
                            box.querySelector('[data-mc-tel-alvo-meta]').textContent = cargoPartido(r.membro);
                            btn.disabled = false;
                            atualizarRoteiro();
                        })
                        .catch(function (err) {
                            form.querySelector('[data-mc-tel-alvo]').hidden = true;
                            mostrarErro(form, (err && err.message) || 'Não foi possível carregar o alvo da vez.');
                        });
                }
                atualizarRoteiro();

                form.addEventListener('submit', function (e) {
                    e.preventDefault();
                    var r = lerAtivistaTelefone(form, c.email_campo);
                    if (r.erro) {
                        mostrarErro(form, r.erro);
                        return;
                    }
                    if (!estado.membro) {
                        mostrarErro(form, select ? 'Escolha para quem ligar.' : 'Aguarde o carregamento do alvo da vez.');
                        return;
                    }
                    mostrarErro(form, '');
                    iniciarLigacao(c, r.ativista, estado, btn, form);
                });
            });
        }

        function iniciarLigacao(c, ativista, estado, btn, form) {
            var anterior = Core.getAtivista() || {};
            Core.saveAtivista({ nome: ativista.nome, email: ativista.email || anterior.email || '', telefone: ativista.telefone });
            if (ativista.email) {
                marcarLead();
            }
            var escolher = c.selecao === 'escolher';
            setLoading(btn, true);
            Core.realizarAcao({
                root: root,
                alvoId: c.alvo_id,
                campanhaId: config.campanha_id,
                canal: 'telefone',
                templateId: estado.templateId,
                ativista: ativista,
                membroId: estado.membro.id,
                selecao: escolher ? 'ativista' : 'automatica'
            })
                .then(function (create) {
                    var api = (create.data && create.data.data) || {};
                    var acaoId = (create.data && create.data.acao_id) || api.acao_id;
                    if (!acaoId) {
                        throw new Error('ID da ação não encontrado.');
                    }
                    var dados = (api.proximo_passo && api.proximo_passo.dados) || {};
                    var salvo = {
                        acaoId: acaoId,
                        telefone: ativista.telefone,
                        membroId: escolher ? estado.membro.id : '',
                        prefixo: dados.numero_origem_prefixo || '',
                        alvoNome: (dados.alvo && dados.alvo.nome) || estado.membro.nome,
                        roteiro: dados.roteiro || roteiroTexto(estado.roteiro, estado.membro.nome, ativista.nome)
                    };
                    salvarLigacao(c, salvo);
                    acompanharLigacao(c, salvo);
                })
                .catch(function (err) {
                    mostrarErro(form, (err && err.message) || 'Não foi possível iniciar a ligação. Tente novamente.');
                })
                .finally(function () {
                    setLoading(btn, false);
                });
        }

        function ligandoTextos(salvo) {
            return {
                titulo: 'Vamos te ligar em instantes',
                texto: 'Fique com o telefone por perto.' + (salvo.prefixo ? ' O número pode começar com (' + salvo.prefixo + ').' : '')
            };
        }

        function andamentoTextos(etapa, salvo) {
            var alvo = salvo.alvoNome || 'o alvo';
            return {
                titulo: 'Ligação em andamento',
                texto: etapa === 'EM_ANDAMENTO'
                    ? 'Você está falando com a equipe de ' + alvo + '. Se precisar, use o roteiro abaixo.'
                    : 'Estamos conectando você com a equipe de ' + alvo + '.'
            };
        }

        function ligandoHtml(salvo) {
            var t = ligandoTextos(salvo);
            return (
                '<div class="pressao-mc-feedback pressao-mc-tel-ligando">' +
                '<span class="pressao-mc-feedback-icon" aria-hidden="true">' + ico('telefone-entrada') + '</span>' +
                '<h3 class="pressao-mc-feedback-title">' + esc(t.titulo) + '</h3>' +
                '<p class="pressao-mc-feedback-text">' + esc(t.texto) + '</p>' +
                '</div>' +
                '<button type="button" class="pressao-mc-btn pressao-mc-btn-secondary pressao-mc-tel-ligando-fechar" data-mc-tel-fechar hidden>Fechar e acompanhar depois</button>'
            );
        }

        function andamentoHtml(etapa, salvo) {
            var t = andamentoTextos(etapa, salvo);
            return (
                navHtml('telefone', CANAL_TEXTOS.telefone.nome) +
                '<div class="pressao-mc-screen-body">' +
                '<div class="pressao-mc-tel-status" role="status">' +
                '<span class="pressao-mc-tel-status-icon" aria-hidden="true">' + ico('telefone') + '</span>' +
                '<div><strong data-mc-tel-status-titulo>' + esc(t.titulo) + '</strong>' +
                '<p data-mc-tel-status-texto>' + esc(t.texto) + '</p></div></div>' +
                roteiroHtml(salvo.roteiro || '', true) +
                '</div>'
            );
        }

        /**
         * Acompanha a ligação por polling: modal "Vamos te ligar" até o ativista atender, tela
         * "Ligação em andamento" com o roteiro enquanto fala com o alvo, depois sucesso ou erro.
         * `retomando`: reabertura do canal; espera o primeiro status antes de escolher a tela.
         */
        function acompanharLigacao(c, salvo, retomando) {
            pararAcompanhamento();
            var atual = { salvo: salvo, poller: null };
            ligacao = atual;
            aoFecharTela = pararAcompanhamento;

            var fase = null;
            var inicio = Date.now();
            var fecharVisivel = false;

            function abrirLigando() {
                fase = 'ligando';
                closeAllModals();
                openModal({
                    label: 'Vamos te ligar em instantes',
                    className: 'pressao-mc-modal-dialog--feedback',
                    dismissable: false,
                    html: ligandoHtml(salvo),
                    onMount: function (d) {
                        var fechar = d.querySelector('[data-mc-tel-fechar]');
                        fechar.hidden = !fecharVisivel;
                        fechar.addEventListener('click', function () {
                            closeAllModals();
                            closeScreen();
                        });
                    }
                });
            }

            function mostrarAndamento(etapa) {
                if (fase !== 'andamento') {
                    fase = 'andamento';
                    closeAllModals();
                    openScreen(andamentoHtml(etapa, salvo), 'telefone');
                    return;
                }
                var t = andamentoTextos(etapa, salvo);
                var titulo = screen.querySelector('[data-mc-tel-status-titulo]');
                var texto = screen.querySelector('[data-mc-tel-status-texto]');
                if (titulo) {
                    titulo.textContent = t.titulo;
                }
                if (texto) {
                    texto.textContent = t.texto;
                }
            }

            if (!retomando) {
                abrirLigando();
            }
            atual.poller = Core.poll(
                function () {
                    return Core.statusLigacao({ root: root, acaoId: salvo.acaoId, campanhaId: config.campanha_id }).then(
                        function (st) {
                            if (ligacao !== atual) {
                                return true;
                            }
                            if (st.alvo && st.alvo.nome) {
                                salvo.alvoNome = st.alvo.nome;
                            }
                            if (st.etapa === 'CONCLUIDA') {
                                ligacaoConcluida(c, salvo, st);
                                return true;
                            }
                            if (st.etapa === 'FALHA') {
                                ligacaoFalhou(c, salvo, st);
                                return true;
                            }
                            if (st.etapa === 'CHAMANDO_ALVO' || st.etapa === 'EM_ANDAMENTO') {
                                mostrarAndamento(st.etapa);
                            } else if (fase !== 'ligando') {
                                abrirLigando();
                            }
                            if (!fecharVisivel && Date.now() - inicio > LIGACAO_FECHAR_APOS_MS) {
                                fecharVisivel = true;
                                var fechar = dialog.querySelector('[data-mc-tel-fechar]');
                                if (fechar) {
                                    fechar.hidden = false;
                                }
                            }
                            return false;
                        },
                        function (err) {
                            if (ligacao !== atual) {
                                return true;
                            }
                            if (/sessão/i.test((err && err.message) || '')) {
                                pararAcompanhamento();
                                aoFecharTela = null;
                                limparLigacao(c);
                                closeAllModals();
                                abrirTelefoneForm(c);
                                mostrarErro(screen, 'Não encontramos sua ligação. Inicie uma nova.');
                                return true;
                            }
                            throw err;
                        }
                    );
                },
                function (decorrido) {
                    return decorrido < LIGACAO_POLL_LENTO_APOS_MS ? LIGACAO_POLL_MS : LIGACAO_POLL_LENTO_MS;
                }
            );
        }

        function ligacaoConcluida(c, salvo, st) {
            pararAcompanhamento();
            aoFecharTela = null;
            limparLigacao(c);
            salvarAcaoFeita(c, salvo.acaoId);
            Core.updateCounter(config.campanha_id, typeof st.acoes_confirmadas === 'number' ? st.acoes_confirmadas : undefined);
            closeAllModals();
            concluirComFeedback('Ligação realizada com sucesso!');
        }

        function ligacaoFalhou(c, salvo, st) {
            pararAcompanhamento();
            aoFecharTela = null;
            limparLigacao(c);
            closeAllModals();
            abrirErroLigacao(c, salvo, erroLigacaoTextos(st.origem_falha, st.motivo_falha, salvo.alvoNome));
        }

        function erroLigacaoHtml(salvo, t) {
            var numero = t.doAlvo
                ? infoHtml('Se ninguém atender, você ainda pode ajudar compartilhando a campanha.') +
                  '<button type="button" class="pressao-mc-share-link" data-mc-open-share>Compartilhar campanha' + ico('enviar') + '</button>'
                : '<div class="pressao-mc-tel-numero">' +
                  '<span class="pressao-mc-tel-numero-label">Seu número</span>' +
                  '<strong data-mc-tel-numero-valor>' + esc(Core.formatPhoneMask(salvo.telefone)) + '</strong>' +
                  '<button type="button" class="pressao-mc-tel-alterar" data-mc-tel-alterar>Alterar</button>' +
                  '<input type="tel" name="telefone" inputmode="numeric" autocomplete="tel" placeholder="(00) 00000-0000" aria-label="Seu número" data-mc-telefone hidden' +
                  ' value="' + escAttr(Core.formatPhoneMask(salvo.telefone)) + '" />' +
                  '</div>';
            return (
                navHtml('telefone', CANAL_TEXTOS.telefone.nome) +
                '<div class="pressao-mc-screen-body">' +
                '<div class="pressao-mc-tel-erro" role="alert">' +
                '<span class="pressao-mc-tel-erro-icon" aria-hidden="true">' + ico('alerta') + '</span>' +
                '<h4 class="pressao-mc-tel-erro-titulo">' + esc(t.titulo) + '</h4>' +
                '<p class="pressao-mc-tel-erro-texto">' + esc(t.texto) + '</p>' +
                '</div>' +
                numero +
                erroHtml() +
                '<div class="pressao-mc-actions">' +
                '<button type="button" class="pressao-mc-btn pressao-mc-btn-primary" data-mc-tel-novamente>' + ico('telefone') + 'Iniciar ligação novamente</button>' +
                '</div></div>'
            );
        }

        function abrirErroLigacao(c, salvo, t) {
            openScreen(erroLigacaoHtml(salvo, t), 'telefone', function (container) {
                var input = container.querySelector('[data-mc-telefone]');
                var alterar = container.querySelector('[data-mc-tel-alterar]');
                var btn = container.querySelector('[data-mc-tel-novamente]');
                if (input) {
                    Core.bindPhoneMask(input);
                }
                if (alterar) {
                    alterar.addEventListener('click', function () {
                        container.querySelector('[data-mc-tel-numero-valor]').hidden = true;
                        alterar.hidden = true;
                        input.hidden = false;
                        input.focus();
                    });
                }
                btn.addEventListener('click', function () {
                    var telefone = '';
                    if (input && !input.hidden) {
                        telefone = Core.digitsOnly(input.value);
                        if (!telefoneValido(telefone)) {
                            mostrarErro(container, 'Informe seu telefone com DDD.');
                            return;
                        }
                    }
                    mostrarErro(container, '');
                    tentarDeNovo(c, salvo, telefone, btn, container);
                });
            });
        }

        function tentarDeNovo(c, salvo, telefone, btn, container) {
            setLoading(btn, true);
            Core.novaLigacao({ root: root, acaoId: salvo.acaoId, telefone: telefone, membroId: salvo.membroId })
                .then(function (r) {
                    var api = r.data || {};
                    var dados = (api.proximo_passo && api.proximo_passo.dados) || {};
                    if (telefone) {
                        var ativista = Core.getAtivista() || {};
                        ativista.telefone = telefone;
                        Core.saveAtivista(ativista);
                    }
                    var novo = {
                        acaoId: salvo.acaoId,
                        telefone: telefone || salvo.telefone,
                        membroId: salvo.membroId,
                        prefixo: dados.numero_origem_prefixo || salvo.prefixo,
                        alvoNome: (dados.alvo && dados.alvo.nome) || salvo.alvoNome,
                        roteiro: dados.roteiro || salvo.roteiro
                    };
                    salvarLigacao(c, novo);
                    acompanharLigacao(c, novo);
                })
                .catch(function (err) {
                    mostrarErro(container, (err && err.message) || 'Não foi possível iniciar a ligação. Tente novamente.');
                })
                .finally(function () {
                    setLoading(btn, false);
                });
        }

        // ---------------- Pular ("Não uso") ----------------

        function abrirPular(canalPulado) {
            var restantes = pendentes(canalPulado);
            var cards = restantes
                .map(function (c) {
                    return '<li>' + homeCardClone(c.canal) + '</li>';
                })
                .join('');
            openModal({
                label: 'Tudo bem! Veja outras opções',
                className: 'pressao-mc-modal-dialog--pular',
                html:
                    modalHeaderHtml('Tudo bem! Veja outras opções') +
                    '<div class="pressao-mc-modal-body">' +
                    '<p class="pressao-mc-modal-text">Você ainda pode ajudar de outras formas e compartilhar com outras pessoas.</p>' +
                    (cards ? '<ul class="pressao-mc-cards pressao-mc-cards--modal">' + cards + '</ul>' : '') +
                    '<button type="button" class="pressao-mc-share-link" data-mc-open-share>Compartilhar campanha' + ico('enviar') + '</button>' +
                    '</div>'
            });
        }

        function naoUso(canal) {
            marcarNaoUso(canal);
            closeScreen();
            abrirPular(canal);
        }

        // ---------------- Compartilhar ----------------

        function abrirShare() {
            var header =
                '<header class="pressao-mc-share-header">' +
                '<button type="button" class="pressao-mc-icon-btn pressao-mc-back pressao-mc-desktop-only" data-mc-back aria-label="Voltar">' + ico('seta-voltar') + '</button>' +
                '<h3 class="pressao-mc-title" tabindex="-1" data-mc-screen-title>Convide mais pessoas</h3>' +
                '<button type="button" class="pressao-mc-icon-btn pressao-mc-mobile-only" data-mc-back aria-label="Fechar">' + ico('fechar') + '</button>' +
                '</header>';
            openScreen('<div class="pressao-mc-screen-body pressao-mc-share" data-mc-share></div>', 'compartilhar', function (container) {
                Core.renderShare(container.querySelector('[data-mc-share]'), config.share || {}, {
                    prefix: 'pressao-mc',
                    dataPrefix: 'mc',
                    redes: Array.isArray(config.redes) && config.redes.length ? config.redes : ['whatsapp', 'x', 'instagram'],
                    headerHtml: header,
                    subtitulo: 'Quanto mais gente participar, maior a pressão pela ' + campanhaNome + '. Você pode compartilhar com amigos ou marcar mais parlamentares.',
                    onShared: function () {
                        Core.saveActionCookie(SHARE_KEY, { timestamp: Math.floor(Date.now() / 1000), status: 'CONCLUIDA' });
                    }
                });
            });
        }

        // ---------------- Abrir canal ----------------

        function abrirCanal(canal) {
            var c = canaisPorId[canal];
            if (!c) {
                return;
            }
            if (canalState(canal) === 'skipped') {
                desfazerNaoUso(canal);
                refreshHome();
            }
            if (canal === 'email') {
                abrirEmail(c);
            } else if (canal === 'telefone') {
                abrirTelefone(c);
            } else {
                abrirSocial(c, 'copiar');
            }
        }

        // ---------------- Eventos (delegação) ----------------

        root.addEventListener('click', function (e) {
            var target = e.target.closest('button, a, summary, [data-mc-close-modal]');
            if (!target || !root.contains(target)) {
                return;
            }

            if (target.hasAttribute('data-mc-close-modal')) {
                var top = modalStack[modalStack.length - 1];
                if (top && top.dismissable) {
                    closeModal();
                }
                return;
            }

            var modalName = target.getAttribute('data-mc-open-modal');
            if (modalName) {
                openModal({ template: modalName, label: target.getAttribute('aria-label') || '', className: 'pressao-mc-modal-dialog--' + modalName });
                return;
            }

            if (target.hasAttribute('data-mc-open-share')) {
                closeAllModals();
                abrirShare();
                return;
            }

            var canalCard = target.getAttribute('data-mc-canal');
            if (canalCard) {
                closeAllModals();
                abrirCanal(canalCard);
                return;
            }

            var goto = target.getAttribute('data-mc-goto');
            if (goto) {
                abrirCanal(goto);
                return;
            }

            if (target.hasAttribute('data-mc-back')) {
                closeScreen();
                return;
            }

            if (target.hasAttribute('data-mc-chips-toggle')) {
                var wrap = target.closest('[data-mc-chips]');
                var expanded = wrap.classList.toggle('is-expanded');
                target.setAttribute('aria-expanded', expanded ? 'true' : 'false');
                return;
            }

            var c = screenCanal ? canaisPorId[screenCanal] : null;
            if (!c) {
                return;
            }
            if (target.hasAttribute('data-mc-copiar')) {
                copiarEAbrir(c, target);
            } else if (target.hasAttribute('data-mc-naouso')) {
                naoUso(c.canal);
            } else if (target.hasAttribute('data-mc-tentar')) {
                abrirSocial(c, 'copiar');
            } else if (target.hasAttribute('data-mc-confirmar')) {
                confirmarSocial(c, target);
            }
        });

        root.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                if (modalStack.length) {
                    if (modalStack[modalStack.length - 1].dismissable) {
                        e.preventDefault();
                        closeModal();
                    }
                    return;
                }
                if (screenCanal !== null) {
                    e.preventDefault();
                    closeScreen();
                }
                return;
            }
            if (e.key === 'Tab' && modalStack.length) {
                var items = focusables(dialog);
                if (!items.length) {
                    e.preventDefault();
                    dialog.focus();
                    return;
                }
                var first = items[0];
                var last = items[items.length - 1];
                if (e.shiftKey && document.activeElement === first) {
                    e.preventDefault();
                    last.focus();
                } else if (!e.shiftKey && document.activeElement === last) {
                    e.preventDefault();
                    first.focus();
                }
            }
        });

        var onViewportChange = function () {
            syncScrollLock();
        };
        if (DESKTOP_MQ.addEventListener) {
            DESKTOP_MQ.addEventListener('change', onViewportChange);
        } else if (DESKTOP_MQ.addListener) {
            DESKTOP_MQ.addListener(onViewportChange);
        }

        refreshHome();
        root.classList.add('is-ready');
    }

    function init() {
        document.querySelectorAll('.pressao-mc[data-pressao-mc]').forEach(function (root) {
            if (root.dataset.mcInit) {
                return;
            }
            root.dataset.mcInit = '1';
            Widget(root);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
