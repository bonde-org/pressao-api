#!/bin/bash
set -e

echo "🔍 Inicializando PostgreSQL..."

# Função para criar banco se não existir
create_db_if_not_exists() {
    local dbname=$1
    local owner=$2
    
    echo "📋 Verificando banco: $dbname"
    
    # Verifica se o banco já existe
    if psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" -tAc "SELECT 1 FROM pg_database WHERE datname='$dbname'" | grep -q 1; then
        echo "✅ Banco '$dbname' já existe"
    else
        echo "🔄 Criando banco: $dbname"
        psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
            CREATE DATABASE $dbname;
            GRANT ALL PRIVILEGES ON DATABASE $dbname TO $owner;
EOSQL
        echo "✅ Banco '$dbname' criado com sucesso!"
    fi
}

# Cria os bancos
echo "🚀 Criando bancos de dados..."

# Banco do Keycloak
create_db_if_not_exists "keycloak" "$POSTGRES_USER"

# Banco da API
create_db_if_not_exists "pressao" "$POSTGRES_USER"

echo "✅ Inicialização concluída!"