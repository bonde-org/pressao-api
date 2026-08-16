# Helm chart — pressao-api

Chart em `pressao-api/helm/`. Instala a API no Kubernetes e, **opcionalmente**, um PostgreSQL gerenciado pelo [CloudNativePG](https://cloudnative-pg.io/) (CNPG).

**Banco integrado desligado por padrão** (`database.enabled: false`). Sem CNPG, a API lê `DATABASE_URL` de um Secret.

## Pré-requisitos

- Kubernetes 1.25+
- Helm 3.12+
- Imagem da API publicada (`image.repository` / `image.tag`)
- Se `database.enabled: true`: operador **CloudNativePG** instalado no cluster
- Se backup Barman Cloud: plugin `barman-cloud.cloudnative-pg.io` e um `ObjectStore` referenciado em `database.backup.clusterPlugin.parameters.barmanObjectName`

## Instalação rápida (banco externo)

```bash
cd pressao-api

helm upgrade --install pressao-api ./helm \
  --set secrets.DATABASE_URL='postgresql://user:pass@host:5432/pressao' \
  --set secrets.SECRET_KEY='...' \
  --set secrets.KEYCLOAK_CLIENT_SECRET='...'
```

Ou aponte um Secret já existente:

```bash
kubectl create secret generic pressao-db \
  --from-literal=DATABASE_URL='postgresql://user:pass@host:5432/pressao'

helm upgrade --install pressao-api ./helm \
  --set database.enabled=false \
  --set database.existingSecret=pressao-db \
  --set database.urlKey=DATABASE_URL \
  --set secrets.existingSecret=pressao-api-creds
```

O Secret `pressao-api-creds` deve conter pelo menos `SECRET_KEY`, `KEYCLOAK_CLIENT_SECRET`, `SENDGRID_API_KEY`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`.

## Ativar CloudNativePG

```bash
helm upgrade --install pressao-api ./helm \
  --set database.enabled=true \
  --set database.superuser.password='uma-senha-forte'
```

O chart cria:

| Recurso | Nome padrão |
|---------|-------------|
| `Cluster` | `{release}-pressao-api-pg` |
| Superuser Secret (`kubernetes.io/basic-auth`) | `{cluster}-superuser` |
| Secret da aplicação (CNPG) | `{cluster}-app` — chave `uri` |
| `ScheduledBackup` | só se `database.backup.enabled: true` |

A API injeta `DATABASE_URL` a partir da chave `uri` do Secret `{cluster}-app` (usuário dono do banco, não o superuser).

Espere o cluster ficar pronto antes das migrações:

```bash
kubectl wait --for=condition=Ready cluster/pressao-api-pressao-api-pg --timeout=300s
kubectl exec -it deploy/pressao-api-pressao-api -- alembic upgrade head
```

Para **desligar** o CNPG de novo: `database.enabled: false` e forneça `DATABASE_URL` (values ou Secret externo). O Helm **não** apaga PVCs automaticamente; remova o `Cluster` CNPG com cuidado se não quiser mais o volume.

## Ajustar CNPG por ambiente

| Campo | Uso |
|-------|-----|
| `database.instances` | Réplicas PostgreSQL (1 em dev, 3 em prod) |
| `database.storage.size` / `storageClass` | PVC dos dados |
| `database.walStorage` | PVC separado para WAL |
| `database.resources` | CPU/memória dos pods Postgres |
| `database.postgresql.parameters` | `max_connections`, `shared_buffers`, etc. |
| `database.monitoring.enablePodMonitor` | Prometheus Operator |
| `database.nodeSelector` / `tolerations` / `affinity` | Agendamento (CNPG `spec.affinity`) |
| `database.imageName` | Imagem PostgreSQL do CNPG |
| `database.database` / `owner` | Banco e usuário da API (`bootstrap.initdb`) |
| `database.backup.*` | `ScheduledBackup` + plugin Barman Cloud |

Backup (quando `database.backup.enabled` e `clusterPlugin.enabled`):

```yaml
database:
  backup:
    enabled: true
    schedule: "0 0 2 * * *"   # cron de 6 campos (CNPG)
    method: plugin
    plugin:
      name: barman-cloud.cloudnative-pg.io
    clusterPlugin:
      enabled: true
      name: barman-cloud.cloudnative-pg.io
      isWALArchiver: true
      parameters:
        barmanObjectName: pressao-pg-backup
```

Crie o `ObjectStore` do Barman **antes** do Cluster, no mesmo namespace.

## Overlays

| Arquivo | Perfil |
|---------|--------|
| `values.yaml` | Padrão: CNPG **off**, banco externo |
| `values-dev.yaml` | CNPG 1 instância, sem backup |
| `values-staging.yaml` | 2 instâncias, WAL extra, PodMonitor, backup |
| `values-prod.yaml` | 3 instâncias, HPA, Ingress TLS, `secrets.existingSecret` |

```bash
helm upgrade --install pressao-api ./helm -f helm/values.yaml -f helm/values-dev.yaml
helm upgrade --install pressao-api ./helm -f helm/values.yaml -f helm/values-staging.yaml
helm upgrade --install pressao-api ./helm -f helm/values.yaml -f helm/values-prod.yaml
```

## Segurança

- `database.superuser.password` no values é só para bootstrap. **Altere em produção**; o default é `CHANGE-ME-CNPG-SUPERUSER`.
- Não commite senhas reais. Prefira:
  - **[SealedSecrets](https://github.com/bitnami-labs/sealed-secrets)**: cifre o Secret da API e o Superuser Secret e aplique no cluster.
  - **[External Secrets Operator](https://external-secrets.io/)**: sincronize Vault / AWS Secrets Manager / GCP SM para Secrets Kubernetes com os nomes esperados (`secrets.existingSecret`, `database.superuser.secretName`, ou `database.existingSecret` quando CNPG está off).
- Com CNPG ligado, **não** coloque `DATABASE_URL` no Secret da API: o operador gera `{cluster}-app`.
- Com CNPG desligado, use `database.existingSecret` em vez de `secrets.DATABASE_URL` no Git.

Exemplo ExternalSecret (superuser CNPG):

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: pressao-pg-superuser
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault
    kind: ClusterSecretStore
  target:
    name: pressao-pg-superuser-prod
    template:
      type: kubernetes.io/basic-auth
  data:
    - secretKey: username
      remoteRef:
        key: pressao/cnpg
        property: username
    - secretKey: password
      remoteRef:
        key: pressao/cnpg
        property: password
```

Depois, em `values-prod.yaml`: `database.superuser.createSecret: false` e `database.superuser.secretName: pressao-pg-superuser-prod`. O Cluster CNPG referencia esse Secret; o Helm não o cria.

## Templates

- `templates/deployment.yaml`, `service.yaml`, `configmap.yaml`, `secret.yaml`, `serviceaccount.yaml`
- `templates/ingress.yaml`, `hpa.yaml` (condicionais)
- `templates/cnpg-cluster.yaml`, `cnpg-scheduledbackup.yaml`, `cnpg-superuser-secret.yaml` (se `database.enabled`)
