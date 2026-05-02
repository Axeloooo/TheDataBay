# TheDataBay Production Deployment Runbook

This runbook provisions the Azure production foundation once, stores runtime
secrets in Azure Key Vault, builds TheDataBay images into Azure Container Registry,
and deploys the Kubernetes manifests to AKS.

Production origin: `https://thedatabay.com`

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
unique; change `thedatabaytfstate` if Azure reports it is already taken, and keep
`infra/terraform/backend.tf` in sync.

```bash
az group create --name thedatabay-tfstate-rg --location mexicocentral

az storage account create \
  --name thedatabaytfstate \
  --resource-group thedatabay-tfstate-rg \
  --location mexicocentral \
  --sku Standard_LRS

az storage container create \
  --name tfstate \
  --account-name thedatabaytfstate
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

export APP_NAME="TheDataBay API"
export APP_VERSION="0.1.0"
export ENVIRONMENT="production"
export HOST="0.0.0.0"
export PORT="8080"
export CORS_ORIGINS='["https://thedatabay.com"]'
export LLM_PROVIDER="ollama"
export LLM_BASE_URL="http://ollama-svc:11434"
export LLM_CHAT_MODEL="deepseek-v4-flash:cloud"
export LLM_EMBEDDING_MODEL="nomic-embed-text"
export LLM_EMBEDDING_DIMENSION="768"
export LLM_THINK="false"
export OLLAMA_API_KEY=""
export DATASET_SUMMARY_COUNT="5"
export DATASET_SUMMARY_SAMPLE_ROWS="20"
export MAX_FILE_SIZE_MB="50"
export MAX_DATASET_ROWS="50000"
export TOP_K="10"
export SIMILARITY_THRESHOLD="0.30"
export CACHE_MAXSIZE="100"
export POSTGRES_URL="postgresql+psycopg://thedatabay:<PASSWORD>@postgres:5432/thedatabay"
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

terraform output -json > /tmp/thedatabay-tf-outputs.json
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
set_secret LLM-PROVIDER "$LLM_PROVIDER"
set_secret LLM-BASE-URL "$LLM_BASE_URL"
set_secret LLM-CHAT-MODEL "$LLM_CHAT_MODEL"
set_secret LLM-EMBEDDING-MODEL "$LLM_EMBEDDING_MODEL"
set_secret LLM-EMBEDDING-DIMENSION "$LLM_EMBEDDING_DIMENSION"
set_secret LLM-THINK "$LLM_THINK"
set_secret DATASET-SUMMARY-COUNT "$DATASET_SUMMARY_COUNT"
set_secret DATASET-SUMMARY-SAMPLE-ROWS "$DATASET_SUMMARY_SAMPLE_ROWS"
set_secret MAX-FILE-SIZE-MB "$MAX_FILE_SIZE_MB"
set_secret MAX-DATASET-ROWS "$MAX_DATASET_ROWS"
set_secret TOP-K "$TOP_K"
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
  -t "$ACR_LOGIN_SERVER/thedatabay/api:$TAG" \
  .
docker push "$ACR_LOGIN_SERVER/thedatabay/api:$TAG"

docker build \
  -f infra/docker/production/client.Dockerfile \
  --build-arg VITE_API_URL=https://thedatabay.com \
  --build-arg VITE_SERVER_URL=https://thedatabay.com \
  --build-arg VITE_PINATA_GATEWAY_URL=https://gateway.pinata.cloud \
  --build-arg VITE_WALLETCONNECT_PROJECT_ID="<WALLETCONNECT_PROJECT_ID>" \
  --build-arg VITE_CONTRACT_ADDRESS="$CONTRACT_ADDRESS" \
  --build-arg VITE_PAYMENT_TOKEN_ADDRESS="$PAYMENT_TOKEN_ADDRESS" \
  --build-arg VITE_CADC_TOKEN_ADDRESS="$CADC_TOKEN_ADDRESS" \
  --build-arg VITE_CHAIN_ID=84532 \
  -t "$ACR_LOGIN_SERVER/thedatabay/ui:$TAG" \
  .
docker push "$ACR_LOGIN_SERVER/thedatabay/ui:$TAG"

echo "Images pushed:"
echo "$ACR_LOGIN_SERVER/thedatabay/api:$TAG"
echo "$ACR_LOGIN_SERVER/thedatabay/ui:$TAG"
```

## Phase 5: Configure kubectl

