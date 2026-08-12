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
}

// Inicializa o shortcode
new PressaoPlugin_Shortcode();