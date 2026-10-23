(function($) {
    function labels() {
        return window.pressaoAdminData || {};
    }

    function ajaxUrl() {
        return labels().ajaxUrl || (window.ajaxurl || '');
    }

    function closeAllEditors($list) {
        $list.find('.pressao-admin-list-row').removeClass('is-expanded');
        $list.find('.pressao-admin-list-editor').removeClass('is-open').attr('hidden', true);
    }

    function openEditor($row) {
        const $list = $row.closest('.pressao-admin-list');
        const index = $row.attr('data-index');
        closeAllEditors($list);
        $row.addClass('is-expanded');
        $list.find('.pressao-admin-list-editor[data-index="' + index + '"]')
            .addClass('is-open')
            .removeAttr('hidden');
    }

    function collectEditorData($editor) {
        const $fields = $editor.find('.pressao-admin-list-editor-fields');
        return {
            nome: $fields.find('[data-field="nome"]').val() || '',
            cargo: $fields.find('[data-field="cargo"]').val() || '',
            partido: $fields.find('[data-field="partido"]').val() || '',
            estado: $fields.find('[data-field="estado"]').val() || '',
            link_url: $fields.find('[data-field="link_url"]').val() || '',
            tiktok: $fields.find('[data-field="tiktok"]').val() || '',
            descricao: $fields.find('[data-field="descricao"]').val() || '',
            imagem_id: $fields.find('[data-field="imagem_id"]').val() || '0'
        };
    }

    function updateSummaryRow($row, item, thumb) {
        $row.find('[data-field="nome"]').text(item.nome || '');
        $row.find('[data-field="cargo"]').text(item.cargo || '');
        $row.find('[data-field="partido"]').text(item.partido || '');
        $row.find('[data-field="estado"]').text(item.estado || '');
        $row.find('[data-field="link_url"]').text(item.link_url || '');
        $row.find('[data-field="tiktok"]').text(item.tiktok || '');

        const $thumb = $row.find('.pressao-admin-list-thumb');
        if (thumb) {
            $thumb.html('<img src="' + thumb + '" alt="" />');
        } else {
            $thumb.html('<span class="pressao-admin-list-thumb-empty" aria-hidden="true">—</span>');
        }
    }

    function setStatus($editor, text, isError) {
        const $status = $editor.find('.pressao-admin-list-status');
        $status.text(text || '');
        $status.toggleClass('is-error', !!isError);
    }

    function renameShareImageFields($item, index) {
        $item.attr('data-index', index);
        $item.find('[name]').each(function() {
            this.name = this.name.replace(
                /pressao_compartilhamento\[imagens\]\[\d+\]/,
                'pressao_compartilhamento[imagens][' + index + ']'
            );
        });
    }

    function clearShareImage($item) {
        $item.find('input[type="text"]').val('');
        $item.find('.pressao-share-imagem-id').val('');
        $item.find('.pressao-share-imagem-preview').empty();
    }

    $(document).on('click', '.pressao-admin-list-row .pressao-admin-list-toggle, .pressao-admin-list-row td:not(.column-actions)', function(e) {
        if ($(e.target).closest('.pressao-admin-list-delete, a, button').length && !$(e.target).closest('.pressao-admin-list-toggle').length) {
            return;
        }
        e.preventDefault();
        const $row = $(this).closest('.pressao-admin-list-row');
        if ($row.hasClass('is-expanded')) {
            closeAllEditors($row.closest('.pressao-admin-list'));
            return;
        }
        openEditor($row);
    });

    $(document).on('click', '.pressao-admin-list-cancel', function(e) {
        e.preventDefault();
        closeAllEditors($(this).closest('.pressao-admin-list'));
    });

    $(document).on('click', '.pressao-admin-list-save', function(e) {
        e.preventDefault();
        const $btn = $(this);
        const $list = $btn.closest('.pressao-admin-list');
        const $editor = $btn.closest('.pressao-admin-list-editor');
        const index = $editor.attr('data-index');
        const data = collectEditorData($editor);
        const L = labels();

        setStatus($editor, L.saving || 'Salvando…', false);
        $btn.prop('disabled', true);

        $.post(ajaxUrl(), {
            action: 'pressao_candidato_save',
            nonce: $list.attr('data-nonce'),
            option: $list.attr('data-option'),
            index: index,
            candidato: data
        })
            .done(function(resp) {
                if (!resp || !resp.success) {
                    setStatus($editor, (resp && resp.data && resp.data.message) || L.saveError || 'Erro', true);
                    return;
                }
                const item = resp.data.item || data;
                const $row = $list.find('.pressao-admin-list-row[data-index="' + index + '"]');
                updateSummaryRow($row, item, resp.data.thumb || '');
                setStatus($editor, resp.data.message || L.saved || 'Salvo.', false);
            })
            .fail(function() {
                setStatus($editor, L.saveError || 'Erro', true);
            })
            .always(function() {
                $btn.prop('disabled', false);
            });
    });

    $(document).on('click', '.pressao-admin-list-delete', function(e) {
        e.preventDefault();
        e.stopPropagation();
        const L = labels();
        const msg = L.removeItemConfirm || 'Remover este candidato da lista?';
        if (!window.confirm(msg)) {
            return;
        }

        const $btn = $(this);
        const $list = $btn.closest('.pressao-admin-list');
        const $row = $btn.closest('.pressao-admin-list-row');
        const index = $row.attr('data-index');

        $btn.prop('disabled', true);

        $.post(ajaxUrl(), {
            action: 'pressao_candidato_delete',
            nonce: $list.attr('data-nonce'),
            option: $list.attr('data-option'),
            index: index
        })
            .done(function(resp) {
                if (!resp || !resp.success) {
                    window.alert((resp && resp.data && resp.data.message) || L.deleteError || 'Erro');
                    return;
                }
                window.location.reload();
            })
            .fail(function() {
                window.alert(L.deleteError || 'Erro');
            })
            .always(function() {
                $btn.prop('disabled', false);
            });
    });

    $(document).on('click', '.pressao-admin-list-add', function(e) {
        e.preventDefault();
        const $btn = $(this);
        const $list = $btn.closest('.pressao-admin-list');
        const L = labels();

        $btn.prop('disabled', true);

        $.post(ajaxUrl(), {
            action: 'pressao_candidato_add',
            nonce: $list.attr('data-nonce'),
            option: $list.attr('data-option')
        })
            .done(function(resp) {
                if (!resp || !resp.success || !resp.data || !resp.data.redirect) {
                    window.alert((resp && resp.data && resp.data.message) || L.addError || 'Erro');
                    return;
                }
                window.location.href = resp.data.redirect;
            })
            .fail(function() {
                window.alert(L.addError || 'Erro');
            })
            .always(function() {
                $btn.prop('disabled', false);
            });
    });

    $(document).on('click', '.pressao-select-candidato-image', function(e) {
        e.preventDefault();

        const $field = $(this).closest('.pressao-candidato-image-field');
        const L = labels();
        const frame = wp.media({
            title: L.selectCandidateImage || 'Selecionar imagem do candidato',
            button: {
                text: L.useThisImage || 'Usar esta imagem'
            },
            multiple: false
        });

        frame.on('select', function() {
            const attachment = frame.state().get('selection').first().toJSON();
            const previewUrl = (attachment.sizes && attachment.sizes.thumbnail && attachment.sizes.thumbnail.url)
                || attachment.url;

            $field.find('.pressao-candidato-image-id').val(attachment.id);
            $field.find('.pressao-candidato-image-preview').html(
                '<img src="' + previewUrl + '" alt="" />'
            );
        });

        frame.open();
    });

    $(document).on('click', '.pressao-remove-candidato-image', function(e) {
        e.preventDefault();

        const $field = $(this).closest('.pressao-candidato-image-field');
        $field.find('.pressao-candidato-image-id').val('');
        $field.find('.pressao-candidato-image-preview').empty();
    });

    $(document).on('click', '.pressao-add-share-imagem', function(e) {
        e.preventDefault();

        const $container = $(this).closest('.pressao-share-imagens-admin');
        const $list = $container.find('.pressao-share-imagens-list');
        const nextIndex = parseInt($container.attr('data-next-index'), 10) || 0;
        const $first = $list.find('.pressao-share-imagem-admin-item').first();

        if (!$first.length) {
            return;
        }

        const $newItem = $first.clone();
        renameShareImageFields($newItem, nextIndex);
        clearShareImage($newItem);
        $list.append($newItem);
        $container.attr('data-next-index', nextIndex + 1);
    });

    $(document).on('click', '.pressao-remove-share-imagem', function(e) {
        e.preventDefault();

        const $list = $(this).closest('.pressao-share-imagens-list');
        const $items = $list.find('.pressao-share-imagem-admin-item');

        if ($items.length <= 1) {
            clearShareImage($items.first());
            return;
        }

        $(this).closest('.pressao-share-imagem-admin-item').remove();
    });

    $(document).on('click', '.pressao-select-share-imagem', function(e) {
        e.preventDefault();

        const $field = $(this).closest('.pressao-share-imagem-field');
        const L = labels();
        const frame = wp.media({
            title: L.selectShareImage || 'Selecionar imagem para postar',
            button: {
                text: L.useThisImage || 'Usar esta imagem'
            },
            multiple: false
        });

        frame.on('select', function() {
            const attachment = frame.state().get('selection').first().toJSON();
            const previewUrl = (attachment.sizes && attachment.sizes.thumbnail && attachment.sizes.thumbnail.url)
                || attachment.url;

            $field.find('.pressao-share-imagem-id').val(attachment.id);
            $field.find('.pressao-share-imagem-preview').html(
                '<img src="' + previewUrl + '" alt="" />'
            );
        });

        frame.open();
    });

    $(document).on('click', '.pressao-remove-share-imagem-file', function(e) {
        e.preventDefault();

        const $field = $(this).closest('.pressao-share-imagem-field');
        $field.find('.pressao-share-imagem-id').val('');
        $field.find('.pressao-share-imagem-preview').empty();
    });

    function initImagensFila() {
        const $card = $('.pressao-imagens-fila');
        if (!$card.length) {
            return;
        }

        const L = labels();
        const nonce = $card.attr('data-nonce');
        const $barra = $card.find('.pressao-imagens-fila-barra');
        const $contagem = $card.find('.pressao-imagens-fila-contagem');
        const $estado = $card.find('.pressao-imagens-fila-estado');
        const $erros = $card.find('.pressao-imagens-fila-erros');
        const $continuar = $card.find('.pressao-imagens-fila-continuar');
        const MAX_FALHAS = 3;

        let status = {};
        try {
            status = JSON.parse($card.attr('data-status') || '{}');
        } catch (e) {
            status = {};
        }
        let ultimoTotal = status.total || 0;
        let falhas = 0;
        let rodando = false;
        let processouAlgo = false;

        function render(data) {
            status = data;
            if (data.total) {
                ultimoTotal = data.total;
            }
            const total = ultimoTotal || 0;
            const feitas = data.total ? data.concluidas : total - (data.erros || []).length;
            $barra.attr('max', Math.max(1, total)).val(feitas);
            $contagem.text(
                (L.filaContagem || '%1$d de %2$d imagens')
                    .replace('%1$d', feitas)
                    .replace('%2$d', total)
            );

            const erros = data.erros || [];
            const $lista = $erros.find('ul').empty();
            erros.forEach(function(item) {
                $('<li>')
                    .append($('<strong>').text(item.handle))
                    .append(document.createTextNode(' — ' + (item.erro || '')))
                    .appendTo($lista);
            });
            $erros.prop('hidden', !erros.length);
        }

        function concluir() {
            rodando = false;
            const comErros = (status.erros || []).length > 0;
            $estado.text(comErros ? (L.filaConcluidaErros || '') : (L.filaConcluida || ''));
            if (processouAlgo) {
                setTimeout(function() {
                    window.location.reload();
                }, comErros ? 3000 : 1500);
            }
        }

        function processar() {
            rodando = true;
            $continuar.prop('hidden', true);
            $estado.text(L.filaProcessando || '');
            $.post(ajaxUrl(), {
                action: 'pressao_apoiadores_imagens_processar',
                nonce: nonce
            }).done(function(resp) {
                if (!resp || !resp.success) {
                    falhou();
                    return;
                }
                falhas = 0;
                const data = resp.data || {};
                if (data.processadas) {
                    processouAlgo = true;
                }
                render(data);
                if (data.ocupado) {
                    $estado.text(L.filaOcupado || '');
                    setTimeout(processar, 5000);
                } else if (data.pendentes > 0) {
                    processar();
                } else {
                    concluir();
                }
            }).fail(falhou);
        }

        function falhou() {
            falhas++;
            if (falhas >= MAX_FALHAS) {
                rodando = false;
                $estado.text(L.filaFalhaRede || '');
                $continuar.prop('hidden', false);
                return;
            }
            setTimeout(processar, 3000);
        }

        $continuar.on('click', function() {
            falhas = 0;
            processar();
        });

        $card.on('click', '.pressao-imagens-fila-retentar', function() {
            const $btn = $(this).prop('disabled', true);
            $.post(ajaxUrl(), {
                action: 'pressao_apoiadores_imagens_retentar',
                nonce: nonce
            }).done(function(resp) {
                if (resp && resp.success) {
                    render(resp.data || {});
                    processar();
                }
            }).always(function() {
                $btn.prop('disabled', false);
            });
        });

        window.addEventListener('beforeunload', function(e) {
            if (rodando && status.pendentes > 0) {
                e.preventDefault();
                e.returnValue = L.filaSaindo || '';
                return e.returnValue;
            }
        });

        render(status);
        if (status.pendentes > 0) {
            processar();
        } else if ((status.erros || []).length) {
            $estado.text(L.filaConcluidaErros || '');
        }
    }

    function initCampanhaPicker() {
        const $root = $('.pressao-campanha-picker');
        if (!$root.length) {
            return;
        }

        const L = labels();
        const $card = $root.find('.pressao-campanha-card');
        const $busca = $root.find('.pressao-campanha-busca');
        const $form = $root.find('.pressao-campanha-form');
        const $status = $root.find('.pressao-campanha-form-status');
        const $salvar = $root.find('[data-action="salvar-form"]');
        const $select = $root.find('#pressao-campanha-select');
        let origemForm = 'busca';
        let linking = false;
        let ts = null;

        function nonce() {
            return $root.attr('data-nonce') || '';
        }

        function currentCampaign() {
            try {
                return JSON.parse($root.attr('data-campaign') || '{}') || {};
            } catch (e) {
                return {};
            }
        }

        function setCampaign(c) {
            $root.attr('data-campaign', JSON.stringify(c || {}));
        }

        function post(data) {
            return $.post(ajaxUrl(), $.extend({ nonce: nonce() }, data));
        }

        function show($el) {
            $el.removeAttr('hidden');
        }

        function hide($el) {
            $el.attr('hidden', true);
        }

        function showState(state) {
            hide($card);
            hide($busca);
            hide($form);
            if (state === 'cartao') {
                show($card);
            } else if (state === 'form') {
                show($form);
            } else {
                show($busca);
            }
        }

        function fillCard(c) {
            $card.find('.pressao-campanha-nome').text(c.nome || '');
            const $desc = $card.find('.pressao-campanha-descricao');
            $desc.text(c.descricao || '');
            if (c.descricao) {
                $desc.removeAttr('hidden');
            } else {
                $desc.attr('hidden', true);
            }
            $card.find('.pressao-campanha-telefone span').text(
                c.telefone_origem || L.campaignPhoneEmpty || 'Não definido'
            );
            const $badge = $card.find('.pressao-campanha-badge');
            const ativa = c.ativa !== false;
            $badge
                .text(ativa ? (L.campaignActive || 'Ativa') : (L.campaignInactive || 'Inativa'))
                .toggleClass('is-ativa', ativa)
                .toggleClass('is-inativa', !ativa)
                .removeAttr('hidden');
        }

        function fillForm(c) {
            $form.find('[data-field="id"]').val(c && c.id ? c.id : '');
            $form.find('[data-field="nome"]').val(c && c.nome ? c.nome : '');
            $form.find('[data-field="telefone_origem"]').val(c && c.telefone_origem ? c.telefone_origem : '');
            $form.find('[data-field="descricao"]').val(c && c.descricao ? c.descricao : '');
            $form.find('[data-field="ativa"]').prop('checked', !c || c.ativa !== false);
            $status.text('').removeClass('is-error');
            $salvar.text(
                c && c.id
                    ? (L.campaignSave || 'Salvar alterações')
                    : (L.campaignCreate || 'Criar campanha')
            );
        }

        function formData() {
            return {
                id: $form.find('[data-field="id"]').val() || '',
                nome: $form.find('[data-field="nome"]').val() || '',
                telefone_origem: $form.find('[data-field="telefone_origem"]').val() || '',
                descricao: $form.find('[data-field="descricao"]').val() || '',
                ativa: $form.find('[data-field="ativa"]').is(':checked') ? '1' : '0'
            };
        }

        function ajaxErrorMessage(resp, fallback) {
            return (resp && resp.data && resp.data.message) || fallback;
        }

        if ($select.length && typeof TomSelect !== 'undefined') {
            ts = new TomSelect('#pressao-campanha-select', {
                maxItems: 1,
                maxOptions: null,
                valueField: 'id',
                labelField: 'text',
                searchField: ['text'],
                placeholder: $select.attr('placeholder') || 'Digite o nome da campanha',
                preload: false,
                persist: false,
                loadThrottle: 300,
                shouldLoad: function (input) {
                    return input.length >= 2;
                },
                load: function (query, callback) {
                    post({ action: 'pressao_admin_buscar_campanhas', q: query })
                        .done(function (resp) {
                            if (!resp || !resp.success) {
                                callback();
                                return;
                            }
                            callback((resp.data && resp.data.results) || []);
                        })
                        .fail(function () {
                            callback();
                        });
                },
                render: {
                    no_results: function () {
                        return '<div class="no-results">' +
                            (L.campaignNoResults || 'Não encontramos resultados para sua busca') +
                            '</div>';
                    }
                },
                onChange: function (value) {
                    if (!value || linking) {
                        return;
                    }
                    linking = true;
                    post({ action: 'pressao_admin_vincular_campanha', id: value })
                        .done(function (resp) {
                            if (!resp || !resp.success) {
                                linking = false;
                                window.alert(ajaxErrorMessage(resp, L.campaignLinkError));
                                ts.clear(true);
                                return;
                            }
                            window.location.reload();
                        })
                        .fail(function () {
                            linking = false;
                            window.alert(L.campaignLinkError || 'Erro');
                            ts.clear(true);
                        });
                }
            });
        }

        $root.on('click', '[data-action="criar"]', function () {
            origemForm = 'busca';
            fillForm({});
            showState('form');
        });

        $root.on('click', '[data-action="editar"]', function () {
            origemForm = 'cartao';
            fillForm(currentCampaign());
            showState('form');
        });

        $root.on('click', '[data-action="trocar"]', function () {
            origemForm = 'busca';
            if (ts) {
                linking = true;
                ts.clear(true);
                linking = false;
            }
            $root.find('[data-action="voltar"]').removeAttr('hidden');
            showState('busca');
        });

        $root.on('click', '[data-action="voltar"]', function () {
            showState('cartao');
        });

        $root.on('click', '[data-action="cancelar"]', function () {
            showState(origemForm === 'cartao' ? 'cartao' : 'busca');
        });

        $root.on('click', '[data-action="salvar-form"]', function () {
            const data = formData();
            const editing = !!data.id;
            $status.text(L.saving || 'Salvando…').removeClass('is-error');
            $salvar.prop('disabled', true);

            const payload = {
                action: editing ? 'pressao_admin_atualizar_campanha' : 'pressao_admin_criar_campanha',
                nome: data.nome,
                descricao: data.descricao,
                telefone_origem: data.telefone_origem,
                ativa: data.ativa
            };
            if (editing) {
                payload.id = data.id;
            }

            post(payload)
                .done(function (resp) {
                    if (!resp || !resp.success) {
                        $status.text(ajaxErrorMessage(resp, L.campaignSaveError)).addClass('is-error');
                        return;
                    }
                    if (editing) {
                        const c = (resp.data && resp.data.campanha) || data;
                        setCampaign(c);
                        fillCard(c);
                        showState('cartao');
                        return;
                    }
                    window.location.reload();
                })
                .fail(function (xhr) {
                    let msg = L.campaignSaveError || 'Erro';
                    if (xhr && xhr.responseJSON && xhr.responseJSON.data && xhr.responseJSON.data.message) {
                        msg = xhr.responseJSON.data.message;
                    }
                    $status.text(msg).addClass('is-error');
                })
                .always(function () {
                    $salvar.prop('disabled', false);
                });
        });
    }

    function initRedesSociais() {
        $('.pressao-redes, .pressao-agregado').each(function () {
            initBaloesTemplates($(this));
        });
        $('.pressao-agregado').each(function () {
            initMembrosAgregado($(this));
            initTelefoneSelecao($(this));
        });
    }

    function initBaloesTemplates($root) {
        if (!$root.length) {
            return;
        }
        const L = labels();

        function nonce() {
            return $root.attr('data-nonce') || '';
        }

        function post(data) {
            return $.post(ajaxUrl(), $.extend({ nonce: nonce() }, data));
        }

        function ajaxMsg(resp, xhr, fallback) {
            if (resp && resp.data && resp.data.message) {
                return resp.data.message;
            }
            if (xhr && xhr.responseJSON && xhr.responseJSON.data && xhr.responseJSON.data.message) {
                return xhr.responseJSON.data.message;
            }
            return fallback;
        }

        function closeEditors() {
            $root.find('.pressao-redes-editor').attr('hidden', true);
            $root.find('.pressao-redes-balao').removeClass('is-open');
        }

        function fillEditor($editor, data) {
            $editor.find('[data-field="template-id"]').val(data.id || '');
            $editor.find('[data-field="titulo"]').val(data.titulo || '');
            $editor.find('[data-field="conteudo"]').val(data.conteudo || '');
            $editor.find('[data-field="ativo"]').prop('checked', data.ativo !== false && data.ativo !== '0');
            $editor.find('[data-action="remover-texto"]').prop('hidden', !data.id);
            $editor.find('.pressao-redes-editor-status').text('').removeClass('is-error');
        }

        $root.on('click', '[data-action="salvar-alvo"]', function () {
            const $card = $(this).closest('.pressao-redes-card');
            const $status = $card.find('.pressao-redes-alvo-status');
            const $btn = $(this);
            $status.text(L.saving || 'Salvando…').removeClass('is-error');
            $btn.prop('disabled', true);
            post({
                action: 'pressao_admin_salvar_alvo_social',
                canal: $card.attr('data-canal'),
                id: $card.find('[data-field="alvo-id"]').val() || '',
                nome: $card.find('[data-field="nome"]').val() || '',
                contato: $card.find('[data-field="contato"]').val() || ''
            })
                .done(function (resp) {
                    if (!resp || !resp.success) {
                        $status.text(ajaxMsg(resp, null, L.redesSaveError)).addClass('is-error');
                        return;
                    }
                    const alvo = (resp.data && resp.data.alvo) || {};
                    $card.find('[data-field="alvo-id"]').val(alvo.id || '');
                    $card.find('.pressao-redes-vazio').remove();
                    $btn.text($btn.attr('data-label-saved') || L.campaignSave || 'Salvar alterações');
                    $status.text(L.saved || 'Salvo.').removeClass('is-error');
                })
                .fail(function (xhr) {
                    $status.text(ajaxMsg(null, xhr, L.redesSaveError)).addClass('is-error');
                })
                .always(function () {
                    $btn.prop('disabled', false);
                });
        });

        $root.on('click', '.pressao-redes-balao:not(.pressao-redes-balao-add)', function () {
            const $balao = $(this);
            const $card = $balao.closest('.pressao-redes-card');
            const $editor = $card.find('.pressao-redes-editor');
            closeEditors();
            $balao.addClass('is-open');
            fillEditor($editor, {
                id: $balao.attr('data-id'),
                titulo: $balao.attr('data-titulo'),
                conteudo: $balao.attr('data-conteudo'),
                ativo: $balao.attr('data-ativo')
            });
            $editor.removeAttr('hidden');
        });

        $root.on('click', '[data-action="novo-texto"]', function () {
            const $card = $(this).closest('.pressao-redes-card');
            const $editor = $card.find('.pressao-redes-editor');
            closeEditors();
            fillEditor($editor, { ativo: true });
            $editor.removeAttr('hidden');
        });

        $root.on('click', '[data-action="cancelar-texto"]', function () {
            closeEditors();
        });

        $root.on('click', '[data-action="salvar-texto"]', function () {
            const $card = $(this).closest('.pressao-redes-card');
            const $editor = $card.find('.pressao-redes-editor');
            const $status = $editor.find('.pressao-redes-editor-status');
            const $btn = $(this);
            $status.text(L.saving || 'Salvando…').removeClass('is-error');
            $btn.prop('disabled', true);
            post({
                action: 'pressao_admin_salvar_template_social',
                canal: $card.attr('data-canal'),
                id: $editor.find('[data-field="template-id"]').val() || '',
                titulo: $editor.find('[data-field="titulo"]').val() || '',
                conteudo: $editor.find('[data-field="conteudo"]').val() || '',
                ativo: $editor.find('[data-field="ativo"]').is(':checked') ? '1' : '0'
            })
                .done(function (resp) {
                    if (!resp || !resp.success) {
                        $status.text(ajaxMsg(resp, null, L.redesSaveError)).addClass('is-error');
                        return;
                    }
                    window.location.reload();
                })
                .fail(function (xhr) {
                    $status.text(ajaxMsg(null, xhr, L.redesSaveError)).addClass('is-error');
                })
                .always(function () {
                    $btn.prop('disabled', false);
                });
        });

        $root.on('click', '[data-action="remover-texto"]', function () {
            const msg = L.redesDeleteConfirm || 'Remover este texto?';
            if (!window.confirm(msg)) {
                return;
            }
            const $card = $(this).closest('.pressao-redes-card');
            const $editor = $card.find('.pressao-redes-editor');
            const $status = $editor.find('.pressao-redes-editor-status');
            const id = $editor.find('[data-field="template-id"]').val() || '';
            $status.text(L.saving || 'Salvando…').removeClass('is-error');
            post({
                action: 'pressao_admin_deletar_template_social',
                id: id
            })
                .done(function (resp) {
                    if (!resp || !resp.success) {
                        $status.text(ajaxMsg(resp, null, L.redesSaveError)).addClass('is-error');
                        return;
                    }
                    window.location.reload();
                })
                .fail(function (xhr) {
                    $status.text(ajaxMsg(null, xhr, L.redesSaveError)).addClass('is-error');
                });
        });
    }

    function initMembrosAgregado($root) {
        if (!$root.length) {
            return;
        }
        const L = labels();

        function nonce() {
            return $root.attr('data-nonce') || '';
        }

        function post(data) {
            return $.post(ajaxUrl(), $.extend({ nonce: nonce() }, data));
        }

        function ajaxMsg(resp, xhr, fallback) {
            if (resp && resp.data && resp.data.message) {
                return resp.data.message;
            }
            if (xhr && xhr.responseJSON && xhr.responseJSON.data && xhr.responseJSON.data.message) {
                return xhr.responseJSON.data.message;
            }
            return fallback;
        }

        function $editor() {
            return $root.find('.pressao-agregado-editor');
        }

        function fillMembro(data) {
            const $ed = $editor();
            $ed.find('[data-field="membro-id"]').val(data.id || '');
            $ed.find('[data-field="nome"]').val(data.nome || '');
            $ed.find('[data-field="contato"]').val(data.contato || '');
            $ed.find('[data-field="cargo"]').val(data.cargo || '');
            $ed.find('[data-field="partido"]').val(data.partido || '');
            $ed.find('[data-action="remover-membro"]').prop('hidden', !data.id);
            $ed.find('.pressao-agregado-editor-status').text('').removeClass('is-error');
            $ed.removeAttr('hidden');
        }

        $root.on('click', '[data-action="editar-membro"]', function (e) {
            e.preventDefault();
            const $row = $(this).closest('.pressao-agregado-row');
            fillMembro({
                id: $row.attr('data-id'),
                nome: $row.attr('data-nome'),
                contato: $row.attr('data-contato'),
                cargo: $row.attr('data-cargo'),
                partido: $row.attr('data-partido')
            });
        });

        $root.on('click', '[data-action="novo-membro"]', function () {
            fillMembro({});
        });

        $root.on('click', '[data-action="cancelar-membro"]', function () {
            $editor().attr('hidden', true);
        });

        $root.on('click', '[data-action="salvar-membro"]', function () {
            const $ed = $editor();
            const $status = $ed.find('.pressao-agregado-editor-status');
            const $btn = $(this);
            $status.text(L.saving || 'Salvando…').removeClass('is-error');
            $btn.prop('disabled', true);
            post({
                action: 'pressao_admin_salvar_membro',
                canal: $root.attr('data-canal'),
                id: $ed.find('[data-field="membro-id"]').val() || '',
                nome: $ed.find('[data-field="nome"]').val() || '',
                contato: $ed.find('[data-field="contato"]').val() || '',
                cargo: $ed.find('[data-field="cargo"]').val() || '',
                partido: $ed.find('[data-field="partido"]').val() || ''
            })
                .done(function (resp) {
                    if (!resp || !resp.success) {
                        $status.text(ajaxMsg(resp, null, L.redesSaveError)).addClass('is-error');
                        return;
                    }
                    window.location.reload();
                })
                .fail(function (xhr) {
                    $status.text(ajaxMsg(null, xhr, L.redesSaveError)).addClass('is-error');
                })
                .always(function () {
                    $btn.prop('disabled', false);
                });
        });

        $root.on('click', '[data-action="remover-membro"]', function () {
            const msg = L.membroDeleteConfirm || 'Remover esta pessoa?';
            if (!window.confirm(msg)) {
                return;
            }
            const $ed = $editor();
            const $status = $ed.find('.pressao-agregado-editor-status');
            const id = $ed.find('[data-field="membro-id"]').val() || '';
            $status.text(L.saving || 'Salvando…').removeClass('is-error');
            post({
                action: 'pressao_admin_deletar_membro',
                id: id
            })
                .done(function (resp) {
                    if (!resp || !resp.success) {
                        $status.text(ajaxMsg(resp, null, L.redesSaveError)).addClass('is-error');
                        return;
                    }
                    window.location.reload();
                })
                .fail(function (xhr) {
                    $status.text(ajaxMsg(null, xhr, L.redesSaveError)).addClass('is-error');
                });
        });
    }

    function initTelefoneSelecao($root) {
        if (!$root.length || $root.attr('data-canal') !== 'telefone') {
            return;
        }
        const L = labels();

        function ajaxMsg(resp, xhr, fallback) {
            if (resp && resp.data && resp.data.message) {
                return resp.data.message;
            }
            if (xhr && xhr.responseJSON && xhr.responseJSON.data && xhr.responseJSON.data.message) {
                return xhr.responseJSON.data.message;
            }
            return fallback;
        }

        $root.on('click', '.pressao-admin-help', function (e) {
            e.preventDefault();
            e.stopPropagation();
            const $btn = $(this);
            const open = $btn.hasClass('is-open');
            $root.find('.pressao-admin-help').removeClass('is-open');
            if (!open) {
                $btn.addClass('is-open');
            }
        });

        $(document).on('click.pressaoTelefoneHelp', function (e) {
            if ($(e.target).closest('.pressao-admin-help').length) {
                return;
            }
            $root.find('.pressao-admin-help').removeClass('is-open');
        });

        $root.on('click', '[data-action="salvar-telefone-selecao"]', function () {
            const $status = $root.find('.pressao-telefone-selecao-status');
            const $btn = $(this);
            const selecao = $root.find('input[name="pressao_telefone_selecao"]:checked').val() || '';
            $status.text(L.saving || 'Salvando…').removeClass('is-error');
            $btn.prop('disabled', true);
            $.post(ajaxUrl(), {
                action: 'pressao_admin_salvar_telefone_selecao',
                nonce: $root.attr('data-nonce') || '',
                selecao: selecao
            })
                .done(function (resp) {
                    if (!resp || !resp.success) {
                        $status.text(ajaxMsg(resp, null, L.redesSaveError)).addClass('is-error');
                        return;
                    }
                    $status.text(L.saved || 'Salvo.').removeClass('is-error');
                })
                .fail(function (xhr) {
                    $status.text(ajaxMsg(null, xhr, L.redesSaveError)).addClass('is-error');
                })
                .always(function () {
                    $btn.prop('disabled', false);
                });
        });
    }

    $(function() {
        initCampanhaPicker();
        initRedesSociais();

        const $removeSelect = $('#pressao-apoiadores-remove-select');
        if ($removeSelect.length && typeof TomSelect !== 'undefined') {
            new TomSelect('#pressao-apoiadores-remove-select', {
                plugins: ['remove_button'],
                maxItems: null,
                maxOptions: null,
                placeholder: $removeSelect.attr('placeholder') || 'Digite nome ou @',
                searchField: ['text'],
                render: {
                    no_results: function () {
                        return '<div class="no-results">Não encontramos resultados para sua busca</div>';
                    }
                }
            });
        }

        initImagensFila();

        $('.pressao-apoiadores-remove-form').on('submit', function(e) {
            const L = labels();
            const selected = $removeSelect.val();
            if (!selected || !selected.length) {
                e.preventDefault();
                return;
            }
            const msg = L.removeConfirm || 'Remover os candidatos selecionados da base de apoiadores?';
            if (!window.confirm(msg)) {
                e.preventDefault();
            }
        });
    });
})(jQuery);
