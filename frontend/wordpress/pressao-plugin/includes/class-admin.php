<?php
/**
 * Classe de administração - Versão Simplificada
 * 
 * @package PressaoPlugin
 */

if (!defined('ABSPATH')) {
    exit;
}

class PressaoPlugin_Admin {
    
    public function __construct() {
        add_action('admin_menu', [$this, 'add_admin_menu']);
        add_action('admin_init', [$this, 'register_settings']);
    }
    
    public function add_admin_menu() {
        add_options_page(
            __('Pressão Plugin', 'pressao-plugin'),
            __('Pressão Plugin', 'pressao-plugin'),
            'manage_options',
            'pressao-settings',
            [$this, 'render_settings_page']
        );
    }
    
    public function register_settings() {
        // Configurações principais
        register_setting('pressao_settings_group', 'pressao_keycloak_url');
        register_setting('pressao_settings_group', 'pressao_realm');
        register_setting('pressao_settings_group', 'pressao_client_id');
        register_setting('pressao_settings_group', 'pressao_client_secret');
        register_setting('pressao_settings_group', 'pressao_api_url');
        register_setting('pressao_settings_group', 'pressao_campaign_id');
        register_setting('pressao_settings_group', 'pressao_widget_title');
        
        // Seção: Autenticação
        add_settings_section(
            'pressao_auth_section',
            __('Configurações de Autenticação', 'pressao-plugin'),
            null,
            'pressao-settings'
        );
        
        add_settings_field(
            'pressao_keycloak_url',
            __('URL do Keycloak', 'pressao-plugin'),
            [$this, 'render_text_field'],
            'pressao-settings',
            'pressao_auth_section',
            ['field' => 'pressao_keycloak_url', 'type' => 'url']
        );
        
        add_settings_field(
            'pressao_realm',
            __('Realm', 'pressao-plugin'),
            [$this, 'render_text_field'],
            'pressao-settings',
            'pressao_auth_section',
            [
                'field' => 'pressao_realm',
                'description' => __('Ex: pressao, master, etc.', 'pressao-plugin')
            ]
        );

        add_settings_field(
            'pressao_client_id',
            __('Client ID', 'pressao-plugin'),
            [$this, 'render_text_field'],
            'pressao-settings',
            'pressao_auth_section',
            ['field' => 'pressao_client_id']
        );
        
        add_settings_field(
            'pressao_client_secret',
            __('Client Secret', 'pressao-plugin'),
            [$this, 'render_password_field'],
            'pressao-settings',
            'pressao_auth_section',
            ['field' => 'pressao_client_secret']
        );
        
        add_settings_field(
            'pressao_api_url',
            __('URL da API', 'pressao-plugin'),
            [$this, 'render_text_field'],
            'pressao-settings',
            'pressao_auth_section',
            ['field' => 'pressao_api_url', 'type' => 'url']
        );
        
        // Seção: Widget
        add_settings_section(
            'pressao_widget_section',
            __('Configurações do Widget', 'pressao-plugin'),
            null,
            'pressao-settings'
        );
        
        add_settings_field(
            'pressao_campaign_id',
            __('ID da Campanha', 'pressao-plugin'),
            [$this, 'render_text_field'],
            'pressao-settings',
            'pressao_widget_section',
            ['field' => 'pressao_campaign_id']
        );
        
        add_settings_field(
            'pressao_widget_title',
            __('Título do Widget', 'pressao-plugin'),
            [$this, 'render_text_field'],
            'pressao-settings',
            'pressao_widget_section',
            ['field' => 'pressao_widget_title']
        );

        // Seção: Ativista
        add_settings_section(
            'pressao_ativista_section',
            __('Configurações do Ativista', 'pressao-plugin'),
            null,
            'pressao-settings'
        );

        add_settings_field(
            'pressao_ativista_confirm_interval',
            __('Intervalo para confirmar identidade (minutos)', 'pressao-plugin'),
            [$this, 'render_number_field'],
            'pressao-settings',
            'pressao_ativista_section',
            [
                'field' => 'pressao_ativista_confirm_interval',
                'default' => 10,
                'min' => 1,
                'max' => 60
            ]
        );
        
        add_settings_field(
            'pressao_ativista_form_title',
            __('Título do formulário de identificação', 'pressao-plugin'),
            [$this, 'render_text_field'],
            'pressao-settings',
            'pressao_ativista_section',
            ['field' => 'pressao_ativista_form_title']
        );
    }
    
