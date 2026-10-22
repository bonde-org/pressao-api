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

    const CONEXAO_STATUS_TRANSIENT = 'pressao_conexao_status';
    const NONCE_CAMPANHA = 'pressao_admin_campanha';
    const NONCE_REDES = 'pressao_admin_redes';
    const CONEXAO_FIELDS = [
        'pressao_keycloak_url',
        'pressao_realm',
        'pressao_client_id',
        'pressao_client_secret',
        'pressao_api_url',
    ];
    
    public function __construct() {
        add_action('admin_menu', [$this, 'add_admin_menu']);
        add_action('admin_init', [$this, 'register_settings']);
        add_filter('wp_redirect', [$this, 'preserve_settings_tab_on_redirect']);
        add_action('wp_ajax_pressao_admin_buscar_campanhas', [$this, 'ajax_buscar_campanhas']);
        add_action('wp_ajax_pressao_admin_criar_campanha', [$this, 'ajax_criar_campanha']);
        add_action('wp_ajax_pressao_admin_atualizar_campanha', [$this, 'ajax_atualizar_campanha']);
        add_action('wp_ajax_pressao_admin_vincular_campanha', [$this, 'ajax_vincular_campanha']);
        add_action('wp_ajax_pressao_admin_salvar_alvo_social', [$this, 'ajax_salvar_alvo_social']);
        add_action('wp_ajax_pressao_admin_salvar_template_social', [$this, 'ajax_salvar_template_social']);
        add_action('wp_ajax_pressao_admin_deletar_template_social', [$this, 'ajax_deletar_template_social']);
    }
    
    public function add_admin_menu() {
        add_menu_page(
            __('Pressão', 'pressao-plugin'),
            __('Pressão', 'pressao-plugin'),
            'manage_options',
            'pressao-settings',
            [$this, 'render_settings_page'],
            'dashicons-megaphone',
            58
        );
        remove_submenu_page('pressao-settings', 'pressao-settings');
    }

    /**
     * URL do painel Pressão (admin.php?page=pressao-settings).
     *
     * @param array<string, mixed> $args Query extra (ex.: tab, cpage).
     * @return string
     */
    public static function settings_url(array $args = []) {
        $args = array_merge(['page' => 'pressao-settings'], $args);
        return add_query_arg($args, admin_url('admin.php'));
    }

    /**
     * Campanha vinculada a este site (UUID gravado, sem probe à API).
     */
    public static function has_campaign() {
        $id = get_option('pressao_campaign_id', '');
        return is_string($id) && $id !== '' && wp_is_uuid($id);
    }

    /**
     * @param string $slug
     * @param bool   $conexao_ok
     * @param bool   $campanha_ok
     * @return bool
     */
    private function tab_esta_liberada($slug, $conexao_ok, $campanha_ok) {
        if (in_array($slug, ['conexao', 'documentacao'], true)) {
            return true;
        }
        if ($slug === 'campanha') {
            return $conexao_ok;
        }
        return $conexao_ok && $campanha_ok;
    }

    /**
     * Mantém ?tab= após salvar options.php (option group pressao_settings_{tab}).
     *
     * @param string $location
     * @return string
     */
    public function preserve_settings_tab_on_redirect($location) {
        if (!is_string($location) || $location === '') {
            return $location;
        }
        if (empty($_POST['option_page']) || strpos((string) $_POST['option_page'], 'pressao_settings_') !== 0) {
            return $location;
        }
        $tab = sanitize_key(substr((string) $_POST['option_page'], strlen('pressao_settings_')));
        $tabs = $this->get_settings_tabs();
        if (!isset($tabs[$tab])) {
            return $location;
        }
        if ($tab === 'conexao') {
            delete_transient(self::CONEXAO_STATUS_TRANSIENT);
        }
        return add_query_arg('tab', $tab, $location);
    }

    /**
     * Abas da página de configurações (slug => rótulo).
     *
     * @return array<string, string>
     */
    public function get_settings_tabs() {
        return [
            'conexao' => __('Conexão', 'pressao-plugin'),
            'campanha' => __('Campanha', 'pressao-plugin'),
            'geral' => __('Geral', 'pressao-plugin'),
            'redes-sociais' => __('Redes Sociais', 'pressao-plugin'),
            'apoiadores' => __('Apoiadores', 'pressao-plugin'),
            'compartilhamento' => __('Compartilhamento', 'pressao-plugin'),
            'documentacao' => __('Documentação', 'pressao-plugin'),
        ];
    }

    /**
     * @return string
     */
    public function get_current_tab() {
        $tabs = $this->get_settings_tabs();
        $tab = isset($_GET['tab']) ? sanitize_key(wp_unslash($_GET['tab'])) : 'conexao';
        if ($tab === 'candidatos') {
            $tab = 'redes-sociais';
        }
        return isset($tabs[$tab]) ? $tab : 'conexao';
    }

    /**
     * Página Settings API da aba (exceto documentação, sem form).
     *
     * @param string $tab
     * @return string
     */
    private function get_settings_page_for_tab($tab) {
        return 'pressao-settings-' . $tab;
    }

    /**
     * Option group da aba (isolado para o options.php não zerar outras abas).
     *
     * @param string $tab
     * @return string
     */
    private function get_option_group_for_tab($tab) {
        return 'pressao_settings_' . $tab;
    }

    public function register_settings() {
        // Conexão
        $page_conexao = $this->get_settings_page_for_tab('conexao');
        $group_conexao = $this->get_option_group_for_tab('conexao');
        register_setting($group_conexao, 'pressao_keycloak_url');
        register_setting($group_conexao, 'pressao_realm');
        register_setting($group_conexao, 'pressao_client_id');
        register_setting($group_conexao, 'pressao_client_secret');
        register_setting($group_conexao, 'pressao_api_url');

        add_settings_section(
            'pressao_auth_section',
            __('Conexão com a API', 'pressao-plugin'),
            null,
            $page_conexao
        );

        add_settings_field(
            'pressao_keycloak_url',
            __('URL do Keycloak', 'pressao-plugin'),
            [$this, 'render_text_field'],
            $page_conexao,
            'pressao_auth_section',
            ['field' => 'pressao_keycloak_url', 'type' => 'url']
        );

        add_settings_field(
            'pressao_realm',
            __('Realm', 'pressao-plugin'),
            [$this, 'render_text_field'],
            $page_conexao,
            'pressao_auth_section',
            [
                'field' => 'pressao_realm',
                'description' => __('Ex: pressao, master, etc.', 'pressao-plugin'),
            ]
        );

        add_settings_field(
            'pressao_client_id',
            __('Client ID', 'pressao-plugin'),
            [$this, 'render_text_field'],
            $page_conexao,
            'pressao_auth_section',
            ['field' => 'pressao_client_id']
        );

        add_settings_field(
            'pressao_client_secret',
            __('Client Secret', 'pressao-plugin'),
            [$this, 'render_password_field'],
            $page_conexao,
            'pressao_auth_section',
            ['field' => 'pressao_client_secret']
        );

        add_settings_field(
            'pressao_api_url',
            __('URL da API', 'pressao-plugin'),
            [$this, 'render_text_field'],
            $page_conexao,
            'pressao_auth_section',
            ['field' => 'pressao_api_url', 'type' => 'url']
        );

        // Geral (widget + ativista) — campaign_id vive na aba Campanha via AJAX
        $page_geral = $this->get_settings_page_for_tab('geral');
        $group_geral = $this->get_option_group_for_tab('geral');
        register_setting($group_geral, 'pressao_widget_title');
        register_setting($group_geral, 'pressao_privacidade_url', [
            'type' => 'string',
            'sanitize_callback' => 'esc_url_raw',
            'default' => '',
        ]);
        register_setting($group_geral, 'pressao_ativista_confirm_interval', [
            'type' => 'integer',
            'sanitize_callback' => [$this, 'sanitize_ativista_confirm_interval'],
            'default' => 10,
        ]);
        register_setting($group_geral, 'pressao_ativista_form_title');
        register_setting($group_geral, 'pressao_session_duration');

        add_settings_section(
            'pressao_widget_section',
            __('Widget do site', 'pressao-plugin'),
            [$this, 'render_geral_widget_section'],
            $page_geral
        );

        add_settings_field(
            'pressao_widget_title',
            __('Título do Widget', 'pressao-plugin'),
            [$this, 'render_text_field'],
            $page_geral,
            'pressao_widget_section',
            ['field' => 'pressao_widget_title']
        );

        add_settings_field(
            'pressao_privacidade_url',
            __('Política de Privacidade', 'pressao-plugin'),
            [$this, 'render_text_field'],
            $page_geral,
            'pressao_widget_section',
            [
                'field' => 'pressao_privacidade_url',
                'type' => 'url',
                'description' => __(
                    'URL do texto de Política de Privacidade abaixo do botão de envio, em qualquer formulário do widget. Se vazio, usa a página de privacidade do WordPress (Ajustes → Privacidade), quando existir.',
                    'pressao-plugin'
                ),
            ]
        );

        add_settings_section(
            'pressao_ativista_section',
            __('Sessão e identificação do ativista', 'pressao-plugin'),
            null,
            $page_geral
        );

        add_settings_field(
            'pressao_ativista_confirm_interval',
            __('Intervalo para confirmar identidade (minutos)', 'pressao-plugin'),
            [$this, 'render_number_field'],
            $page_geral,
            'pressao_ativista_section',
            [
                'field' => 'pressao_ativista_confirm_interval',
                'default' => 10,
                'min' => 1,
                'max' => 60,
            ]
        );

        add_settings_field(
            'pressao_ativista_form_title',
            __('Título do formulário de identificação', 'pressao-plugin'),
            [$this, 'render_text_field'],
            $page_geral,
            'pressao_ativista_section',
            ['field' => 'pressao_ativista_form_title']
        );

        add_settings_field(
            'pressao_session_duration',
            __('Duração da sessão do ativista', 'pressao-plugin'),
            [$this, 'render_session_duration_field'],
            $page_geral,
            'pressao_ativista_section'
        );

        // Opções do [pressao_fluxo] — moradia temporária na Geral (a revisar).
        register_setting($group_geral, 'pressao_fluxo_limite_candidatos', [
            'sanitize_callback' => [$this, 'sanitize_fluxo_limite_candidatos'],
            'default' => 5,
        ]);
        register_setting($group_geral, 'pressao_fluxo_countdown_abrir', [
            'type' => 'boolean',
            'sanitize_callback' => [$this, 'sanitize_fluxo_countdown_abrir'],
            'default' => 0,
        ]);
        register_setting($group_geral, 'pressao_fluxo_ajuda', [
            'sanitize_callback' => [$this, 'sanitize_fluxo_ajuda'],
            'default' => [
                'titulo' => '',
                'conteudo' => '',
            ],
        ]);

        add_settings_section(
            'pressao_fluxo_section',
            __('Opções do fluxo', 'pressao-plugin'),
            [$this, 'render_candidatos_pressao_section'],
            $page_geral
        );

        add_settings_field(
            'pressao_fluxo_limite_candidatos',
            __('Limite de marcação (fluxo)', 'pressao-plugin'),
            [$this, 'render_fluxo_limite_field'],
            $page_geral,
            'pressao_fluxo_section'
        );

        add_settings_field(
            'pressao_fluxo_countdown_abrir',
            __('Contador antes de abrir Instagram', 'pressao-plugin'),
            [$this, 'render_fluxo_countdown_abrir_field'],
            $page_geral,
            'pressao_fluxo_section'
        );

        add_settings_field(
            'pressao_fluxo_ajuda',
            __('Ajuda do fluxo (?)', 'pressao-plugin'),
            [$this, 'render_fluxo_ajuda_field'],
            $page_geral,
            'pressao_fluxo_section'
        );

        // Apoiadores: listagem AJAX (sem options.php); tools CSV abaixo

        // Compartilhamento
        $page_share = $this->get_settings_page_for_tab('compartilhamento');
        $group_share = $this->get_option_group_for_tab('compartilhamento');
        register_setting($group_share, 'pressao_compartilhamento', [
            'sanitize_callback' => [$this, 'sanitize_compartilhamento'],
            'default' => [],
        ]);

        add_settings_section(
            'pressao_compartilhamento_section',
            __('Compartilhamento', 'pressao-plugin'),
            null,
            $page_share
        );

        add_settings_field(
            'pressao_compartilhamento',
            __('Configuração', 'pressao-plugin'),
            [$this, 'render_compartilhamento_field'],
            $page_share,
            'pressao_compartilhamento_section'
        );
    }
    
    public function render_text_field($args) {
        $field = $args['field'];
        $type = isset($args['type']) ? $args['type'] : 'text';
        $constant = strtoupper($field);
        $overridden = defined($constant);
        $value = $overridden ? constant($constant) : get_option($field, '');
        ?>
        <input type="<?php echo esc_attr($type); ?>"
               name="<?php echo esc_attr($field); ?>"
               value="<?php echo esc_attr($value); ?>"
               class="regular-text"
               <?php disabled($overridden); ?> />
        <?php if ($overridden) : ?>
            <p class="description">
                <?php printf(esc_html__('Definido via wp-config.php (constante %s), não editável aqui.', 'pressao-plugin'), esc_html($constant)); ?>
            </p>
        <?php elseif (!empty($args['description'])) : ?>
            <p class="description"><?php echo esc_html($args['description']); ?></p>
        <?php endif; ?>
        <?php
    }

    public function render_password_field($args) {
        $field = $args['field'];
        $constant = strtoupper($field);
        $overridden = defined($constant);
        $value = $overridden ? constant($constant) : get_option($field, '');
        ?>
        <input type="password"
               name="<?php echo esc_attr($field); ?>"
               value="<?php echo esc_attr($value); ?>"
               class="regular-text"
               <?php disabled($overridden); ?> />
        <p class="description">
            <?php if ($overridden) : ?>
                <?php printf(esc_html__('Definido via wp-config.php (constante %s), não editável aqui.', 'pressao-plugin'), esc_html($constant)); ?>
            <?php else : ?>
                <?php esc_html_e('O Client Secret fica guardado no servidor.', 'pressao-plugin'); ?>
            <?php endif; ?>
        </p>
        <?php
    }
    
    /**
     * @return array<int, string>
     */
    public static function conexao_constants() {
        $out = [];
        foreach (self::CONEXAO_FIELDS as $field) {
            $constant = strtoupper($field);
            if (defined($constant)) {
                $out[] = $constant;
            }
        }
        return $out;
    }

    public static function has_editable_conexao_field() {
        return count(self::conexao_constants()) < count(self::CONEXAO_FIELDS);
    }

    /**
     * @param string $url
     * @return string
     */
    private static function host_from_url($url) {
        $host = wp_parse_url((string) $url, PHP_URL_HOST);
        return is_string($host) && $host !== '' ? $host : (string) $url;
    }

    /**
     * @param PressaoPlugin_API $api
     * @param bool              $fresh
     * @return array{ok: bool, message: string, checked_at: int}
     */
    private function get_conexao_status(PressaoPlugin_API $api, $fresh = false) {
        if (!$fresh) {
            $cached = get_transient(self::CONEXAO_STATUS_TRANSIENT);
            if (is_array($cached) && isset($cached['ok'])) {
                return [
                    'ok' => (bool) $cached['ok'],
                    'message' => (string) ($cached['message'] ?? ''),
                    'checked_at' => (int) ($cached['checked_at'] ?? time()),
                ];
            }
        }

        $result = $api->testar_conexao($fresh);
        $status = [
            'ok' => !is_wp_error($result),
            'message' => is_wp_error($result) ? $result->get_error_message() : '',
            'checked_at' => time(),
        ];
        set_transient(self::CONEXAO_STATUS_TRANSIENT, $status, 60);
        return $status;
    }

    public function render_settings_page() {
        if (!current_user_can('manage_options')) {
            wp_die(__('Sem permissão.', 'pressao-plugin'));
        }

        $api = new PressaoPlugin_API();
        $configured = $api->is_configured();
        $campanha_ok = self::has_campaign();
        $tabs = $this->get_settings_tabs();
        $current_tab = $this->get_current_tab();
        if (!$this->tab_esta_liberada($current_tab, $configured, $campanha_ok)) {
            $current_tab = $configured ? 'campanha' : 'conexao';
        }

        $base_url = self::settings_url();
        $bloqueio_conexao = __('Configure a conexão com a API para usar esta aba.', 'pressao-plugin');
        $bloqueio_campanha = __('Vincule uma campanha para usar esta aba.', 'pressao-plugin');
        ?>
        <div class="wrap pressao-settings-wrap">
            <h1><?php esc_html_e('Pressão', 'pressao-plugin'); ?></h1>

            <nav class="nav-tab-wrapper pressao-settings-tabs" aria-label="<?php esc_attr_e('Seções de configuração', 'pressao-plugin'); ?>">
                <?php foreach ($tabs as $slug => $label) : ?>
                    <?php
                    $ativa = $current_tab === $slug;
                    $liberada = $this->tab_esta_liberada($slug, $configured, $campanha_ok);
                    $bloqueio_titulo = $configured ? $bloqueio_campanha : $bloqueio_conexao;
                    ?>
                    <?php if ($liberada) : ?>
                        <a href="<?php echo esc_url(add_query_arg('tab', $slug, $base_url)); ?>"
                           class="nav-tab<?php echo $ativa ? ' nav-tab-active' : ''; ?>">
                            <?php echo esc_html($label); ?>
                        </a>
                    <?php else : ?>
                        <span class="nav-tab nav-tab-disabled"
                              aria-disabled="true"
                              title="<?php echo esc_attr($bloqueio_titulo); ?>">
                            <?php echo esc_html($label); ?>
                        </span>
                    <?php endif; ?>
                <?php endforeach; ?>
            </nav>

            <div class="pressao-settings-tab-panel" data-tab="<?php echo esc_attr($current_tab); ?>">
                <?php if ($current_tab === 'documentacao') : ?>
                    <?php $this->render_documentacao_tab(); ?>
                <?php elseif ($current_tab === 'conexao') : ?>
                    <?php $this->render_conexao_tab($api, $configured); ?>
                <?php elseif ($current_tab === 'campanha') : ?>
                    <?php $this->render_campanha_tab($api); ?>
                <?php elseif ($current_tab === 'apoiadores') : ?>
                    <h2><?php esc_html_e('Candidatos apoiadores', 'pressao-plugin'); ?></h2>
                    <p><?php esc_html_e('Base dos que já apoiam a pauta: botão/lista do [pressao_fluxo] e shortcode [pressao_candidatos]. Use as ferramentas abaixo para importar CSV ou remover da base.', 'pressao-plugin'); ?></p>
                    <?php PressaoPlugin_Apoiadores_Imagens_Fila::render_admin_card(); ?>
                    <?php PressaoPlugin_Candidatos_Admin_List::render(PressaoPlugin_Candidatos_Admin_List::OPTION_APOIADORES); ?>
                    <?php $this->render_apoiadores_tools(); ?>
                <?php elseif ($current_tab === 'redes-sociais') : ?>
                    <?php $this->render_redes_sociais_tab($api); ?>
                <?php else : ?>
                    <form method="post" action="options.php">
                        <?php
                        $group = $this->get_option_group_for_tab($current_tab);
                        $page = $this->get_settings_page_for_tab($current_tab);
                        settings_fields($group);
                        do_settings_sections($page);
                        submit_button();
                        ?>
                    </form>
                <?php endif; ?>
            </div>
        </div>
        <?php
    }

    /**
     * @param PressaoPlugin_API $api
     * @param bool              $configured
     */
    private function render_conexao_tab(PressaoPlugin_API $api, $configured) {
        $editar = $configured && self::has_editable_conexao_field() && !empty($_GET['editar']);
        if (!$configured || $editar) {
            $this->render_conexao_form($configured);
            return;
        }
        $fresh = !empty($_GET['verificar']);
        if ($fresh) {
            check_admin_referer('pressao_verificar_conexao');
        }
        $this->render_conexao_status_card($api, $this->get_conexao_status($api, $fresh));
    }

    /**
     * @param bool $configured
     */
    private function render_conexao_form($configured) {
        ?>
        <p class="pressao-conexao-intro">
            <?php
            echo $configured
                ? esc_html__('Atualize as credenciais que não estão definidas no wp-config.php. Campos com constante continuam bloqueados.', 'pressao-plugin')
                : esc_html__('Informe o Keycloak e a URL da API para este site usar o Pressão. Depois disso, esta aba mostra só o status da conexão.', 'pressao-plugin');
            ?>
        </p>
        <form method="post" action="options.php">
            <?php
            settings_fields($this->get_option_group_for_tab('conexao'));
            do_settings_sections($this->get_settings_page_for_tab('conexao'));
            submit_button($configured ? __('Salvar credenciais', 'pressao-plugin') : __('Salvar e conectar', 'pressao-plugin'));
            ?>
        </form>
        <?php if ($configured) : ?>
            <p>
                <a href="<?php echo esc_url(self::settings_url(['tab' => 'conexao'])); ?>">
                    <?php esc_html_e('Cancelar', 'pressao-plugin'); ?>
                </a>
            </p>
        <?php endif;
    }

    /**
     * @param PressaoPlugin_API                  $api
     * @param array{ok: bool, message: string, checked_at: int} $status
     */
    private function render_conexao_status_card(PressaoPlugin_API $api, array $status) {
        $ok = !empty($status['ok']);
        $constants = self::conexao_constants();
        $editable = self::has_editable_conexao_field();
        $verificar_url = wp_nonce_url(
            self::settings_url(['tab' => 'conexao', 'verificar' => '1']),
            'pressao_verificar_conexao'
        );
        ?>
        <div class="pressao-conexao-card <?php echo $ok ? 'is-ok' : 'is-fail'; ?>">
            <div class="pressao-conexao-card-head">
                <span class="pressao-conexao-badge"><?php echo $ok ? esc_html__('Conectado', 'pressao-plugin') : esc_html__('Sem conexão', 'pressao-plugin'); ?></span>
                <p class="pressao-conexao-card-title">
                    <?php
                    echo $ok
                        ? esc_html__('A API está respondendo com as credenciais atuais.', 'pressao-plugin')
                        : esc_html($status['message'] !== '' ? $status['message'] : __('Não foi possível falar com a API.', 'pressao-plugin'));
                    ?>
                </p>
            </div>
            <ul class="pressao-conexao-hosts">
                <li>
                    <strong><?php esc_html_e('API', 'pressao-plugin'); ?></strong>
                    <?php echo esc_html(self::host_from_url($api->get_api_url())); ?>
                </li>
                <li>
                    <strong><?php esc_html_e('Keycloak', 'pressao-plugin'); ?></strong>
                    <?php echo esc_html(self::host_from_url($api->get_keycloak_url())); ?>
                    · <?php echo esc_html($api->get_realm()); ?>
                </li>
            </ul>
            <?php if ($constants) : ?>
                <p class="pressao-conexao-selos">
                    <?php
                    printf(
                        /* translators: %s: list of PHP constants */
                        esc_html__('Via wp-config.php: %s', 'pressao-plugin'),
                        esc_html(implode(', ', $constants))
                    );
                    ?>
                </p>
            <?php endif; ?>
            <p class="pressao-conexao-meta">
                <?php
                echo esc_html(
                    sprintf(
                        /* translators: %s: time */
                        __('Verificado às %s', 'pressao-plugin'),
                        wp_date(get_option('time_format'), (int) $status['checked_at'])
                    )
                );
                ?>
            </p>
            <p class="pressao-conexao-actions">
                <a class="button" href="<?php echo esc_url($verificar_url); ?>">
                    <?php esc_html_e('Verificar conexão', 'pressao-plugin'); ?>
                </a>
                <?php if ($editable) : ?>
                    <a class="button" href="<?php echo esc_url(self::settings_url(['tab' => 'conexao', 'editar' => '1'])); ?>">
                        <?php esc_html_e('Editar credenciais', 'pressao-plugin'); ?>
                    </a>
                <?php else : ?>
                    <span class="description"><?php esc_html_e('Gerenciado pelo servidor (wp-config.php).', 'pressao-plugin'); ?></span>
                <?php endif; ?>
            </p>
        </div>
        <?php
    }

    /**
     * @param array<string, mixed> $campanha
     * @return array{id: string, nome: string, descricao: string, telefone_origem: string, ativa: bool}
     */
    private static function campanha_payload($campanha) {
        return [
            'id' => isset($campanha['id']) ? (string) $campanha['id'] : '',
            'nome' => isset($campanha['nome']) ? (string) $campanha['nome'] : '',
            'descricao' => isset($campanha['descricao']) ? (string) $campanha['descricao'] : '',
            'telefone_origem' => isset($campanha['telefone_origem']) ? (string) $campanha['telefone_origem'] : '',
            'ativa' => !empty($campanha['ativa']),
        ];
    }

    /**
     * @param PressaoPlugin_API $api
     */
    private function render_campanha_tab(PressaoPlugin_API $api) {
        $campaign_id = (string) get_option('pressao_campaign_id', '');
        $vinculada = $campaign_id !== '' && wp_is_uuid($campaign_id);
        $campanha = null;
        $erro = '';
        if ($vinculada) {
            $result = $api->get_campanha($campaign_id);
            if (is_wp_error($result)) {
                $erro = $result->get_error_message();
            } else {
                $campanha = is_array($result) ? $result : null;
            }
        }
        $payload = $campanha
            ? self::campanha_payload($campanha)
            : [
                'id' => $vinculada ? $campaign_id : '',
                'nome' => '',
                'descricao' => '',
                'telefone_origem' => '',
                'ativa' => true,
            ];
        $mostrar_cartao = $campanha !== null;
        $telefone_ajuda = __(
            'Número Twilio desta campanha: é o que liga para o ativista e o que o alvo vê na chamada. Pode ficar vazio e ser preenchido depois, quando o canal telefone estiver em uso.',
            'pressao-plugin'
        );
        ?>
        <div class="pressao-campanha-picker"
             data-nonce="<?php echo esc_attr(wp_create_nonce(self::NONCE_CAMPANHA)); ?>"
             data-campaign="<?php echo esc_attr(wp_json_encode($payload)); ?>">
            <h2><?php esc_html_e('Campanha deste site', 'pressao-plugin'); ?></h2>
            <p><?php esc_html_e('Busque uma campanha na API ou crie uma nova. O vínculo é gravado na hora e libera as demais abas.', 'pressao-plugin'); ?></p>

            <?php if ($erro !== '') : ?>
                <div class="notice notice-warning inline pressao-campanha-aviso">
                    <p>
                        <?php if ($vinculada) : ?>
                            <?php esc_html_e('A campanha vinculada não foi encontrada na API. Busque outra ou crie uma nova — o vínculo atual segue válido até você escolher.', 'pressao-plugin'); ?>
                            <?php if ($erro !== '') : ?>
                                <br><?php echo esc_html($erro); ?>
                            <?php endif; ?>
                        <?php else : ?>
                            <?php echo esc_html($erro); ?>
                        <?php endif; ?>
                    </p>
                </div>
            <?php endif; ?>

            <div class="pressao-campanha-card" <?php echo $mostrar_cartao ? '' : 'hidden'; ?>>
                <p class="pressao-campanha-badge <?php echo empty($payload['ativa']) ? 'is-inativa' : 'is-ativa'; ?>">
                    <?php echo empty($payload['ativa']) ? esc_html__('Inativa', 'pressao-plugin') : esc_html__('Ativa', 'pressao-plugin'); ?>
                </p>
                <h3 class="pressao-campanha-nome"><?php echo esc_html($payload['nome']); ?></h3>
                <p class="pressao-campanha-descricao" <?php echo $payload['descricao'] === '' ? 'hidden' : ''; ?>>
                    <?php echo esc_html($payload['descricao']); ?>
                </p>
                <p class="pressao-campanha-telefone">
                    <strong><?php esc_html_e('Telefone de origem', 'pressao-plugin'); ?></strong>
                    <span><?php echo $payload['telefone_origem'] !== '' ? esc_html($payload['telefone_origem']) : esc_html__('Não definido', 'pressao-plugin'); ?></span>
                </p>
                <p class="pressao-campanha-actions">
                    <button type="button" class="button" data-action="editar"><?php esc_html_e('Editar campanha', 'pressao-plugin'); ?></button>
                    <button type="button" class="button" data-action="trocar"><?php esc_html_e('Trocar campanha', 'pressao-plugin'); ?></button>
                </p>
            </div>

            <div class="pressao-campanha-busca" <?php echo $mostrar_cartao ? 'hidden' : ''; ?>>
                <p>
                    <label for="pressao-campanha-select"><?php esc_html_e('Buscar campanha', 'pressao-plugin'); ?></label>
                </p>
                <select id="pressao-campanha-select"
                        placeholder="<?php esc_attr_e('Digite o nome da campanha', 'pressao-plugin'); ?>"></select>
                <p>
                    <button type="button" class="button button-secondary" data-action="criar">
                        <?php esc_html_e('Adicionar nova campanha', 'pressao-plugin'); ?>
                    </button>
                    <button type="button" class="button" data-action="voltar" hidden>
                        <?php esc_html_e('Voltar', 'pressao-plugin'); ?>
                    </button>
                </p>
            </div>

            <div class="pressao-campanha-form" hidden>
                <input type="hidden" data-field="id" value="">
                <div class="pressao-campanha-form-row">
                    <p>
                        <label for="pressao-campanha-nome"><?php esc_html_e('Nome', 'pressao-plugin'); ?></label>
                        <input id="pressao-campanha-nome" type="text" class="regular-text" data-field="nome" maxlength="200" required>
                    </p>
                    <p>
                        <label for="pressao-campanha-telefone"><?php esc_html_e('Telefone de origem', 'pressao-plugin'); ?></label>
                        <input id="pressao-campanha-telefone" type="text" class="regular-text" data-field="telefone_origem">
                        <span class="description"><?php echo esc_html($telefone_ajuda); ?></span>
                    </p>
                </div>
                <p>
                    <label for="pressao-campanha-descricao"><?php esc_html_e('Descrição', 'pressao-plugin'); ?></label>
                    <textarea id="pressao-campanha-descricao" class="large-text" rows="3" data-field="descricao"></textarea>
                </p>
                <p class="pressao-campanha-ativa">
                    <label for="pressao-campanha-ativa">
                        <input id="pressao-campanha-ativa" type="checkbox" data-field="ativa" value="1" checked>
                        <?php esc_html_e('Campanha ativa', 'pressao-plugin'); ?>
                    </label>
                    <span class="description"><?php esc_html_e('Desmarque para pausar a campanha na API. Este site continua vinculado.', 'pressao-plugin'); ?></span>
                </p>
                <p class="pressao-campanha-form-status" role="status"></p>
                <p class="pressao-campanha-form-actions">
                    <button type="button" class="button button-primary" data-action="salvar-form">
                        <?php esc_html_e('Criar campanha', 'pressao-plugin'); ?>
                    </button>
                    <button type="button" class="button" data-action="cancelar">
                        <?php esc_html_e('Cancelar', 'pressao-plugin'); ?>
                    </button>
                </p>
            </div>
        </div>
        <?php
    }

    private function assert_can_manage_campanha() {
        if (!current_user_can('manage_options')) {
            wp_send_json_error(['message' => __('Sem permissão.', 'pressao-plugin')], 403);
        }
        check_ajax_referer(self::NONCE_CAMPANHA, 'nonce');
    }

    /**
     * @param array<string, mixed> $campanha
     * @return array<string, mixed>
     */
    private static function campanha_ajax_item($campanha) {
        $payload = self::campanha_payload($campanha);
        $text = $payload['nome'];
        if (!$payload['ativa']) {
            $text .= ' (' . __('inativa', 'pressao-plugin') . ')';
        }
        $payload['text'] = $text;
        return $payload;
    }

    /**
     * @return array{nome: string, descricao: string, telefone_origem: string, ativa: bool}
     */
    private function campanha_dados_do_post() {
        $nome = isset($_POST['nome']) ? sanitize_text_field(wp_unslash($_POST['nome'])) : '';
        $nome = trim($nome);
        if (strlen($nome) < 3 || strlen($nome) > 200) {
            wp_send_json_error(
                ['message' => __('O nome da campanha precisa ter entre 3 e 200 caracteres.', 'pressao-plugin')],
                400
            );
        }
        $ativa_raw = isset($_POST['ativa']) ? wp_unslash($_POST['ativa']) : '1';
        $ativa = !($ativa_raw === '0' || $ativa_raw === 'false' || $ativa_raw === '');
        return [
            'nome' => $nome,
            'descricao' => isset($_POST['descricao']) ? sanitize_textarea_field(wp_unslash($_POST['descricao'])) : '',
            'telefone_origem' => isset($_POST['telefone_origem']) ? sanitize_text_field(wp_unslash($_POST['telefone_origem'])) : '',
            'ativa' => $ativa,
        ];
    }

    public function ajax_buscar_campanhas() {
        $this->assert_can_manage_campanha();
        $q = isset($_POST['q']) ? sanitize_text_field(wp_unslash($_POST['q'])) : '';
        $q = trim($q);
        if (strlen($q) < 2) {
            wp_send_json_success(['results' => []]);
        }
        $api = new PressaoPlugin_API();
        $lista = $api->listar_campanhas($q);
        if (is_wp_error($lista)) {
            wp_send_json_error(['message' => $lista->get_error_message()], 400);
        }
        $results = [];
        foreach ($lista as $item) {
            if (!is_array($item)) {
                continue;
            }
            $results[] = self::campanha_ajax_item($item);
        }
        wp_send_json_success(['results' => $results]);
    }

    public function ajax_criar_campanha() {
        $this->assert_can_manage_campanha();
        $dados = $this->campanha_dados_do_post();
        $payload = [
            'nome' => $dados['nome'],
            'ativa' => $dados['ativa'],
        ];
        if ($dados['descricao'] !== '') {
            $payload['descricao'] = $dados['descricao'];
        }
        if ($dados['telefone_origem'] !== '') {
            $payload['telefone_origem'] = $dados['telefone_origem'];
        }
        $api = new PressaoPlugin_API();
        $campanha = $api->criar_campanha($payload);
        if (is_wp_error($campanha)) {
            wp_send_json_error(['message' => $campanha->get_error_message()], 400);
        }
        $id = isset($campanha['id']) ? (string) $campanha['id'] : '';
        if ($id === '' || !wp_is_uuid($id)) {
            wp_send_json_error(['message' => __('A API não devolveu um ID de campanha válido.', 'pressao-plugin')], 400);
        }
        update_option('pressao_campaign_id', $id, false);
        wp_send_json_success(['campanha' => self::campanha_ajax_item($campanha)]);
    }

    public function ajax_atualizar_campanha() {
        $this->assert_can_manage_campanha();
        $id = isset($_POST['id']) ? sanitize_text_field(wp_unslash($_POST['id'])) : '';
        if ($id === '' || !wp_is_uuid($id)) {
            wp_send_json_error(['message' => __('ID da campanha inválido.', 'pressao-plugin')], 400);
        }
        $dados = $this->campanha_dados_do_post();
        $payload = [
            'nome' => $dados['nome'],
            'descricao' => $dados['descricao'],
            'ativa' => $dados['ativa'],
        ];
        if ($dados['telefone_origem'] !== '') {
            $payload['telefone_origem'] = $dados['telefone_origem'];
        }
        $api = new PressaoPlugin_API();
        $campanha = $api->atualizar_campanha($id, $payload);
        if (is_wp_error($campanha)) {
            wp_send_json_error(['message' => $campanha->get_error_message()], 400);
        }
        wp_send_json_success(['campanha' => self::campanha_ajax_item($campanha)]);
    }

    public function ajax_vincular_campanha() {
        $this->assert_can_manage_campanha();
        $id = isset($_POST['id']) ? sanitize_text_field(wp_unslash($_POST['id'])) : '';
        if ($id === '' || !wp_is_uuid($id)) {
            wp_send_json_error(['message' => __('ID da campanha inválido.', 'pressao-plugin')], 400);
        }
        update_option('pressao_campaign_id', $id, false);
        wp_send_json_success(['id' => $id]);
    }

    /**
     * @param array|mixed $alvos
     * @param string      $tipo
     * @return array<string, mixed>|null
     */
    private static function primeiro_alvo_tipo($alvos, $tipo) {
        if (!is_array($alvos)) {
            return null;
        }
        foreach ($alvos as $alvo) {
            if (!is_array($alvo)) {
                continue;
            }
            if (($alvo['tipo_contato'] ?? '') === $tipo && ($alvo['ativo'] ?? true)) {
                return $alvo;
            }
        }
        return null;
    }

    /**
     * @param PressaoPlugin_API $api
     */
    private function render_redes_sociais_tab(PressaoPlugin_API $api) {
        $campanha_id = (string) get_option('pressao_campaign_id', '');
        $alvos = [];
        $erro = '';
        $templates = [
            'instagram' => [],
            'tiktok' => [],
        ];
        if ($campanha_id !== '' && wp_is_uuid($campanha_id)) {
            $lista = $api->get_alvos($campanha_id);
            if (is_wp_error($lista)) {
                $erro = $lista->get_error_message();
            } else {
                $alvos = is_array($lista) ? $lista : [];
            }
            foreach (['instagram', 'tiktok'] as $canal) {
                $tpl = $api->listar_templates($campanha_id, $canal);
                $templates[$canal] = is_wp_error($tpl) ? [] : $tpl;
            }
        }
        $plataformas = [
            'instagram' => [
                'titulo' => __('Instagram', 'pressao-plugin'),
                'url_label' => __('URL da postagem', 'pressao-plugin'),
                'vazio' => __('Ainda não há publicação do Instagram nesta campanha.', 'pressao-plugin'),
                'salvar' => __('Salvar Instagram', 'pressao-plugin'),
            ],
            'tiktok' => [
                'titulo' => __('TikTok', 'pressao-plugin'),
                'url_label' => __('URL do vídeo', 'pressao-plugin'),
                'vazio' => __('Ainda não há vídeo do TikTok nesta campanha.', 'pressao-plugin'),
                'salvar' => __('Salvar TikTok', 'pressao-plugin'),
            ],
        ];
        ?>
        <div class="pressao-redes"
             data-nonce="<?php echo esc_attr(wp_create_nonce(self::NONCE_REDES)); ?>"
             data-campaign-id="<?php echo esc_attr($campanha_id); ?>">
            <h2><?php esc_html_e('Redes Sociais', 'pressao-plugin'); ?></h2>
            <p><?php esc_html_e('Defina a publicação e os textos do Instagram e do TikTok. No fim da página, quem marcar nos comentários.', 'pressao-plugin'); ?></p>

            <?php if ($erro !== '') : ?>
                <div class="notice notice-warning inline">
                    <p><?php echo esc_html($erro); ?></p>
                </div>
            <?php endif; ?>

            <div class="pressao-redes-duo">
                <?php foreach ($plataformas as $canal => $meta) : ?>
                    <?php
                    $alvo = self::primeiro_alvo_tipo($alvos, $canal);
                    $alvo_id = is_array($alvo) ? (string) ($alvo['id'] ?? '') : '';
                    $nome = is_array($alvo) ? (string) ($alvo['nome'] ?? '') : '';
                    $contato = is_array($alvo) ? (string) ($alvo['contato'] ?? '') : '';
                    $tpls = isset($templates[$canal]) && is_array($templates[$canal]) ? $templates[$canal] : [];
                    ?>
                    <section class="pressao-redes-card" data-canal="<?php echo esc_attr($canal); ?>">
                        <h3><?php echo esc_html($meta['titulo']); ?></h3>
                        <?php if ($alvo_id === '') : ?>
                            <p class="description pressao-redes-vazio"><?php echo esc_html($meta['vazio']); ?></p>
                        <?php endif; ?>
                        <div class="pressao-redes-alvo">
                            <input type="hidden" data-field="alvo-id" value="<?php echo esc_attr($alvo_id); ?>">
                            <p>
                                <label><?php esc_html_e('Nome do perfil', 'pressao-plugin'); ?></label>
                                <input type="text" class="regular-text" data-field="nome" value="<?php echo esc_attr($nome); ?>">
                            </p>
                            <p>
                                <label><?php echo esc_html($meta['url_label']); ?></label>
                                <input type="url" class="regular-text" data-field="contato" value="<?php echo esc_attr($contato); ?>">
                            </p>
                            <p class="pressao-redes-alvo-status" role="status"></p>
                            <p>
                                <button type="button"
                                        class="button button-primary"
                                        data-action="salvar-alvo"
                                        data-label-saved="<?php echo esc_attr($meta['salvar']); ?>">
                                    <?php echo esc_html($alvo_id === '' ? __('Criar', 'pressao-plugin') : $meta['salvar']); ?>
                                </button>
                            </p>
                        </div>
                        <h4><?php esc_html_e('Textos do comentário', 'pressao-plugin'); ?></h4>
                        <p class="description">
                            <?php esc_html_e('A cada visita o widget sorteia um destes textos. Placeholders: {alvo_nome}, {campanha_nome}.', 'pressao-plugin'); ?>
                        </p>
                        <div class="pressao-redes-baloes">
                            <?php foreach ($tpls as $tpl) : ?>
                                <?php
                                if (!is_array($tpl)) {
                                    continue;
                                }
                                $preview = wp_strip_all_tags((string) ($tpl['conteudo'] ?? ''));
                                if (function_exists('mb_substr')) {
                                    $preview = mb_substr($preview, 0, 120);
                                } else {
                                    $preview = substr($preview, 0, 120);
                                }
                                $ativo = !empty($tpl['ativo']);
                                ?>
                                <button type="button"
                                        class="pressao-redes-balao<?php echo $ativo ? '' : ' is-inativo'; ?>"
                                        data-id="<?php echo esc_attr((string) ($tpl['id'] ?? '')); ?>"
                                        data-titulo="<?php echo esc_attr((string) ($tpl['titulo'] ?? '')); ?>"
                                        data-conteudo="<?php echo esc_attr((string) ($tpl['conteudo'] ?? '')); ?>"
                                        data-ativo="<?php echo $ativo ? '1' : '0'; ?>">
                                    <span class="pressao-redes-balao-preview"><?php echo esc_html($preview !== '' ? $preview : '…'); ?></span>
                                    <?php if (!$ativo) : ?>
                                        <span class="pressao-redes-balao-selo"><?php esc_html_e('Fora do sorteio', 'pressao-plugin'); ?></span>
                                    <?php endif; ?>
                                </button>
                            <?php endforeach; ?>
                            <button type="button" class="pressao-redes-balao pressao-redes-balao-add" data-action="novo-texto">
                                <?php esc_html_e('+ Novo texto', 'pressao-plugin'); ?>
                            </button>
                        </div>
                        <div class="pressao-redes-editor" hidden>
                            <input type="hidden" data-field="template-id" value="">
                            <p>
                                <label><?php esc_html_e('Nome interno', 'pressao-plugin'); ?></label>
                                <input type="text" class="regular-text" data-field="titulo">
                            </p>
                            <p>
                                <label><?php esc_html_e('Texto do comentário', 'pressao-plugin'); ?></label>
                                <textarea class="large-text" rows="5" data-field="conteudo"></textarea>
                            </p>
                            <p>
                                <label>
                                    <input type="checkbox" data-field="ativo" value="1" checked>
                                    <?php esc_html_e('Usar no sorteio', 'pressao-plugin'); ?>
                                </label>
                            </p>
                            <p class="pressao-redes-editor-status" role="status"></p>
                            <p class="pressao-redes-editor-actions">
                                <button type="button" class="button button-primary" data-action="salvar-texto"><?php esc_html_e('Salvar texto', 'pressao-plugin'); ?></button>
                                <button type="button" class="button" data-action="cancelar-texto"><?php esc_html_e('Cancelar', 'pressao-plugin'); ?></button>
                                <button type="button" class="button-link link-delete" data-action="remover-texto" hidden><?php esc_html_e('Remover', 'pressao-plugin'); ?></button>
                            </p>
                        </div>
                    </section>
                <?php endforeach; ?>
            </div>

            <?php PressaoPlugin_Candidatos_Filtros::render_admin_tools(); ?>

            <h2><?php esc_html_e('Quem marcar', 'pressao-plugin'); ?></h2>
            <p><?php esc_html_e('Pessoas a marcar nos comentários do Instagram e do TikTok. Salve cada item na lista (não pelo botão Salvar de outras abas).', 'pressao-plugin'); ?></p>
            <?php PressaoPlugin_Candidatos_Admin_List::render(PressaoPlugin_Candidatos_Admin_List::OPTION_PRESSIONAR); ?>
        </div>
        <?php
    }

    private function assert_can_manage_redes() {
        if (!current_user_can('manage_options')) {
            wp_send_json_error(['message' => __('Sem permissão.', 'pressao-plugin')], 403);
        }
        check_ajax_referer(self::NONCE_REDES, 'nonce');
    }

    /**
     * @return string
     */
    private function campanha_id_atual() {
        $id = (string) get_option('pressao_campaign_id', '');
        if ($id === '' || !wp_is_uuid($id)) {
            wp_send_json_error(['message' => __('Vincule uma campanha antes de editar as redes.', 'pressao-plugin')], 400);
        }
        return $id;
    }

    /**
     * @return string
     */
    private function canal_social_do_post() {
        $canal = isset($_POST['canal']) ? sanitize_key(wp_unslash($_POST['canal'])) : '';
        if (!in_array($canal, ['instagram', 'tiktok'], true)) {
            wp_send_json_error(['message' => __('Plataforma inválida.', 'pressao-plugin')], 400);
        }
        return $canal;
    }

    public function ajax_salvar_alvo_social() {
        $this->assert_can_manage_redes();
        $campanha_id = $this->campanha_id_atual();
        $canal = $this->canal_social_do_post();
        $nome = isset($_POST['nome']) ? sanitize_text_field(wp_unslash($_POST['nome'])) : '';
        $contato = isset($_POST['contato']) ? esc_url_raw(wp_unslash($_POST['contato'])) : '';
        $nome = trim($nome);
        $contato = trim($contato);
        if ($nome === '' || $contato === '') {
            wp_send_json_error(
                ['message' => __('Informe o nome do perfil e a URL.', 'pressao-plugin')],
                400
            );
        }
        $id = isset($_POST['id']) ? sanitize_text_field(wp_unslash($_POST['id'])) : '';
        $api = new PressaoPlugin_API();
        if ($id !== '' && wp_is_uuid($id)) {
            $alvo = $api->atualizar_alvo($id, [
                'nome' => $nome,
                'contato' => $contato,
            ], $campanha_id);
        } else {
            $alvo = $api->criar_alvo([
                'campanha_id' => $campanha_id,
                'nome' => $nome,
                'contato' => $contato,
                'tipo_contato' => $canal,
                'ativo' => true,
            ]);
        }
        if (is_wp_error($alvo)) {
            wp_send_json_error(['message' => $alvo->get_error_message()], 400);
        }
        wp_send_json_success(['alvo' => $alvo]);
    }

    public function ajax_salvar_template_social() {
        $this->assert_can_manage_redes();
        $campanha_id = $this->campanha_id_atual();
        $canal = $this->canal_social_do_post();
        $conteudo = isset($_POST['conteudo']) ? wp_kses_post(wp_unslash($_POST['conteudo'])) : '';
        $conteudo = trim($conteudo);
        if ($conteudo === '') {
            wp_send_json_error(['message' => __('O texto do comentário não pode ficar vazio.', 'pressao-plugin')], 400);
        }
        $titulo = isset($_POST['titulo']) ? sanitize_text_field(wp_unslash($_POST['titulo'])) : '';
        $titulo = trim($titulo);
        if ($titulo === '') {
            $titulo = function_exists('mb_substr') ? mb_substr(wp_strip_all_tags($conteudo), 0, 40) : substr(wp_strip_all_tags($conteudo), 0, 40);
        }
        if ($titulo === '') {
            $titulo = $canal;
        }
        $ativo_raw = isset($_POST['ativo']) ? wp_unslash($_POST['ativo']) : '1';
        $ativo = !($ativo_raw === '0' || $ativo_raw === 'false' || $ativo_raw === '');
        $id = isset($_POST['id']) ? sanitize_text_field(wp_unslash($_POST['id'])) : '';
        $api = new PressaoPlugin_API();
        if ($id !== '' && wp_is_uuid($id)) {
            $tpl = $api->atualizar_template($id, [
                'titulo' => $titulo,
                'conteudo' => $conteudo,
                'ativo' => $ativo,
            ], $campanha_id);
        } else {
            $tpl = $api->criar_template([
                'campanha_id' => $campanha_id,
                'canal' => $canal,
                'titulo' => $titulo,
                'conteudo' => $conteudo,
                'ativo' => $ativo,
            ]);
        }
        if (is_wp_error($tpl)) {
            wp_send_json_error(['message' => $tpl->get_error_message()], 400);
        }
        wp_send_json_success(['template' => $tpl]);
    }

    public function ajax_deletar_template_social() {
        $this->assert_can_manage_redes();
        $campanha_id = $this->campanha_id_atual();
        $id = isset($_POST['id']) ? sanitize_text_field(wp_unslash($_POST['id'])) : '';
        if ($id === '' || !wp_is_uuid($id)) {
            wp_send_json_error(['message' => __('ID do texto inválido.', 'pressao-plugin')], 400);
        }
        $api = new PressaoPlugin_API();
        $ok = $api->deletar_template($id, $campanha_id);
        if (is_wp_error($ok)) {
            wp_send_json_error(['message' => $ok->get_error_message()], 400);
        }
        wp_send_json_success(['id' => $id]);
    }

    private function render_documentacao_tab() {
        $shortcodes = [
            [
                'tag' => '[pressao_multicanal]',
                'title' => __('Widget padrão multicanal', 'pressao-plugin'),
                'body' => __('Shortcode recomendado: home com os canais da campanha (Instagram, TikTok, e-mail), barra de progresso e compartilhamento. Marca quem está em Redes Sociais nos comentários e cria a ação ao fim de cada canal.', 'pressao-plugin'),
                'example' => '[pressao_multicanal campaign="uuid" canais="instagram,tiktok,email" countdown="3"]',
            ],
            [
                'tag' => '[pressao_alvos]',
                'title' => __('Lista de alvos com ações (legado)', 'pressao-plugin'),
                'body' => __('Lista os canais da campanha (Instagram, TikTok, e-mail etc.) e permite ao ativista agir. Se o compartilhamento estiver ativo na aba Compartilhamento, o botão aparece por último na lista. Para campanhas novas, prefira [pressao_multicanal].', 'pressao-plugin'),
                'example' => '[pressao_alvos campaign="uuid" show_ativista_form="yes" ordem="instagram,tiktok,email" tempo_email="1 min"]',
            ],
            [
                'tag' => '[pressao_fluxo]',
                'title' => __('Fluxo sequencial (Instagram)', 'pressao-plugin'),
                'body' => __('Wizard isolado por alvo/canal: marcar quem pressionar, copiar/abrir Instagram, confirmar e opcionalmente deixar contato. Usa as bases das abas Redes Sociais e Apoiadores. Requer alvo_id e canal.', 'pressao-plugin'),
                'example' => '[pressao_fluxo alvo_id="uuid-do-alvo" canal="instagram"]',
            ],
            [
                'tag' => '[pressao_candidatos]',
                'title' => __('Bloco de candidatos apoiadores (legado)', 'pressao-plugin'),
                'body' => __('Exibe a base editorial de quem já apoia a pauta (option pressao_candidatos_apoiadores), configurada na aba Apoiadores.', 'pressao-plugin'),
                'example' => '[pressao_candidatos title="Conheça os candidatos"]',
            ],
            [
                'tag' => '[pressao_contador]',
                'title' => __('Contador de ações confirmadas (legado)', 'pressao-plugin'),
                'body' => __('Mostra o total de ações confirmadas da campanha (atualiza com cache curto) e pode animar quando o ativista conclui uma ação na mesma página.', 'pressao-plugin'),
                'example' => '[pressao_contador campaign="uuid" label="ações confirmadas"]',
            ],
            [
                'tag' => '[pressao_progresso]',
                'title' => __('Progresso pessoal do ativista (legado)', 'pressao-plugin'),
                'body' => __('Barra done/total com base nas ações realizadas neste navegador (cookie). Zera quando a sessão do ativista é limpa (“Não sou eu” ou expiração).', 'pressao-plugin'),
                'example' => '[pressao_progresso]',
            ],
            [
                'tag' => '[pressao_widget]',
                'title' => __('Widget completo (legado)', 'pressao-plugin'),
                'body' => __('Combina formulário e lista num único bloco. Prefira [pressao_multicanal] para campanhas novas com canais e compartilhamento.', 'pressao-plugin'),
                'example' => '[pressao_widget title="Meu Widget"]',
            ],
            [
                'tag' => '[pressao_form]',
                'title' => __('Somente formulário (legado)', 'pressao-plugin'),
                'body' => __('Renderiza só o formulário de identificação/ação do widget antigo.', 'pressao-plugin'),
                'example' => '[pressao_form button_text="Enviar"]',
            ],
            [
                'tag' => '[pressao_list]',
                'title' => __('Somente lista (legado)', 'pressao-plugin'),
                'body' => __('Renderiza só a lista do widget antigo, sem o formulário.', 'pressao-plugin'),
                'example' => '[pressao_list limit="5"]',
            ],
        ];
        ?>
        <div class="pressao-docs">
            <header class="pressao-docs-intro">
                <h2><?php esc_html_e('Como usar', 'pressao-plugin'); ?></h2>
                <p>
                    <?php esc_html_e('O Pressão Plugin conecta este site à API de pressão multicanal. Configure a conexão (Keycloak + API) e vincule uma campanha nas abas Conexão e Campanha; depois insira os shortcodes nas páginas ou posts.', 'pressao-plugin'); ?>
                </p>
                <p class="description">
                    <?php esc_html_e('Atributos como campaign usam a campanha da aba Campanha quando omitidos. Detalhes completos de atributos estão no README do plugin.', 'pressao-plugin'); ?>
                </p>
            </header>

            <div class="pressao-docs-grid">
                <?php foreach ($shortcodes as $item) : ?>
                    <article class="pressao-docs-card">
                        <h3 class="pressao-docs-card-title">
                            <code><?php echo esc_html($item['tag']); ?></code>
                            <span><?php echo esc_html($item['title']); ?></span>
                        </h3>
                        <p class="pressao-docs-card-body"><?php echo esc_html($item['body']); ?></p>
                        <pre class="pressao-docs-example"><code><?php echo esc_html($item['example']); ?></code></pre>
                    </article>
                <?php endforeach; ?>
            </div>

            <aside class="pressao-lgpd-info" aria-labelledby="pressao-docs-lgpd-title">
                <h3 id="pressao-docs-lgpd-title"><?php esc_html_e('Sobre a LGPD', 'pressao-plugin'); ?></h3>
                <p>
                    <?php esc_html_e('O plugin armazena apenas o nome do ativista no navegador para identificação. Email e telefone são opcionais e só são enviados ao servidor quando o ativista realiza uma ação. A confirmação de identidade exibe apenas o nome, respeitando a Lei Geral de Proteção de Dados.', 'pressao-plugin'); ?>
                </p>
            </aside>
        </div>
        <?php
    }

    public function render_geral_widget_section() {
        echo '<p>' . esc_html__(
            'Textos do widget neste site. A campanha da API é escolhida na aba Campanha. Alvos e templates continuam sendo geridos pela API (abas futuras no admin).',
            'pressao-plugin'
        ) . '</p>';
    }

    public function sanitize_ativista_confirm_interval($value) {
        $n = absint($value);
        if ($n < 1) {
            $n = 1;
        }
        if ($n > 60) {
            $n = 60;
        }
        return $n;
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
    public function render_session_duration_field() {
        $value = get_option('pressao_session_duration', '86400');
        $options = [
            '1800' => __('30 minutos', 'pressao-plugin'),
            '3600' => __('1 hora', 'pressao-plugin'),
            '7200' => __('2 horas', 'pressao-plugin'),
            '21600' => __('6 horas', 'pressao-plugin'),
            '43200' => __('12 horas', 'pressao-plugin'),
            '86400' => __('24 horas', 'pressao-plugin'),
            '604800' => __('7 dias', 'pressao-plugin'),
            '2592000' => __('30 dias', 'pressao-plugin'),
            '0' => __('Sessão do navegador (sem expiração)', 'pressao-plugin'),
        ];
        ?>
        <select name="pressao_session_duration">
            <?php foreach ($options as $val => $label) : ?>
                <option value="<?php echo esc_attr($val); ?>" <?php selected($value, $val); ?>>
                    <?php echo esc_html($label); ?>
                </option>
            <?php endforeach; ?>
        </select>
        <p class="description"><?php esc_html_e('Tempo que a sessão do ativista permanece ativa no navegador.', 'pressao-plugin'); ?></p>
        <?php
    }

    public function render_candidatos_pressao_section() {
        echo '<p>' . esc_html__(
            'Preferências do [pressao_fluxo]. Moradia temporária nesta aba; a lista de quem marcar fica em Redes Sociais.',
            'pressao-plugin'
        ) . '</p>';
    }

    private function render_apoiadores_tools() {
        $apoiadores = get_option('pressao_candidatos_apoiadores', []);
        if (!is_array($apoiadores)) {
            $apoiadores = [];
        }
        ?>
        <div class="pressao-apoiadores-tools">
            <h2><?php esc_html_e('Ferramentas — candidatos apoiadores', 'pressao-plugin'); ?></h2>

            <div class="pressao-admin-card">
                <h3><?php esc_html_e('Importar CSV (incremental)', 'pressao-plugin'); ?></h3>
                <p class="description">
                    <?php esc_html_e('Colunas: nome, cargo, partido, descricao, instagram (ou link_url), imagem_url (opcional). Novos @ são adicionados; @ existentes são atualizados; quem não está no CSV permanece. Os candidatos são salvos na hora; as imagens públicas são baixadas depois, em lotes, para uploads/candidatos/ (acompanhe o progresso no topo desta aba).', 'pressao-plugin'); ?>
                </p>
                <form method="post"
                      action="<?php echo esc_url(admin_url('admin-post.php')); ?>"
                      enctype="multipart/form-data">
                    <input type="hidden" name="action" value="<?php echo esc_attr(PressaoPlugin_Candidatos_Import::ACTION_IMPORT); ?>" />
                    <?php wp_nonce_field(PressaoPlugin_Candidatos_Import::ACTION_IMPORT); ?>
                    <p>
                        <input type="file" name="pressao_apoiadores_csv" accept=".csv,text/csv" required />
                    </p>
                    <p class="pressao-admin-actions">
                        <?php submit_button(__('Importar CSV', 'pressao-plugin'), 'secondary', 'submit', false); ?>
                        <a class="button"
                           href="<?php echo esc_url(PRESSAO_PLUGIN_URL . 'assets/examples/candidatos-apoiadores-exemplo.csv'); ?>"
                           download="candidatos-apoiadores-exemplo.csv">
                            <?php esc_html_e('Baixar CSV de exemplo', 'pressao-plugin'); ?>
                        </a>
                    </p>
                </form>
            </div>

            <div class="pressao-admin-card">
                <h3><?php esc_html_e('Remover da base', 'pressao-plugin'); ?></h3>
                <p class="description">
                    <?php esc_html_e('Busque por nome ou @, selecione um ou mais e remova. Não apaga arquivos da Media Library.', 'pressao-plugin'); ?>
                </p>
                <form method="post"
                      action="<?php echo esc_url(admin_url('admin-post.php')); ?>"
                      class="pressao-apoiadores-remove-form">
                    <input type="hidden" name="action" value="<?php echo esc_attr(PressaoPlugin_Candidatos_Import::ACTION_REMOVE); ?>" />
                    <?php wp_nonce_field(PressaoPlugin_Candidatos_Import::ACTION_REMOVE); ?>
                    <p>
                        <select id="pressao-apoiadores-remove-select"
                                name="pressao_apoiadores_remove[]"
                                multiple
                                placeholder="<?php esc_attr_e('Digite nome ou @', 'pressao-plugin'); ?>"
                                class="pressao-apoiadores-remove-select">
                            <?php foreach ($apoiadores as $candidato) : ?>
                                <?php
                                if (!is_array($candidato)) {
                                    continue;
                                }
                                $handle = PressaoPlugin_Candidatos_Import::normalize_handle($candidato['link_url'] ?? '');
                                if ($handle === '') {
                                    continue;
                                }
                                $nome = trim((string) ($candidato['nome'] ?? ''));
                                $label = $nome !== '' ? $nome . ' ' . $handle : $handle;
                                ?>
                                <option value="<?php echo esc_attr($handle); ?>">
                                    <?php echo esc_html($label); ?>
                                </option>
                            <?php endforeach; ?>
                        </select>
                    </p>
                    <?php
                    submit_button(
                        __('Remover da base', 'pressao-plugin'),
                        'delete',
                        'submit',
                        false,
                        ['id' => 'pressao-apoiadores-remove-btn']
                    );
                    ?>
                </form>
            </div>
        </div>
        <?php
    }

    public function sanitize_candidatos($value) {
        return PressaoPlugin_Candidatos_Admin_List::sanitize_list($value);
    }

    /**
     * Normaliza @handle do Instagram (aceita URL de perfil ou @user).
     */
    public function sanitize_instagram_handle($value) {
        return PressaoPlugin_Candidatos_Admin_List::sanitize_instagram_handle($value);
    }

    public function sanitize_fluxo_limite_candidatos($value) {
        $n = absint($value);
        if ($n < 1) {
            $n = 1;
        }
        if ($n > 20) {
            $n = 20;
        }
        return $n;
    }

    public function render_fluxo_limite_field() {
        $value = (int) get_option('pressao_fluxo_limite_candidatos', 5);
        ?>
        <input type="number"
               name="pressao_fluxo_limite_candidatos"
               value="<?php echo esc_attr($value); ?>"
               min="1"
               max="20"
               class="small-text" />
        <p class="description">
            <?php esc_html_e('Máximo de candidatos que o ativista pode marcar na mensagem do [pressao_fluxo].', 'pressao-plugin'); ?>
        </p>
        <?php
    }

    public function sanitize_fluxo_countdown_abrir($value) {
        return !empty($value) ? 1 : 0;
    }

    public function render_fluxo_countdown_abrir_field() {
        $value = (int) get_option('pressao_fluxo_countdown_abrir', 0);
        ?>
        <input type="hidden" name="pressao_fluxo_countdown_abrir" value="0" />
        <label>
            <input type="checkbox"
                   name="pressao_fluxo_countdown_abrir"
                   value="1"
                   <?php checked($value, 1); ?> />
            <?php esc_html_e('Aguardar contador e mostrar aviso antes de abrir o Instagram', 'pressao-plugin'); ?>
        </label>
        <p class="description">
            <?php esc_html_e('Desligado (padrão): abre no clique, sem toast. Ligado: toast com countdown e só então abre. No mobile a abertura tenta o app Instagram (para o voltar nativo retornar ao fluxo); no desktop abre em nova aba.', 'pressao-plugin'); ?>
        </p>
        <?php
    }

    public function sanitize_fluxo_ajuda($value) {
        if (!is_array($value)) {
            return [
                'titulo' => '',
                'conteudo' => '',
            ];
        }

        return [
            'titulo' => sanitize_text_field($value['titulo'] ?? ''),
            'conteudo' => wp_kses_post($value['conteudo'] ?? ''),
        ];
    }

    public function render_fluxo_ajuda_field() {
        $ajuda = get_option('pressao_fluxo_ajuda', []);
        if (!is_array($ajuda)) {
            $ajuda = [];
        }
        $titulo = $ajuda['titulo'] ?? '';
        $conteudo = $ajuda['conteudo'] ?? '';
        ?>
        <p>
            <label>
                <?php esc_html_e('Título', 'pressao-plugin'); ?><br>
                <input type="text"
                       name="pressao_fluxo_ajuda[titulo]"
                       value="<?php echo esc_attr($titulo); ?>"
                       class="regular-text"
                       placeholder="<?php esc_attr_e('Como funciona?', 'pressao-plugin'); ?>" />
            </label>
        </p>
        <p>
            <label for="pressao_fluxo_ajuda_conteudo"><?php esc_html_e('Conteúdo (HTML permitido)', 'pressao-plugin'); ?></label>
        </p>
        <?php
        wp_editor(
            $conteudo,
            'pressao_fluxo_ajuda_conteudo',
            [
                'textarea_name' => 'pressao_fluxo_ajuda[conteudo]',
                'textarea_rows' => 10,
                'media_buttons' => false,
                'teeny' => true,
                'quicktags' => true,
            ]
        );
        ?>
        <p class="description">
            <?php esc_html_e('Exibido no modal/drawer ao clicar no ? do [pressao_fluxo].', 'pressao-plugin'); ?>
        </p>
        <?php
    }

    public function render_compartilhamento_field() {
        $config = get_option('pressao_compartilhamento', []);
        if (!is_array($config)) {
            $config = [];
        }
        $imagens = isset($config['imagens']) && is_array($config['imagens']) ? $config['imagens'] : [];
        if (empty($imagens)) {
            $imagens = [[]];
        }
        $ativo = !empty($config['ativo']);
        ?>
        <div class="pressao-compartilhamento-admin">
            <p>
                <label>
                    <input type="checkbox"
                           name="pressao_compartilhamento[ativo]"
                           value="1"
                           <?php checked($ativo); ?> />
                    <?php esc_html_e('Exibir botão de compartilhamento no final da lista de alvos', 'pressao-plugin'); ?>
                </label>
            </p>

            <h4><?php esc_html_e('Botão na lista', 'pressao-plugin'); ?></h4>
            <p>
                <label>
                    <?php esc_html_e('Título', 'pressao-plugin'); ?><br>
                    <input type="text"
                           name="pressao_compartilhamento[titulo]"
                           value="<?php echo esc_attr($config['titulo'] ?? ''); ?>"
                           class="regular-text"
                           placeholder="<?php esc_attr_e('Compartilhar ação', 'pressao-plugin'); ?>" />
                </label>
            </p>
            <p>
                <label>
                    <?php esc_html_e('Subtítulo', 'pressao-plugin'); ?><br>
                    <input type="text"
                           name="pressao_compartilhamento[subtitulo]"
                           value="<?php echo esc_attr($config['subtitulo'] ?? ''); ?>"
                           class="regular-text"
                           placeholder="<?php esc_attr_e('Ajude a chegar em mais gente', 'pressao-plugin'); ?>" />
                </label>
            </p>
            <p>
                <label>
                    <?php esc_html_e('Tempo estimado', 'pressao-plugin'); ?><br>
                    <input type="text"
                           name="pressao_compartilhamento[tempo]"
                           value="<?php echo esc_attr($config['tempo'] ?? ''); ?>"
                           class="small-text"
                           placeholder="3 min" />
                </label>
            </p>

            <h4><?php esc_html_e('Overlay', 'pressao-plugin'); ?></h4>
            <p>
                <label>
                    <?php esc_html_e('Título do overlay', 'pressao-plugin'); ?><br>
                    <input type="text"
                           name="pressao_compartilhamento[overlay_titulo]"
                           value="<?php echo esc_attr($config['overlay_titulo'] ?? ''); ?>"
                           class="regular-text"
                           placeholder="<?php esc_attr_e('Compartilhe e aumente o seu impacto', 'pressao-plugin'); ?>" />
                </label>
            </p>
            <p>
                <label>
                    <?php esc_html_e('Link para compartilhar', 'pressao-plugin'); ?><br>
                    <input type="url"
                           name="pressao_compartilhamento[link]"
                           value="<?php echo esc_url($config['link'] ?? ''); ?>"
                           class="regular-text" />
                </label>
            </p>
            <p>
                <label>
                    <?php esc_html_e('Mensagem pré-definida', 'pressao-plugin'); ?><br>
                    <textarea name="pressao_compartilhamento[mensagem]"
                              rows="3"
                              class="large-text"><?php echo esc_textarea($config['mensagem'] ?? ''); ?></textarea>
                </label>
                <span class="description">
                    <?php esc_html_e('Usada no WhatsApp (wa.me/?text=) quando a URL customizada estiver vazia.', 'pressao-plugin'); ?>
                </span>
            </p>
            <p>
                <label>
                    <?php esc_html_e('URL WhatsApp (opcional)', 'pressao-plugin'); ?><br>
                    <input type="url"
                           name="pressao_compartilhamento[whatsapp_url]"
                           value="<?php echo esc_url($config['whatsapp_url'] ?? ''); ?>"
                           class="regular-text" />
                </label>
                <span class="description">
                    <?php esc_html_e('Se vazio, o link é gerado automaticamente a partir da Mensagem.', 'pressao-plugin'); ?>
                </span>
            </p>
            <p>
                <label>
                    <?php esc_html_e('URL X (opcional)', 'pressao-plugin'); ?><br>
                    <input type="url"
                           name="pressao_compartilhamento[x_url]"
                           value="<?php echo esc_url($config['x_url'] ?? ''); ?>"
                           class="regular-text" />
                </label>
                <span class="description">
                    <?php esc_html_e('Se vazio, o link é gerado automaticamente a partir da Mensagem (igual ao WhatsApp).', 'pressao-plugin'); ?>
                </span>
            </p>
            <p>
                <label>
                    <?php esc_html_e('URL Instagram', 'pressao-plugin'); ?><br>
                    <input type="url"
                           name="pressao_compartilhamento[instagram_url]"
                           value="<?php echo esc_url($config['instagram_url'] ?? ''); ?>"
                           class="regular-text" />
                </label>
                <span class="description">
                    <?php esc_html_e('Link direto pra uma publicação/perfil no Instagram — sem geração automática, precisa ser preenchido.', 'pressao-plugin'); ?>
                </span>
            </p>
            <p>
                <label>
                    <?php esc_html_e('URL Facebook', 'pressao-plugin'); ?><br>
                    <input type="url"
                           name="pressao_compartilhamento[facebook_url]"
                           value="<?php echo esc_url($config['facebook_url'] ?? ''); ?>"
                           class="regular-text" />
                </label>
                <span class="description">
                    <?php esc_html_e('Link direto pra uma publicação/perfil no Facebook — sem geração automática, precisa ser preenchido.', 'pressao-plugin'); ?>
                </span>
            </p>

            <h4><?php esc_html_e('Imagens para postar', 'pressao-plugin'); ?></h4>
            <p>
                <label>
                    <?php esc_html_e('Título do card', 'pressao-plugin'); ?><br>
                    <input type="text"
                           name="pressao_compartilhamento[imagens_titulo]"
                           value="<?php echo esc_attr($config['imagens_titulo'] ?? ''); ?>"
                           class="regular-text"
                           placeholder="<?php esc_attr_e('Imagens para postar', 'pressao-plugin'); ?>" />
                </label>
            </p>
            <p>
                <label>
                    <?php esc_html_e('Subtítulo do card', 'pressao-plugin'); ?><br>
                    <input type="text"
                           name="pressao_compartilhamento[imagens_subtitulo]"
                           value="<?php echo esc_attr($config['imagens_subtitulo'] ?? ''); ?>"
                           class="regular-text"
                           placeholder="<?php esc_attr_e('baixe imagens prontas para postar nas redes', 'pressao-plugin'); ?>" />
                </label>
            </p>
            <p>
                <label>
                    <?php esc_html_e('Instrução da tela de download', 'pressao-plugin'); ?><br>
                    <textarea name="pressao_compartilhamento[imagens_instrucao]"
                              rows="2"
                              class="large-text"><?php echo esc_textarea($config['imagens_instrucao'] ?? ''); ?></textarea>
                </label>
            </p>

            <div class="pressao-share-imagens-admin" data-next-index="<?php echo esc_attr(count($imagens)); ?>">
                <div class="pressao-share-imagens-list">
                    <?php foreach ($imagens as $index => $imagem) : ?>
                        <?php $this->render_share_imagem_admin_item((int) $index, $imagem); ?>
                    <?php endforeach; ?>
                </div>
                <button type="button" class="button pressao-add-share-imagem">
                    <?php esc_html_e('Adicionar imagem', 'pressao-plugin'); ?>
                </button>
                <p class="description">
                    <?php esc_html_e('As imagens usam a Biblioteca de Mídia do WordPress (attachment ID).', 'pressao-plugin'); ?>
                </p>
            </div>
        </div>
        <?php
    }

    private function render_share_imagem_admin_item($index, $imagem) {
        $imagem = is_array($imagem) ? $imagem : [];
        $imagem_id = absint($imagem['imagem_id'] ?? 0);
        $imagem_url = $imagem_id ? wp_get_attachment_image_url($imagem_id, 'thumbnail') : '';
        ?>
        <div class="pressao-share-imagem-admin-item" data-index="<?php echo esc_attr($index); ?>">
            <p>
                <label>
                    <?php esc_html_e('Rótulo', 'pressao-plugin'); ?><br>
                    <input type="text"
                           name="pressao_compartilhamento[imagens][<?php echo esc_attr($index); ?>][rotulo]"
                           value="<?php echo esc_attr($imagem['rotulo'] ?? ''); ?>"
                           class="regular-text"
                           placeholder="<?php esc_attr_e('Story/Status', 'pressao-plugin'); ?>" />
                </label>
            </p>
            <div class="pressao-share-imagem-field">
                <input type="hidden"
                       class="pressao-share-imagem-id"
                       name="pressao_compartilhamento[imagens][<?php echo esc_attr($index); ?>][imagem_id]"
                       value="<?php echo esc_attr($imagem_id); ?>" />
                <div class="pressao-share-imagem-preview">
                    <?php if ($imagem_url) : ?>
                        <img src="<?php echo esc_url($imagem_url); ?>" alt="" />
                    <?php endif; ?>
                </div>
                <button type="button" class="button pressao-select-share-imagem">
                    <?php esc_html_e('Selecionar imagem', 'pressao-plugin'); ?>
                </button>
                <button type="button" class="button pressao-remove-share-imagem-file">
                    <?php esc_html_e('Remover imagem', 'pressao-plugin'); ?>
                </button>
            </div>
            <p>
                <button type="button" class="button link-delete pressao-remove-share-imagem">
                    <?php esc_html_e('Remover item', 'pressao-plugin'); ?>
                </button>
            </p>
            <hr>
        </div>
        <?php
    }

    public function sanitize_compartilhamento($value) {
        if (!is_array($value)) {
            return [];
        }

        $imagens = [];
        if (isset($value['imagens']) && is_array($value['imagens'])) {
            foreach ($value['imagens'] as $imagem) {
                if (!is_array($imagem)) {
                    continue;
                }
                $rotulo = sanitize_text_field($imagem['rotulo'] ?? '');
                $imagem_id = absint($imagem['imagem_id'] ?? 0);
                if ($rotulo === '' && !$imagem_id) {
                    continue;
                }
                $imagens[] = [
                    'rotulo' => $rotulo,
                    'imagem_id' => $imagem_id,
                ];
            }
        }

        return [
            'ativo' => !empty($value['ativo']) ? 1 : 0,
            'titulo' => sanitize_text_field($value['titulo'] ?? ''),
            'subtitulo' => sanitize_text_field($value['subtitulo'] ?? ''),
            'tempo' => sanitize_text_field($value['tempo'] ?? ''),
            'overlay_titulo' => sanitize_text_field($value['overlay_titulo'] ?? ''),
            'link' => esc_url_raw($value['link'] ?? ''),
            'mensagem' => sanitize_textarea_field($value['mensagem'] ?? ''),
            'whatsapp_url' => esc_url_raw($value['whatsapp_url'] ?? ''),
            'x_url' => esc_url_raw($value['x_url'] ?? ''),
            'instagram_url' => esc_url_raw($value['instagram_url'] ?? ''),
            'facebook_url' => esc_url_raw($value['facebook_url'] ?? ''),
            'imagens_titulo' => sanitize_text_field($value['imagens_titulo'] ?? ''),
            'imagens_subtitulo' => sanitize_text_field($value['imagens_subtitulo'] ?? ''),
            'imagens_instrucao' => sanitize_textarea_field($value['imagens_instrucao'] ?? ''),
            'imagens' => $imagens,
        ];
    }
}

new PressaoPlugin_Admin();