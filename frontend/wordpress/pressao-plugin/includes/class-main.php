<?php
/**
 * Classe principal de funcionalidades do plugin
 * 
 * @package PressaoPlugin
 */

if (!defined('ABSPATH')) {
    exit;
}

class PressaoPlugin_Main {
    
    /**
     * Construtor
     */
    public function __construct() {
        // Adiciona hooks específicos
        add_action('wp_footer', [$this, 'maybe_render_widget_footer']);
    }
    
    /**
     * Renderiza widget no footer se necessário
     * Pode ser usado para widgets flutuantes
     */
    public function maybe_render_widget_footer() {
        // Verifica se deve renderizar no footer
        if (apply_filters('pressao_render_widget_footer', false)) {
            echo do_shortcode('[pressao_widget]');
        }
    }
    
    /**
     * Obtém token do Keycloak (será expandido depois)
     */
    public function get_keycloak_token() {
        // Placeholder - será implementado depois
        return 'token_placeholder';
    }
}