```bash
az aks get-credentials \
  --resource-group thedatabay-production-rg \
  --name thedatabay-production-aks \
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
  --resource-group thedatabay-production-rg \
  --name thedatabay-production-aks \
  --query addonProfiles.azureKeyvaultSecretsProvider.identity.clientId \
  -o tsv)"
export ACR_LOGIN_SERVER KEY_VAULT_NAME TAG TENANT_ID SECRETS_PROVIDER_CLIENT_ID

RENDER_DIR="/tmp/thedatabay-k8s-$TAG"
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

if [ -n "$OLLAMA_API_KEY" ]; then
  kubectl create secret generic thedatabay-optional-secrets \
    -n thedatabay \
    --from-literal=OLLAMA_API_KEY="$OLLAMA_API_KEY" \
    --dry-run=client -o yaml | kubectl apply -f -
fi

kubectl apply -f "$RENDER_DIR/postgres-statefulset.yaml"
kubectl apply -f "$RENDER_DIR/ollama-deployment.yaml"

kubectl wait --namespace thedatabay \
  --for=condition=ready pod \
  --selector=app=postgres \
  --timeout=180s

kubectl wait --namespace thedatabay \
  --for=condition=ready pod \
  --selector=app=ollama \
  --timeout=600s

kubectl apply -f "$RENDER_DIR/cert-manager/cluster-issuer.yaml"
kubectl apply -f "$RENDER_DIR/backend-deployment.yaml"
kubectl apply -f "$RENDER_DIR/frontend-deployment.yaml"
kubectl apply -f "$RENDER_DIR/ingress.yaml"
kubectl apply -f "$RENDER_DIR/hpa.yaml"
kubectl apply -f "$RENDER_DIR/pdb.yaml"

kubectl rollout status deployment/backend -n thedatabay --timeout=180s
kubectl rollout status deployment/ollama -n thedatabay --timeout=600s
kubectl rollout status deployment/frontend -n thedatabay --timeout=180s
```

## Phase 9: Configure DNS

The public entrypoint is the `ingress-nginx-controller` `LoadBalancer` service
external IP. Create an apex `A` record for `thedatabay.com` that points to that IP.
Do not point DNS at `backend-svc`, `frontend-svc`, pod IPs, or node IPs.

```bash
kubectl get svc -n ingress-nginx ingress-nginx-controller -w

INGRESS_IP="$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"
echo "Create A record: thedatabay.com -> $INGRESS_IP"

az network dns record-set a add-record \
  --resource-group thedatabay-production-rg \
  --zone-name thedatabay.com \
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

- `AZURE_RESOURCE_GROUP=thedatabay-production-rg`
- `AKS_CLUSTER_NAME=thedatabay-production-aks`
- `ACR_LOGIN_SERVER=<terraform output acr_login_server>`
- `KEY_VAULT_NAME=<terraform output key_vault_name>`
- `PRODUCTION_DOMAIN=thedatabay.com`

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
kubectl get pods -n thedatabay
kubectl get svc -n ingress-nginx ingress-nginx-controller
kubectl get ingress -n thedatabay

curl https://thedatabay.com/
curl https://thedatabay.com/api/v1/

kubectl exec -n thedatabay deploy/ollama -- ollama list | grep nomic-embed-text
kubectl exec -n thedatabay deploy/ollama -- sh -c 'test -z "$OLLAMA_API_KEY" && echo "OLLAMA_API_KEY unset" || echo "OLLAMA_API_KEY set"'
kubectl exec -n thedatabay deploy/backend -- printenv LLM_BASE_URL
kubectl exec -n thedatabay deploy/backend -- sh -c 'test -z "$OLLAMA_API_KEY" && echo "OLLAMA_API_KEY unset" || echo "OLLAMA_API_KEY set"'
kubectl exec -n thedatabay deploy/backend -- python - <<'PY'
import asyncio

from app.config.settings import get_settings
from app.llm.services.ollama_provider import OllamaLLMService

async def main() -> int:
    settings = get_settings()
    result = await OllamaLLMService.from_settings(settings).embed_text("warmup")
    return 0 if result.dimension == settings.llm_embedding_dimension else 1

raise SystemExit(asyncio.run(main()))
PY

curl -sS https://thedatabay.com/api/v1/ai/similarity-search \
  -H 'content-type: application/json' \
  -d '{"query":"dog","limit":10}'

curl -sS https://thedatabay.com/api/v1/ai/similarity-search \
  -H 'content-type: application/json' \
  -d '{"query":"men age 37 with chol 266","limit":10}'

kubectl describe certificate thedatabay-tls -n thedatabay
kubectl logs -n cert-manager -l app=cert-manager --tail=50
```

After deploying this search/indexing change, re-embed or backfill pre-launch
datasets so PGVector contains the new `dataset_summaries` documents. Search
sanity checks should confirm that off-domain queries return no default matches
and dataset-oriented queries return whole marketplace listings with
`best_summary` evidence.

## Rollback

```bash
kubectl rollout undo deployment/backend -n thedatabay
kubectl rollout undo deployment/frontend -n thedatabay
```

Rollback to a specific revision:

```bash
kubectl rollout history deployment/backend -n thedatabay
kubectl rollout undo deployment/backend --to-revision=<N> -n thedatabay
```
