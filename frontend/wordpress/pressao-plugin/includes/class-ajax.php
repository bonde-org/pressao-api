<?php
/**
 * AJAX Handlers para campanha
 * 
 * @package PressaoPlugin
 */

if (!defined('ABSPATH')) {
    exit;
}

class PressaoPlugin_Ajax {
    
    private $api;
    
    public function __construct() {
        $this->api = new PressaoPlugin_API();
        
        add_action('wp_ajax_pressao_get_campanha', [$this, 'ajax_get_campanha']);
        add_action('wp_ajax_nopriv_pressao_get_campanha', [$this, 'ajax_get_campanha']);

        add_action('wp_ajax_pressao_realizar_acao', [$this, 'ajax_realizar_acao']);
        add_action('wp_ajax_nopriv_pressao_realizar_acao', [$this, 'ajax_realizar_acao']);

        add_action('wp_ajax_pressao_confirmar_acao', [$this, 'ajax_confirmar_acao']);
        add_action('wp_ajax_nopriv_pressao_confirmar_acao', [$this, 'ajax_confirmar_acao']);
        
        add_action('wp_ajax_pressao_get_acoes_status', [$this, 'ajax_get_acoes_status']);
        add_action('wp_ajax_nopriv_pressao_get_acoes_status', [$this, 'ajax_get_acoes_status']);

        add_action('wp_ajax_pressao_buscar_candidatos', [$this, 'ajax_buscar_candidatos']);
        add_action('wp_ajax_nopriv_pressao_buscar_candidatos', [$this, 'ajax_buscar_candidatos']);

        // Sem verificação de nonce: serve para renovar nonce stale (page cache / sessão)
        add_action('wp_ajax_pressao_refresh_nonce', [$this, 'ajax_refresh_nonce']);
        add_action('wp_ajax_nopriv_pressao_refresh_nonce', [$this, 'ajax_refresh_nonce']);
    }
    
    /**
     * AJAX: Renova o nonce da sessão atual (não exige nonce prévio).
     *
     * Necessário quando a página foi servida de cache com nonce de outro usuário/tick,
     * ou quando cookies de sessão WP caíram após estouro do limite de cookies.
     */
    public function ajax_refresh_nonce() {
        wp_send_json_success([
            'nonce' => wp_create_nonce('pressao_acao_nonce'),
        ]);
    }

    /**
     * AJAX: Obtém dados da campanha
     */
    public function ajax_get_campanha() {
        // Verifica nonce
        if (!isset($_POST['nonce']) || !wp_verify_nonce($_POST['nonce'], 'pressao_acao_nonce')) {
            wp_send_json_error(['message' => __('Nonce inválido', 'pressao-plugin')], 403);
        }
        
        $campanha_id = isset($_POST['campanha_id']) ? sanitize_text_field($_POST['campanha_id']) : '';
        
        if (empty($campanha_id)) {
            wp_send_json_error(['message' => __('ID da campanha não informado', 'pressao-plugin')], 400);
        }
        
        // Busca campanha
        $result = $this->api->get_campanha($campanha_id);
        
        if (is_wp_error($result)) {
            wp_send_json_error([
                'message' => $result->get_error_message(),
                'code' => $result->get_error_code()
            ], 500);
        }
        
        wp_send_json_success([
            'data' => $result
        ]);
    }

