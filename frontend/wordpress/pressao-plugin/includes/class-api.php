<?php
/**
 * Classe de integração com API e Keycloak
 * 
 * @package PressaoPlugin
 */

if (!defined('ABSPATH')) {
    exit;
}

class PressaoPlugin_API {
    
    private $keycloak_url;
    private $realm;
    private $client_id;
    private $client_secret;
    private $api_url;
    private $token_cache_key = 'pressao_keycloak_token';
    
    public function __construct() {
        $this->keycloak_url = get_option('pressao_keycloak_url', '');
        $this->realm = get_option('pressao_realm', 'master');
        $this->client_id = get_option('pressao_client_id', '');
        $this->client_secret = get_option('pressao_client_secret', '');
        $this->api_url = get_option('pressao_api_url', '');
    }
    
    /**
     * Obtém token do Keycloak com cache
     */
    public function get_token() {
        $cached_token = get_transient($this->token_cache_key);
        if ($cached_token) {
            return $cached_token;
        }
        
        $token_data = $this->fetch_new_token();

        if ($token_data && isset($token_data['access_token'])) {
            $expires_in = isset($token_data['expires_in']) ? intval($token_data['expires_in']) : 300;
            $expires_in = $expires_in - 30; // Margem de segurança
            
            set_transient($this->token_cache_key, $token_data['access_token'], $expires_in);
            return $token_data['access_token'];
        }
        
        return false;
    }
    
    /**
     * Busca novo token no Keycloak
     */
    private function fetch_new_token() {
        if (empty($this->keycloak_url) || empty($this->client_id) || empty($this->client_secret)) {
            error_log('Pressão Plugin: Configurações do Keycloak incompletas');
            return false;
        }
        
        $url = trailingslashit($this->keycloak_url) . 'realms/' . trailingslashit($this->realm) . 'protocol/openid-connect/token';
        
        $response = wp_remote_post($url, [
            'body' => [
                'client_id' => $this->client_id,
                'client_secret' => $this->client_secret,
                'grant_type' => 'client_credentials'
            ],
            'timeout' => 10,
            'sslverify' => apply_filters('pressao_ssl_verify', true)
        ]);
        
        if (is_wp_error($response)) {
            error_log('Pressão Plugin - Erro ao obter token Keycloak: ' . $response->get_error_message());
            return false;
        }
        
        $body = wp_remote_retrieve_body($response);
        $status = wp_remote_retrieve_response_code($response);
        
        if ($status !== 200) {
            error_log('Pressão Plugin - Keycloak retornou status ' . $status . ': ' . $body);
            return false;
        }
        
        $data = json_decode($body, true);
        
        if (!isset($data['access_token'])) {
            error_log('Pressão Plugin - Resposta inválida do Keycloak: ' . $body);
            return false;
        }
        
        return $data;
    }
    
    /**
     * Faz requisição para a API
     */
    public function api_request($endpoint, $method = 'GET', $data = null, $retry = true) {
        $token = $this->get_token();

        if (!$token) {
            return new WP_Error(
                'auth_error',
                __('Não foi possível obter token de autenticação', 'pressao-plugin')
            );
        }
        
        if (empty($this->api_url)) {
            return new WP_Error(
                'config_error',
                __('URL da API não configurada', 'pressao-plugin')
            );
        }
        
        $url = trailingslashit($this->api_url) . ltrim($endpoint, '/');
        $args = [
            'method' => $method,
            'headers' => [
                'Authorization' => 'Bearer ' . $token,
                'Content-Type' => 'application/json',
                'Accept' => 'application/json',
            ],
            'timeout' => 30,
        ];
        
        if ($data && in_array($method, ['POST', 'PUT', 'PATCH'])) {
            $args['body'] = json_encode($data);
        }
        
        $response = wp_remote_request($url, $args);

        if (is_wp_error($response)) {
            return $response;
        }
        
        $status = wp_remote_retrieve_response_code($response);
        $body = wp_remote_retrieve_body($response);
        
        // Se token expirou, tenta novamente
        if ($status === 401 && $retry) {
            delete_transient($this->token_cache_key);
            return $this->api_request($endpoint, $method, $data, false);
        }
        
        $decoded_body = json_decode($body, true);

        if ($status >= 400) {
            $error_message = isset($decoded_body['message']) 
                ? $decoded_body['message'] 
                : sprintf(__('Erro %d na requisição', 'pressao-plugin'), $status);
            
            return new WP_Error(
                'api_error_' . $status,
                $error_message,
                ['status' => $status, 'body' => $decoded_body]
            );
        }
        
        return $decoded_body;
    }
    
    /**
     * Obtém dados de uma campanha específica
     */
    public function get_campanha($campanha_id) {
        if (empty($campanha_id)) {
            return new WP_Error(
                'invalid_campaign',
                __('ID da campanha não informado', 'pressao-plugin')
            );
        }
        
        $endpoint = sprintf('/api/v1/campanhas/%s', $campanha_id);
        $response = $this->api_request($endpoint, 'GET');
        
        if (is_wp_error($response)) {
            return $response;
        }
        
        // A resposta já é o objeto da campanha
        return $response;
    }
    
    /**
     * Obtém campanha do cache ou da API
     */
    public function get_campanha_cached($campanha_id, $cache_time = 3600) {
        $cache_key = 'pressao_campanha_' . md5($campanha_id);
        $cached = get_transient($cache_key);
        
        if ($cached !== false) {
            return [
                'success' => true,
                'data' => $cached,
                'cached' => true
            ];
        }
        
        $result = $this->get_campanha($campanha_id);
        
        if (is_wp_error($result)) {
            return $result;
        }
        
        // Cache apenas se tiver dados
        if (!empty($result)) {
            set_transient($cache_key, $result, $cache_time);
        }
        
        return [
            'success' => true,
            'data' => $result,
            'cached' => false
        ];
    }
}