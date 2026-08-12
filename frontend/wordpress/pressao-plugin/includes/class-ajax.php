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
    }
    
    /**
     * AJAX: Obtém dados da campanha
     */
    public function ajax_get_campanha() {
        // Verifica nonce
        if (!isset($_POST['nonce']) || !wp_verify_nonce($_POST['nonce'], 'pressao_widget_nonce')) {
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
}

// Inicializa AJAX
new PressaoPlugin_Ajax();