    /**
     * AJAX: Realiza uma ação para um alvo
     */
    public function ajax_realizar_acao() {
        // Verifica nonce
        if (!isset($_POST['nonce']) || !wp_verify_nonce($_POST['nonce'], 'pressao_acao_nonce')) {
            wp_send_json_error(['message' => __('Nonce inválido', 'pressao-plugin')], 403);
        }
        
        $alvo_id = isset($_POST['alvo_id']) ? sanitize_text_field($_POST['alvo_id']) : '';
        $campanha_id = isset($_POST['campanha_id']) ? sanitize_text_field($_POST['campanha_id']) : '';
        $canal = isset($_POST['canal']) ? sanitize_text_field($_POST['canal']) : 'email';
        $sessao_id = isset($_POST['sessao_id']) ? sanitize_text_field($_POST['sessao_id']) : '';
        $template_id = isset($_POST['template_id']) ? sanitize_text_field($_POST['template_id']) : null;
        
        // Dados do ativista
        $ativista_nome = isset($_POST['ativista_nome']) ? sanitize_text_field($_POST['ativista_nome']) : '';
        $ativista_email = isset($_POST['ativista_email']) ? sanitize_email($_POST['ativista_email']) : '';
        $ativista_telefone = isset($_POST['ativista_telefone']) ? sanitize_text_field($_POST['ativista_telefone']) : '';
        
        $has_ativista_data = !empty($ativista_nome) || !empty($ativista_email) || !empty($ativista_telefone);
        
        if (empty($alvo_id) || empty($campanha_id)) {
            wp_send_json_error(['message' => __('Dados incompletos', 'pressao-plugin')], 400);
        }
        
        // Prepara dados para a API
        if ($has_ativista_data) {
            $ativista = [
                'nome' => $ativista_nome,
                'email' => $ativista_email,
                'telefone' => $ativista_telefone
            ];
            $result = $this->api->criar_acao_com_ativista($campanha_id, $alvo_id, $canal, $ativista, $template_id, $sessao_id);
        } else {
            $result = $this->api->criar_acao_sem_ativista($campanha_id, $alvo_id, $canal, $template_id, $sessao_id);
        }
        
        if (is_wp_error($result)) {
            wp_send_json_error([
                'message' => $result->get_error_message(),
                'code' => $result->get_error_code()
            ], 500);
        }
        
        // Gera ID de usuário anônimo se necessário
        $user_id = $this->get_or_create_anonymous_user_id();
        
        // ============================================
        // RETORNA O STATUS DA AÇÃO PARA O FRONTEND
        // ============================================
        $api_data = $result['data'] ?? [];

        if (!empty($campanha_id)) {
            $this->api->invalidar_cache_contador($campanha_id);
        }

        wp_send_json_success([
            'message' => $result['message'] ?? __('Ação realizada com sucesso!', 'pressao-plugin'),
            'alvo_id' => $alvo_id,
            'timestamp' => time(),
            'user_id' => $user_id,
            'data' => $api_data,
            'acao_id' => $api_data['acao_id'] ?? null,
            'status' => $api_data['status_atual'] ?? 'CONCLUIDA',
        ]);
    }

    /**
     * AJAX: Confirma uma ação manual
     */
    public function ajax_confirmar_acao() {
        if (!isset($_POST['nonce']) || !wp_verify_nonce($_POST['nonce'], 'pressao_acao_nonce')) {
            wp_send_json_error(['message' => __('Nonce inválido', 'pressao-plugin')], 403);
        }

        $acao_id = isset($_POST['acao_id']) ? sanitize_text_field($_POST['acao_id']) : '';
        $alvo_id = isset($_POST['alvo_id']) ? sanitize_text_field($_POST['alvo_id']) : '';
        $campanha_id = isset($_POST['campanha_id']) ? sanitize_text_field($_POST['campanha_id']) : '';

        if (empty($acao_id)) {
            wp_send_json_error(['message' => __('ID da ação não informado', 'pressao-plugin')], 400);
        }

        $result = $this->api->confirmar_acao($acao_id);

        if (is_wp_error($result)) {
            wp_send_json_error([
                'message' => $result->get_error_message(),
                'code' => $result->get_error_code()
            ], 500);
        }

        if ($campanha_id) {
            $this->api->invalidar_cache_contador($campanha_id);
        }

        wp_send_json_success([
            'message' => $result['message'] ?? __('Ação confirmada com sucesso!', 'pressao-plugin'),
            'acao_id' => $acao_id,
            'alvo_id' => $alvo_id,
            'status' => 'CONCLUIDA',
            'timestamp' => time(),
            'acoes_confirmadas' => $result['acoes_confirmadas'] ?? null,
        ]);
    }

