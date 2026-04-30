# Ulenor Production Deployment Runbook

This runbook provisions the Azure production foundation once, stores runtime
secrets in Azure Key Vault, builds Ulenor images into Azure Container Registry,
and deploys the Kubernetes manifests to AKS.

Production origin: `https://ulenor.com`

## Prerequisites

Install:

- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) (`az`)
- [Terraform](https://developer.hashicorp.com/terraform/downloads) >= 1.5
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Docker](https://docs.docker.com/get-docker/)

Login to Azure:

```bash
az login
az account set --subscription "<YOUR_SUBSCRIPTION_ID>"
```

## Phase 1: Bootstrap Terraform Remote State

Run once per Azure subscription. The storage account name must be globally
unique; change `ulenortfstate` if Azure reports it is already taken, and keep
`infra/terraform/backend.tf` in sync.

```bash
az group create --name ulenor-tfstate-rg --location mexicocentral

az storage account create \
  --name ulenortfstate \
  --resource-group ulenor-tfstate-rg \
  --location mexicocentral \
  --sku Standard_LRS

az storage container create \
  --name tfstate \
  --account-name ulenortfstate
```

## Phase 2: Provision Azure Infrastructure

Get your Azure subscription and tenant IDs:

```bash
az account show --query "{subscriptionId:id, tenantId:tenantId}" -o json
```

Create or update `infra/terraform/environments/production/.env` as a
shell-sourceable bootstrap file:

```bash
export ARM_SUBSCRIPTION_ID="<YOUR_SUBSCRIPTION_ID>"
export ARM_TENANT_ID="<YOUR_TENANT_ID>"
export KEY_VAULT_NAME="$(cd infra/terraform/environments/production && terraform output -raw key_vault_name 2>/dev/null || true)"

export APP_NAME="Ulenor API"
export APP_VERSION="0.1.0"
export ENVIRONMENT="production"
export HOST="0.0.0.0"
export PORT="8080"
export CORS_ORIGINS='["https://ulenor.com"]'
export OLLAMA_HOST="http://ollama-svc:11434"
export EMBEDDING_MODEL="nomic-embed-text"
export EMBEDDING_DIMENSION="768"
export MAX_FILE_SIZE_MB="50"
export MAX_DATASET_ROWS="50000"
export EMBEDDING_CHUNK_SIZE="256"
export TOP_K="10"
export K_ROWS="100"
export SIMILARITY_THRESHOLD="0.30"
export CACHE_MAXSIZE="100"
export POSTGRES_URL="postgresql+psycopg://ulenor:<PASSWORD>@postgres:5432/ulenor"
export POSTGRES_PASSWORD="<VALUE>"
export PINATA_API_KEY="<VALUE>"
export PINATA_SECRET_KEY="<VALUE>"
export PINATA_GATEWAY_URL="https://gateway.pinata.cloud"
export SERVER_PRIVATE_KEY="<EVM_PRIVATE_KEY>"
export CONTRACT_ADDRESS="<MARKETPLACE_CONTRACT_ADDRESS>"
export PAYMENT_TOKEN_ADDRESS="<USDC_TOKEN_ADDRESS>"
export CADC_TOKEN_ADDRESS="<CADC_TOKEN_ADDRESS>"
export CONTRACT_ABI_PATH="/code/app/contracts/Marketplace.json"
export CHAIN_ID="84532"
export RPC_URL="https://sepolia.base.org"
```

Provision AKS, ACR, Key Vault, VNet, and DNS:

```bash
source infra/terraform/environments/production/.env

cd infra/terraform/environments/production
terraform init
terraform plan
terraform apply

terraform output -json > /tmp/ulenor-tf-outputs.json
export ACR_LOGIN_SERVER="$(terraform output -raw acr_login_server)"
export KEY_VAULT_NAME="$(terraform output -raw key_vault_name)"
```

## Phase 3: Populate Azure Key Vault

Re-source the bootstrap file after Terraform completes so `KEY_VAULT_NAME`
resolves from Terraform output, then upload runtime secrets.

```bash
source infra/terraform/environments/production/.env

set_secret() {
  local name="$1"
  local value="$2"
  az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "$name" --value "$value"
}

set_secret APP-NAME "$APP_NAME"
set_secret APP-VERSION "$APP_VERSION"
set_secret ENVIRONMENT "$ENVIRONMENT"
set_secret HOST "$HOST"
set_secret PORT "$PORT"
set_secret CORS-ORIGINS "$CORS_ORIGINS"
set_secret OLLAMA-HOST "$OLLAMA_HOST"
set_secret EMBEDDING-MODEL "$EMBEDDING_MODEL"
set_secret EMBEDDING-DIMENSION "$EMBEDDING_DIMENSION"
set_secret MAX-FILE-SIZE-MB "$MAX_FILE_SIZE_MB"
set_secret MAX-DATASET-ROWS "$MAX_DATASET_ROWS"
set_secret EMBEDDING-CHUNK-SIZE "$EMBEDDING_CHUNK_SIZE"
set_secret TOP-K "$TOP_K"
set_secret K-ROWS "$K_ROWS"
set_secret SIMILARITY-THRESHOLD "$SIMILARITY_THRESHOLD"
set_secret CACHE-MAXSIZE "$CACHE_MAXSIZE"
set_secret POSTGRES-URL "$POSTGRES_URL"
set_secret POSTGRES-PASSWORD "$POSTGRES_PASSWORD"
set_secret PINATA-API-KEY "$PINATA_API_KEY"
set_secret PINATA-SECRET-KEY "$PINATA_SECRET_KEY"
set_secret PINATA-GATEWAY-URL "$PINATA_GATEWAY_URL"
set_secret SERVER-PRIVATE-KEY "$SERVER_PRIVATE_KEY"
set_secret CONTRACT-ADDRESS "$CONTRACT_ADDRESS"
set_secret PAYMENT-TOKEN-ADDRESS "$PAYMENT_TOKEN_ADDRESS"
set_secret CADC-TOKEN-ADDRESS "$CADC_TOKEN_ADDRESS"
set_secret CONTRACT-ABI-PATH "$CONTRACT_ABI_PATH"
set_secret CHAIN-ID "$CHAIN_ID"
set_secret RPC-URL "$RPC_URL"
```

## Phase 4: Build and Push Docker Images Manually

GitHub Actions normally handles this. Use these commands for an emergency
manual deployment.

```bash
ACR_LOGIN_SERVER="$(cd infra/terraform/environments/production && terraform output -raw acr_login_server)"
ACR_NAME="${ACR_LOGIN_SERVER%%.azurecr.io}"
TAG="$(git rev-parse --short HEAD)"

az acr login --name "$ACR_NAME"

docker build \
  -f infra/docker/production/server.Dockerfile \
  -t "$ACR_LOGIN_SERVER/ulenor/api:$TAG" \
  .
docker push "$ACR_LOGIN_SERVER/ulenor/api:$TAG"

docker build \
  -f infra/docker/production/client.Dockerfile \
  --build-arg VITE_API_URL=https://ulenor.com \
  --build-arg VITE_SERVER_URL=https://ulenor.com \
  --build-arg VITE_PINATA_GATEWAY_URL=https://gateway.pinata.cloud \
  --build-arg VITE_WALLETCONNECT_PROJECT_ID="<WALLETCONNECT_PROJECT_ID>" \
  --build-arg VITE_CONTRACT_ADDRESS="$CONTRACT_ADDRESS" \
  --build-arg VITE_PAYMENT_TOKEN_ADDRESS="$PAYMENT_TOKEN_ADDRESS" \
  --build-arg VITE_CADC_TOKEN_ADDRESS="$CADC_TOKEN_ADDRESS" \
  --build-arg VITE_CHAIN_ID=84532 \
  -t "$ACR_LOGIN_SERVER/ulenor/ui:$TAG" \
  .
docker push "$ACR_LOGIN_SERVER/ulenor/ui:$TAG"

echo "Images pushed:"
echo "$ACR_LOGIN_SERVER/ulenor/api:$TAG"
echo "$ACR_LOGIN_SERVER/ulenor/ui:$TAG"
```

## Phase 5: Configure kubectl

```bash
az aks get-credentials \
  --resource-group ulenor-production-rg \
  --name ulenor-production-aks \
  --overwrite-existing

kubectl get nodes
```

## Phase 6: Install ingress-nginx

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.6/deploy/static/provider/cloud/deploy.yaml

kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s
```

## Phase 7: Install cert-manager

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.4/cert-manager.yaml

kubectl wait --namespace cert-manager \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/instance=cert-manager \
  --timeout=90s
```

## Phase 8: Render and Deploy Manifests Manually

GitHub Actions renders these values automatically. For manual deployment,
render into `/tmp` so tracked templates stay unchanged.

```bash
ACR_LOGIN_SERVER="$(cd infra/terraform/environments/production && terraform output -raw acr_login_server)"
KEY_VAULT_NAME="$(cd infra/terraform/environments/production && terraform output -raw key_vault_name)"
TAG="$(git rev-parse --short HEAD)"
TENANT_ID="$(az account show --query tenantId -o tsv)"
SECRETS_PROVIDER_CLIENT_ID="$(az aks show \
  --resource-group ulenor-production-rg \
  --name ulenor-production-aks \
  --query addonProfiles.azureKeyvaultSecretsProvider.identity.clientId \
  -o tsv)"
export ACR_LOGIN_SERVER KEY_VAULT_NAME TAG TENANT_ID SECRETS_PROVIDER_CLIENT_ID

RENDER_DIR="/tmp/ulenor-k8s-$TAG"
rm -rf "$RENDER_DIR"
mkdir -p "$RENDER_DIR"
cp -R infra/k8s/production/. "$RENDER_DIR/"

find "$RENDER_DIR" -type f -name '*.yaml' -exec perl -pi -e '
  s|<ACR_LOGIN_SERVER>|$ENV{ACR_LOGIN_SERVER}|g;
  s|<TAG>|$ENV{TAG}|g;
  s|<KEY_VAULT_NAME>|$ENV{KEY_VAULT_NAME}|g;
  s|<AZURE_TENANT_ID>|$ENV{TENANT_ID}|g;
  s|<SECRETS_PROVIDER_CLIENT_ID>|$ENV{SECRETS_PROVIDER_CLIENT_ID}|g;
' {} +

grep -RInE '<[A-Z0-9_]+>' "$RENDER_DIR" && {
  echo "Unrendered Kubernetes placeholders remain."
  exit 1
}
```

Deploy in order:

```bash
kubectl apply -f "$RENDER_DIR/namespace.yaml"
kubectl apply -f "$RENDER_DIR/secret-provider-class.yaml"
kubectl apply -f "$RENDER_DIR/postgres-statefulset.yaml"
kubectl apply -f "$RENDER_DIR/ollama-deployment.yaml"

kubectl wait --namespace ulenor \
  --for=condition=ready pod \
  --selector=app=postgres \
  --timeout=180s

kubectl wait --namespace ulenor \
  --for=condition=ready pod \
  --selector=app=ollama \
  --timeout=600s

kubectl apply -f "$RENDER_DIR/cert-manager/cluster-issuer.yaml"
kubectl apply -f "$RENDER_DIR/backend-deployment.yaml"
kubectl apply -f "$RENDER_DIR/frontend-deployment.yaml"
kubectl apply -f "$RENDER_DIR/ingress.yaml"
kubectl apply -f "$RENDER_DIR/hpa.yaml"
kubectl apply -f "$RENDER_DIR/pdb.yaml"

kubectl rollout status deployment/backend -n ulenor --timeout=180s
kubectl rollout status deployment/ollama -n ulenor --timeout=600s
kubectl rollout status deployment/frontend -n ulenor --timeout=180s
```

## Phase 9: Configure DNS

The public entrypoint is the `ingress-nginx-controller` `LoadBalancer` service
external IP. Create an apex `A` record for `ulenor.com` that points to that IP.
Do not point DNS at `backend-svc`, `frontend-svc`, pod IPs, or node IPs.

```bash
kubectl get svc -n ingress-nginx ingress-nginx-controller -w

INGRESS_IP="$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"
echo "Create A record: ulenor.com -> $INGRESS_IP"

az network dns record-set a add-record \
  --resource-group ulenor-production-rg \
  --zone-name ulenor.com \
  --record-set-name "@" \
  --ipv4-address "$INGRESS_IP"
```

## Phase 10: GitHub Actions Production CD

The workflow `.github/workflows/deploy-production.yml` deploys on pushes to
`main` and on manual dispatch. Configure the repository `production`
environment with deployment protection rules if you want approval before AKS
changes are applied.

Required GitHub secrets:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

Required GitHub variables:

- `AZURE_RESOURCE_GROUP=ulenor-production-rg`
- `AKS_CLUSTER_NAME=ulenor-production-aks`
- `ACR_LOGIN_SERVER=<terraform output acr_login_server>`
- `KEY_VAULT_NAME=<terraform output key_vault_name>`
- `PRODUCTION_DOMAIN=ulenor.com`

Recommended GitHub variables for the static web build:

- `VITE_WALLETCONNECT_PROJECT_ID`
- `VITE_CONTRACT_ADDRESS`
- `VITE_PAYMENT_TOKEN_ADDRESS`
- `VITE_CADC_TOKEN_ADDRESS`
- `VITE_CHAIN_ID=84532`
- `PINATA_GATEWAY_URL=https://gateway.pinata.cloud`

The workflow does not run Terraform. Keep infrastructure provisioning as a
manual one-time operation unless production change control says otherwise.

## Phase 11: Verify Deployment

```bash
kubectl get pods -n ulenor
kubectl get svc -n ingress-nginx ingress-nginx-controller
kubectl get ingress -n ulenor

curl https://ulenor.com/
curl https://ulenor.com/api/v1/

kubectl exec -n ulenor deploy/ollama -- ollama list | grep nomic-embed-text
kubectl exec -n ulenor deploy/backend -- printenv OLLAMA_HOST
kubectl exec -n ulenor deploy/backend -- python - <<'PY'
from app.shared.vectorstore import warmup_model
from app.config.settings import get_settings
raise SystemExit(0 if warmup_model(get_settings()) else 1)
PY

curl -sS https://ulenor.com/api/v1/ai/similarity-search \
  -H 'content-type: application/json' \
  -d '{"query":"dog","limit":10}'

curl -sS https://ulenor.com/api/v1/ai/similarity-search \
  -H 'content-type: application/json' \
  -d '{"query":"men age 37 with chol 266","limit":10}'

kubectl describe certificate ulenor-tls -n ulenor
kubectl logs -n cert-manager -l app=cert-manager --tail=50
```

After deploying this search/indexing change, re-embed or backfill pre-launch
datasets so PGVector contains the new row and chunk document metadata. Search
sanity checks should confirm that `dog` and `cat` return no default matches,
`age 18` can surface low-relevance age-column datasets, and `men age 37 with
chol 266` ranks the heart/table sample above unrelated listings.

## Rollback

```bash
kubectl rollout undo deployment/backend -n ulenor
kubectl rollout undo deployment/frontend -n ulenor
```

Rollback to a specific revision:

```bash
kubectl rollout history deployment/backend -n ulenor
kubectl rollout undo deployment/backend --to-revision=<N> -n ulenor
```
