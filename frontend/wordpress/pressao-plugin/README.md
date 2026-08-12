# Pressão Plugin

Widget WordPress para integração com Keycloak e API Pressão.

## 📋 Sobre

O Pressão Plugin é um widget WordPress que integra sua aplicação com Keycloak para autenticação e consome a API Pressão. Ele faz parte do ecossistema Pressão e está localizado neste repositório como um dos frontends disponíveis.

## 📂 Localização no Repositório

Este plugin está na estrutura:

```text
pressao-api/
└── frontend/
    └── wordpress/
        └── pressao-plugin/ # ← Este plugin
```

## 🚀 Desenvolvimento

### Pré-requisitos

- Docker e Docker Compose
- Node.js (para assets, opcional)
- PHP 7.4+ (para desenvolvimento local)

### Setup com Docker

O plugin é desenvolvido dentro do ecossistema Pressão. Para iniciar o ambiente completo:

```bash
# Na pasta docker/ do repositório pressao-api
docker compose up -d

# O WordPress estará disponível em:
# http://localhost:8181
```

### Estrutura do plugin

```text
pressao-plugin/
├── pressao-plugin.php          # Arquivo principal
├── includes/
│   ├── class-main.php          # Funcionalidades gerais
│   ├── class-admin.php         # Configurações admin
│   ├── class-api.php           # Integração Keycloak/API
│   ├── class-shortcode.php     # Shortcodes
│   └── class-ajax.php          # AJAX handlers
├── assets/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── widget.js
└── views/
    └── widget-template.php
```

### Ativando o plugin

```bash
# Via WP-CLI
docker compose exec wordpress wp plugin activate pressao-plugin

# Ou pelo admin WordPress
# Plugins > Pressão Plugin > Ativar
```

### Configurando

Acesse Configurações > Pressão Plugin e preencha:

| Campo | Descrição |
|-------|-----------|
| URL do Keycloak | Endereço do servidor Keycloak |
| Realm | Realm do Keycloak |
| Client ID | ID do client configurado |
| Client Secret | Secret do client |
| URL da API | Endereço da API Pressão |
| ID da Campanha | ID da campanha para exibição |

### Debug

Para ativar o debug, no `wp-config.php`:

```bash
define('WP_DEBUG', true);
define('WP_DEBUG_LOG', true);
```

Ver logs:

```bash
docker compose exec wordpress tail -f /var/www/html/wp-content/debug.log
```

## Uso

### Shortcode Principal

```text
[pressao_widget]
```