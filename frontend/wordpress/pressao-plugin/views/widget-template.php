<?php
/**
 * Template do widget
 * 
 * @package PressaoPlugin
 */

if (!defined('ABSPATH')) {
    exit;
}

$widget_id = 'pressao-widget-' . uniqid();
?>
<div id="<?php echo esc_attr($widget_id); ?>" 
     class="pressao-widget pressao-theme-<?php echo esc_attr($theme); ?>"
     data-campaign="<?php echo esc_attr($campaign); ?>">
    
    <div class="pressao-widget-header">
        <h3><?php echo esc_html($title); ?></h3>
        <button class="pressao-widget-toggle">
            <span class="dashicons dashicons-arrow-down-alt2"></span>
        </button>
    </div>
    
    <div class="pressao-widget-body" style="display: none;">
        <div class="pressao-widget-loading">
            <?php esc_html_e('Carregando...', 'pressao-plugin'); ?>
        </div>
        
        <div class="pressao-widget-content" style="display: none;">
            <!-- Conteúdo do widget -->
            <p><?php esc_html_e('Hello World! Este é o Pressão Plugin.', 'pressao-plugin'); ?></p>
            
            <form class="pressao-action-form">
                <textarea name="description" placeholder="<?php esc_attr_e('Digite sua ação...', 'pressao-plugin'); ?>"></textarea>
                <button type="submit"><?php esc_html_e('Enviar', 'pressao-plugin'); ?></button>
            </form>
        </div>
    </div>
</div>