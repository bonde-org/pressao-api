<?php
/**
 * Configuração personalizada do WordPress
 * O arquivo principal é gerado pelo WordPress, este é um override
 */

// Configurações de banco de dados
define('DB_NAME', getenv('WORDPRESS_DB_NAME') ?: 'pressao_db');
define('DB_USER', getenv('WORDPRESS_DB_USER') ?: 'pressao_user');
define('DB_PASSWORD', getenv('WORDPRESS_DB_PASSWORD') ?: 'secure_password_here');
define('DB_HOST', getenv('WORDPRESS_DB_HOST') ?: 'db:3306');
define('DB_CHARSET', 'utf8');
define('DB_COLLATE', '');

// Debug
define('WP_DEBUG', getenv('WORDPRESS_DEBUG') === 'true');
define('WP_DEBUG_LOG', getenv('WORDPRESS_DEBUG_LOG') === 'true');
define('WP_DEBUG_DISPLAY', getenv('WORDPRESS_DEBUG_DISPLAY') === 'true');
define('SCRIPT_DEBUG', getenv('SCRIPT_DEBUG') === 'true');

// URL pública: permite acessar via localhost e via Tailscale (IP ou MagicDNS)
// no celular. Prioridade: WORDPRESS_URL no .env → Host da requisição → localhost.
if (!function_exists('pressao_wp_public_url')) {
    function pressao_wp_public_url() {
        $from_env = getenv('WORDPRESS_URL');
        if (is_string($from_env) && $from_env !== '') {
            return rtrim($from_env, '/');
        }

        $host = isset($_SERVER['HTTP_HOST']) ? (string) $_SERVER['HTTP_HOST'] : '';
        // Host[:porta] apenas — evita Host header injection em ambiente local.
        if ($host !== '' && preg_match('/^[a-zA-Z0-9.-]+(?::\d{1,5})?$/', $host)) {
            $https = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off')
                || (isset($_SERVER['HTTP_X_FORWARDED_PROTO']) && $_SERVER['HTTP_X_FORWARDED_PROTO'] === 'https')
                || (isset($_SERVER['SERVER_PORT']) && (string) $_SERVER['SERVER_PORT'] === '443');
            return ($https ? 'https' : 'http') . '://' . $host;
        }

        return 'http://localhost:8181';
    }
}
$pressao_wp_url = pressao_wp_public_url();
define('WP_HOME', $pressao_wp_url);
define('WP_SITEURL', $pressao_wp_url);

// Prefixo das tabelas
$table_prefix = getenv('WORDPRESS_TABLE_PREFIX') ?: 'wp_';

// Chaves de segurança (use wp-salts.php para produção)
define('AUTH_KEY',         'put your unique phrase here');
define('SECURE_AUTH_KEY',  'put your unique phrase here');
define('LOGGED_IN_KEY',    'put your unique phrase here');
define('NONCE_KEY',        'put your unique phrase here');
define('AUTH_SALT',        'put your unique phrase here');
define('SECURE_AUTH_SALT', 'put your unique phrase here');
define('LOGGED_IN_SALT',   'put your unique phrase here');
define('NONCE_SALT',       'put your unique phrase here');

// Ambiente local (Docker): Application Passwords funcionam em HTTP
if (!defined('WP_ENVIRONMENT_TYPE')) {
    define('WP_ENVIRONMENT_TYPE', 'local');
}

// Desativa edição de plugins pelo admin (recomendado)
define('DISALLOW_FILE_EDIT', true);

// Configurações de memória
define('WP_MEMORY_LIMIT', '256M');
define('WP_MAX_MEMORY_LIMIT', '512M');

/* Isso é tudo, pare de editar! */

// Caminho absoluto do WordPress
if (!defined('ABSPATH')) {
    define('ABSPATH', __DIR__ . '/');
}

// Inclui o arquivo de configuração do WordPress
if (file_exists(ABSPATH . 'wp-settings.php')) {
    require_once ABSPATH . 'wp-settings.php';
}