    public function render_text_field($args) {
        $field = $args['field'];
        $type = isset($args['type']) ? $args['type'] : 'text';
        $value = get_option($field, '');
        ?>
        <input type="<?php echo esc_attr($type); ?>" 
               name="<?php echo esc_attr($field); ?>" 
               value="<?php echo esc_attr($value); ?>" 
               class="regular-text" />
        <?php
    }
    
    public function render_password_field($args) {
        $field = $args['field'];
        $value = get_option($field, '');
        ?>
        <input type="password" 
               name="<?php echo esc_attr($field); ?>" 
               value="<?php echo esc_attr($value); ?>" 
               class="regular-text" />
        <p class="description">
            <?php esc_html_e('O Client Secret fica guardado no servidor.', 'pressao-plugin'); ?>
        </p>
        <?php
    }
    
    public function render_settings_page() {
        if (!current_user_can('manage_options')) {
            wp_die(__('Sem permissão.', 'pressao-plugin'));
        }
        ?>
        <div class="wrap">
            <h1><?php esc_html_e('Pressão Plugin - Configurações', 'pressao-plugin'); ?></h1>
            
            <form method="post" action="options.php">
                <?php
                settings_fields('pressao_settings_group');
                do_settings_sections('pressao-settings');
                submit_button();
                ?>
            </form>
            
            <div class="pressao-usage">
                <h2><?php esc_html_e('Como usar', 'pressao-plugin'); ?></h2>
                <p><?php esc_html_e('Shortcodes disponíveis:', 'pressao-plugin'); ?></p>
                <ul>
                    <li><code>[pressao_widget]</code> - <?php esc_html_e('Widget principal', 'pressao-plugin'); ?></li>
                    <li><code>[pressao_form]</code> - <?php esc_html_e('Apenas formulário', 'pressao-plugin'); ?></li>
                    <li><code>[pressao_list]</code> - <?php esc_html_e('Apenas lista', 'pressao-plugin'); ?></li>
                    <li><code>[pressao_alvos]</code> - <?php esc_html_e('Lista de alvos com ações', 'pressao-plugin'); ?></li>
                </ul>
                
                <p><?php esc_html_e('Exemplos:', 'pressao-plugin'); ?></p>
                <code>[pressao_widget title="Meu Widget"]</code>
                <br>
                <code>[pressao_form button_text="Enviar"]</code>
                <br>
                <code>[pressao_list limit="5"]</code>
                <br>
                <code>[pressao_alvos campaign="123" show_ativista_form="yes"]</code>
                
                <div class="pressao-lgpd-info" style="margin-top: 20px; padding: 15px; background: #f0f8ff; border-radius: 6px; border-left: 4px solid #0073aa;">
                    <h3 style="margin-top: 0;"><?php esc_html_e('Sobre a LGPD', 'pressao-plugin'); ?></h3>
                    <p style="margin-bottom: 0;">
                        <?php esc_html_e('O plugin armazena apenas o nome do ativista no navegador para identificação. Email e telefone são opcionais e só são enviados ao servidor quando o ativista realiza uma ação. A confirmação de identidade exibe apenas o nome, respeitando a Lei Geral de Proteção de Dados.', 'pressao-plugin'); ?>
                    </p>
                </div>
            </div>
        </div>
        <?php
    }

    public function render_number_field($args) {
        $field = $args['field'];
        $value = get_option($field, $args['default'] ?? 10);
        $min = $args['min'] ?? 1;
        $max = $args['max'] ?? 60;
        ?>
        <input type="number" 
               name="<?php echo esc_attr($field); ?>" 
               value="<?php echo esc_attr($value); ?>" 
               min="<?php echo esc_attr($min); ?>" 
               max="<?php echo esc_attr($max); ?>" 
               class="small-text" />
        <p class="description"><?php esc_html_e('Tempo em minutos para perguntar novamente se é o mesmo ativista.', 'pressao-plugin'); ?></p>
        <?php
    }
}

new PressaoPlugin_Admin();