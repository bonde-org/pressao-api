<?php
/**
 * Classe para gerenciar shortcodes - Com integração da campanha
 * 
 * @package PressaoPlugin
 */

if (!defined('ABSPATH')) {
    exit;
}

$keycloak_url = get_option('pressao_keycloak_url', '');
$client_id = get_option('pressao_client_id', '');
$client_secret = get_option('pressao_client_secret', '');
$api_url = get_option('pressao_api_url', '');

class PressaoPlugin_Shortcode {
    
    private $api;
    
    public function __construct() {
        $this->api = new PressaoPlugin_API();
        add_shortcode('pressao_widget', [$this, 'render_widget']);
        add_shortcode('pressao_form', [$this, 'render_form']);
        add_shortcode('pressao_list', [$this, 'render_list']);
        add_shortcode('pressao_alvos', [$this, 'render_alvos']);
    }
    
    /**
     * Renderiza o widget principal com nome da campanha
     */
    public function render_widget($atts) {
        // Atributos padrão
        $atts = shortcode_atts([
            'title' => get_option('pressao_widget_title', 'Pressão Widget'),
            'campaign' => get_option('pressao_campaign_id', ''),
            'id' => 'pressao-widget-' . uniqid(),
            'show_campaign_name' => 'yes',
            'cache' => '3600'
        ], $atts, 'pressao_widget');
        
        // Sanitização
        $title = sanitize_text_field($atts['title']);
        $campaign_id = sanitize_text_field($atts['campaign']);
        $widget_id = sanitize_text_field($atts['id']);
        $show_campaign_name = sanitize_text_field($atts['show_campaign_name']);
        $cache_time = intval($atts['cache']);
        
        // Busca nome da campanha
        $campaign_name = '';
        $campaign_data = null;
        
        if (!empty($campaign_id) && $show_campaign_name === 'yes') {
            $result = $this->api->get_campanha_cached($campaign_id, $cache_time);
            
            if (!is_wp_error($result) && $result['success'] && !empty($result['data'])) {
                $campaign_data = $result['data'];
                $campaign_name = isset($campaign_data['nome']) ? $campaign_data['nome'] : '';
            }
        }
        
        // Inicia buffer de saída
        ob_start();
        ?>
        <div id="<?php echo esc_attr($widget_id); ?>" 
             class="pressao-widget-container"
             data-campaign="<?php echo esc_attr($campaign_id); ?>"
             data-widget-id="<?php echo esc_attr($widget_id); ?>"
             data-campaign-data='<?php echo json_encode($campaign_data); ?>'>
            
            <!-- Nome do widget + Nome da campanha -->
            <div class="pressao-widget-header">
                <span class="pressao-widget-name">
                    <?php echo esc_html($title); ?>
                </span>
                
                <?php if (!empty($campaign_name)) : ?>
                    <span class="pressao-widget-campaign">
                        <span class="pressao-campaign-separator">|</span>
                        <span class="pressao-campaign-name">
                            <?php echo esc_html($campaign_name); ?>
                        </span>
                    </span>
                <?php endif; ?>
            </div>
            
            <!-- Container para conteúdo dinâmico -->
            <div class="pressao-widget-content" style="display: none;">
                <!-- Conteúdo será carregado via JavaScript -->
            </div>
        </div>
        <?php
        
        return ob_get_clean();
    }
    
    /**
     * Renderiza apenas o formulário
     */
    public function render_form($atts) {
        $atts = shortcode_atts([
            'campaign' => get_option('pressao_campaign_id', ''),
            'button_text' => __('Enviar', 'pressao-plugin'),
            'id' => 'pressao-form-' . uniqid()
        ], $atts, 'pressao_form');
        
        $campaign = sanitize_text_field($atts['campaign']);
        $button_text = sanitize_text_field($atts['button_text']);
        $form_id = sanitize_text_field($atts['id']);
        
        ob_start();
        ?>
        <div id="<?php echo esc_attr($form_id); ?>" 
             class="pressao-form-container"
             data-campaign="<?php echo esc_attr($campaign); ?>">
            
            <div class="pressao-form-name">
                <?php esc_html_e('Formulário Pressão', 'pressao-plugin'); ?>
            </div>
            
            <div class="pressao-form-content" style="display: none;">
                <!-- Conteúdo será carregado via JavaScript -->
            </div>
        </div>
        <?php
        return ob_get_clean();
    }
    