    /**
     * Obtém ou cria um ID de usuário anônimo
     */
    private function get_or_create_anonymous_user_id() {
        // Usa cookie ou localStorage via JavaScript
        // Por enquanto, gera um ID baseado em sessão
        if (isset($_COOKIE['pressao_usuario_id'])) {
            return $_COOKIE['pressao_usuario_id'];
        }
        
        // Gera novo ID
        $user_id = 'anon_' . uniqid() . '_' . md5($_SERVER['REMOTE_ADDR'] . time());
        setcookie('pressao_usuario_id', $user_id, time() + (30 * DAY_IN_SECONDS), '/');
        
        return $user_id;
    }

    /**
     * Busca ações do usuário no banco (para sincronização)
     */
    private function get_user_actions_from_db($user_id) {
        // TODO: Implementar busca de ações no banco
        return [];
    }

    /**
     * AJAX: Obtém status das ações para os alvos
     */
    public function ajax_get_acoes_status() {
        if (!isset($_POST['nonce']) || !wp_verify_nonce($_POST['nonce'], 'pressao_acao_nonce')) {
            wp_send_json_error(['message' => __('Nonce inválido', 'pressao-plugin')], 403);
        }
        
        $alvos = isset($_POST['alvos']) ? array_map('sanitize_text_field', (array) $_POST['alvos']) : [];
        
        if (empty($alvos)) {
            wp_send_json_success([]);
        }
        
        // Busca ações realizadas (local ou DB)
        $acoes = [];
        foreach ($alvos as $alvo_id) {
            $acoes[$alvo_id] = $this->get_alvo_action_state($alvo_id);
        }
        
        wp_send_json_success($acoes);
    }

    /**
     * AJAX: Busca candidatos (base pressao_candidatos) para o autocomplete
     * do [pressao_fluxo]. A lista pode ter milhares de linhas — por isso
     * a busca é feita aqui, no servidor, em vez de embutir tudo no HTML.
     */
    public function ajax_buscar_candidatos() {
        if (!isset($_POST['nonce']) || !wp_verify_nonce($_POST['nonce'], 'pressao_acao_nonce')) {
            wp_send_json_error(['message' => __('Nonce inválido', 'pressao-plugin')], 403);
        }

        $termo = isset($_POST['q']) ? trim(sanitize_text_field(wp_unslash($_POST['q']))) : '';
        if (mb_strlen($termo) < 2) {
            wp_send_json_success(['results' => []]);
        }

        $candidatos_raw = get_option('pressao_candidatos', []);
        if (!is_array($candidatos_raw)) {
            $candidatos_raw = [];
        }
        $termo_lower = mb_strtolower($termo);
        $max_resultados = 20;

        // Filtra ANTES de normalizar — normalize_candidatos_for_fluxo()
        // resolve a URL da imagem (wp_get_attachment_image_url) pra cada
        // linha, e com a base grande (6 mil+) rodar isso pra tudo antes de
        // filtrar deixava a busca levando vários segundos por tecla. Aqui só
        // as poucas linhas que batem com o termo passam pela normalização —
        // o índice original é preservado (array_filter/chaves originais),
        // então o id "c{índice}" sai igual ao que sairia sem esse filtro.
        $matched_raw = [];
        foreach ($candidatos_raw as $index => $candidato) {
            if (!is_array($candidato) || empty($candidato['link_url'])) {
                continue;
            }
            $alvo_busca = mb_strtolower(trim(($candidato['nome'] ?? '') . ' ' . $candidato['link_url']));
            if (strpos($alvo_busca, $termo_lower) === false) {
                continue;
            }
            $matched_raw[$index] = $candidato;
            if (count($matched_raw) >= $max_resultados) {
                break;
            }
        }

        $candidatos = PressaoPlugin_Shortcode::normalize_candidatos_for_fluxo($matched_raw, 'c');
        $resultados = [];
        foreach ($candidatos as $candidato) {
            if (empty($candidato['instagram'])) {
                continue;
            }
            $resultados[] = [
                'id' => $candidato['id'],
                'text' => trim((($candidato['nome'] ?? '') ? $candidato['nome'] . ' ' : '') . $candidato['instagram']),
                'nome' => $candidato['nome'] ?? '',
                'instagram' => $candidato['instagram'],
                'imagem' => $candidato['imagem'] ?? '',
            ];
        }

        wp_send_json_success(['results' => $resultados]);
    }
}

// Inicializa AJAX
new PressaoPlugin_Ajax();