    /**
     * Renderiza apenas a lista
     */
    public function render_list($atts) {
        $atts = shortcode_atts([
            'campaign' => get_option('pressao_campaign_id', ''),
            'limit' => 10,
            'id' => 'pressao-list-' . uniqid()
        ], $atts, 'pressao_list');
        
        $campaign = sanitize_text_field($atts['campaign']);
        $limit = intval($atts['limit']);
        $list_id = sanitize_text_field($atts['id']);
        
        ob_start();
        ?>
        <div id="<?php echo esc_attr($list_id); ?>" 
             class="pressao-list-container"
             data-campaign="<?php echo esc_attr($campaign); ?>"
             data-limit="<?php echo esc_attr($limit); ?>">
            
            <div class="pressao-list-name">
                <?php esc_html_e('Lista Pressão', 'pressao-plugin'); ?>
            </div>
            
            <div class="pressao-list-content" style="display: none;">
                <!-- Conteúdo será carregado via JavaScript -->
            </div>
        </div>
        <?php
        return ob_get_clean();
    }

    /**
     * Renderiza a lista de alvos com botões de ação
     */
    public function render_alvos($atts) {
        $atts = shortcode_atts([
            'campaign' => get_option('pressao_campaign_id', ''),
            'limit' => 10,
            'show_contact' => 'yes',
            'show_actions' => 'yes',
            'show_ativista_form' => 'no',
            'action_label' => __('Agir', 'pressao-plugin'),
            'action_done_label' => __('Ação realizada ✓', 'pressao-plugin'),
            'canal' => 'email',
            'template_id' => '',
            'class' => '',
            'id' => 'pressao-alvos-' . uniqid()
        ], $atts, 'pressao_alvos');
        
        $campanha_id = sanitize_text_field($atts['campaign']);
        $limit = intval($atts['limit']);
        $show_contact = sanitize_text_field($atts['show_contact']);
        $show_actions = sanitize_text_field($atts['show_actions']);
        $show_ativista_form = sanitize_text_field($atts['show_ativista_form']);
        $action_label = sanitize_text_field($atts['action_label']);
        $action_done_label = sanitize_text_field($atts['action_done_label']);
        $canal = sanitize_text_field($atts['canal']);
        $template_id = sanitize_text_field($atts['template_id']);
        $class = sanitize_text_field($atts['class']);
        $alvos_id = sanitize_text_field($atts['id']);
        
        if (empty($campanha_id)) {
            return '<p class="pressao-error">' . esc_html__('ID da campanha não informado', 'pressao-plugin') . '</p>';
        }
        
        // Busca alvos
        $api = new PressaoPlugin_API();
        $result = $api->get_alvos_cached($campanha_id, [], 300);
        
        if (is_wp_error($result)) {
            return sprintf(
                '<p class="pressao-error">%s</p>',
                esc_html($result->get_error_message())
            );
        }
        
        if (!$result['success'] || empty($result['data'])) {
            return '<p class="pressao-empty">' . esc_html__('Nenhum alvo encontrado para esta campanha.', 'pressao-plugin') . '</p>';
        }
        
        $alvos = $result['data'];
        
        // Aplica limite
        if ($limit > 0) {
            $alvos = array_slice($alvos, 0, $limit);
        }
        
        // Gera nonce para ações
        $nonce = wp_create_nonce('pressao_acao_nonce');
        
        // Renderiza
        ob_start();
        ?>
        <div id="<?php echo esc_attr($alvos_id); ?>" 
            class="pressao-alvos <?php echo esc_attr($class); ?>"
            data-campaign="<?php echo esc_attr($campanha_id); ?>"
            data-nonce="<?php echo esc_attr($nonce); ?>"
            data-canal="<?php echo esc_attr($canal); ?>"
            data-template-id="<?php echo esc_attr($template_id); ?>">
            
            <div class="pressao-alvos-header">
                <h3><?php esc_html_e('Alvos da Campanha', 'pressao-plugin'); ?></h3>
                <span class="pressao-alvos-count"><?php echo count($alvos); ?></span>
            </div>
            
            <ul class="pressao-alvos-list">
                <?php foreach ($alvos as $alvo) : 
                    $alvo_id = $alvo['id'];
                    $action_state = $this->get_alvo_action_state($alvo_id);
                ?>
                    <li class="pressao-alvo-item <?php echo $action_state ? 'action-done' : ''; ?>" 
                        data-alvo-id="<?php echo esc_attr($alvo_id); ?>">
                        
                        <div class="pressao-alvo-info">
                            <div class="pressao-alvo-detalhes">
                                <strong class="pressao-alvo-nome"><?php echo esc_html($alvo['nome']); ?></strong>
                                
                                <?php if ($show_contact === 'yes' && !empty($alvo['contato'])) : ?>
                                    <span class="pressao-alvo-contato">
                                        <?php echo esc_html($alvo['contato']); ?>
                                        <?php if (!empty($alvo['tipo_contato'])) : ?>
                                            <span class="pressao-alvo-tipo">(<?php echo esc_html($alvo['tipo_contato']); ?>)</span>
                                        <?php endif; ?>
                                    </span>
                                <?php endif; ?>
                            </div>
                            
                            <?php if ($show_actions === 'yes') : ?>
                                <div class="pressao-alvo-actions">
                                    <?php if ($action_state) : ?>
                                        <span class="pressao-action-done">
                                            <?php echo esc_html($action_done_label); ?>
                                            <span class="pressao-action-time">
                                                <?php echo $this->format_action_time($action_state); ?>
                                            </span>
                                        </span>
                                    <?php else : ?>
                                        <?php if ($show_ativista_form === 'yes') : ?>
                                            <button type="button" 
                                                    class="pressao-action-toggle"
                                                    data-alvo-id="<?php echo esc_attr($alvo_id); ?>">
                                                <?php echo esc_html($action_label); ?>
                                            </button>
                                            
                                            <div class="pressao-ativista-form" style="display: none;">
                                                <div class="pressao-form-group">
                                                    <input type="text" 
                                                        class="pressao-ativista-nome" 
                                                        placeholder="<?php esc_attr_e('Seu nome', 'pressao-plugin'); ?>"
                                                        required />
                                                </div>
                                                <div class="pressao-form-group">
                                                    <input type="email" 
                                                        class="pressao-ativista-email" 
                                                        placeholder="<?php esc_attr_e('Seu email', 'pressao-plugin'); ?>" />
                                                </div>
                                                <div class="pressao-form-group">
                                                    <input type="tel" 
                                                        class="pressao-ativista-telefone" 
                                                        placeholder="<?php esc_attr_e('Seu telefone', 'pressao-plugin'); ?>" />
                                                </div>
                                                <button type="button" 
                                                        class="pressao-action-submit"
                                                        data-alvo-id="<?php echo esc_attr($alvo_id); ?>"
                                                        data-campaign="<?php echo esc_attr($campanha_id); ?>">
                                                    <?php esc_html_e('Confirmar', 'pressao-plugin'); ?>
                                                </button>
                                            </div>
                                        <?php else : ?>
                                            <button type="button" 
                                                    class="pressao-action-button"
                                                    data-alvo-id="<?php echo esc_attr($alvo_id); ?>"
                                                    data-campaign="<?php echo esc_attr($campanha_id); ?>">
                                                <?php echo esc_html($action_label); ?>
                                            </button>
                                        <?php endif; ?>
                                    <?php endif; ?>
                                </div>
                            <?php endif; ?>
                        </div>
                        
                        <?php if (!empty($alvo['metadados'])) : ?>
                            <div class="pressao-alvo-metadados">
                                <small><?php esc_html_e('Metadados:', 'pressao-plugin'); ?></small>
                                <pre><?php echo esc_html(json_encode($alvo['metadados'], JSON_PRETTY_PRINT)); ?></pre>
                            </div>
                        <?php endif; ?>
                    </li>
                <?php endforeach; ?>
            </ul>
            
            <?php if ($result['cached']) : ?>
                <div class="pressao-cache-info">
                    <small><?php esc_html_e('Dados em cache', 'pressao-plugin'); ?></small>
                </div>
            <?php endif; ?>
        </div>
        <?php
        
        return ob_get_clean();
    }

    /**
     * Verifica se o usuário já fez ação para um alvo
     */
    private function get_alvo_action_state($alvo_id) {
        // Tenta recuperar do localStorage via JavaScript
        // No PHP, usamos session ou cookie como fallback
        $actions = isset($_COOKIE['pressao_acoes_realizadas']) 
            ? json_decode(stripslashes($_COOKIE['pressao_acoes_realizadas']), true) 
            : [];
        
        return isset($actions[$alvo_id]) ? $actions[$alvo_id] : false;
    }

    /**
     * Formata o tempo da ação
     */
    private function format_action_time($timestamp) {
        $diff = time() - $timestamp;
        
        if ($diff < 60) {
            return __('agora', 'pressao-plugin');
        } elseif ($diff < 3600) {
            $minutes = floor($diff / 60);
            return sprintf(_n('%d minuto', '%d minutos', $minutes, 'pressao-plugin'), $minutes);
        } elseif ($diff < 86400) {
            $hours = floor($diff / 3600);
            return sprintf(_n('%d hora', '%d horas', $hours, 'pressao-plugin'), $hours);
        } else {
            $days = floor($diff / 86400);
            return sprintf(_n('%d dia', '%d dias', $days, 'pressao-plugin'), $days);
        }
    }
}

// Inicializa o shortcode
new PressaoPlugin_Shortcode();