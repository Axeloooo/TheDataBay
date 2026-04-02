# IP-Factory Production Deployment Runbook

## Prerequisites

Install the following tools:

- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) (`az`)
- [Terraform](https://developer.hashicorp.com/terraform/downloads) >= 1.5
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Docker](https://docs.docker.com/get-docker/)

Login to Azure:

```bash
az login
az account set --subscription "<YOUR_SUBSCRIPTION_ID>"
```

## Phase 1: Bootstrap Terraform Remote State (one-time)

```bash
# Create resource group for Terraform state
az group create --name ip-factory-tfstate-rg --location mexicocentral

# Create storage account (name must be globally unique)
az storage account create \
  --name ipfactorytfstate \
  --resource-group ip-factory-tfstate-rg \
  --location mexicocentral \
  --sku Standard_LRS

# Create blob container
az storage container create \
  --name tfstate \
  --account-name ipfactorytfstate
```

## Phase 2: Terraform — Provision Infrastructure

1. Get your Azure subscription ID and tenant ID:

```bash
az account show --query "{subscriptionId:id, tenantId:tenantId}" -o json
```

2. Create or update `infra/terraform/environments/production/.env` as a shell-sourceable bootstrap file:

```bash
export ARM_SUBSCRIPTION_ID="<YOUR_SUBSCRIPTION_ID>"
export ARM_TENANT_ID="<YOUR_TENANT_ID>"
_ip_factory_repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
export KEY_VAULT_NAME="$(cd "${_ip_factory_repo_root}/infra/terraform/environments/production" && terraform output -raw key_vault_name 2>/dev/null || true)"
export GITHUB_APP_PRIVATE_KEY_FILE="${_ip_factory_repo_root}/infra/k8s/development/github-app.pem"

export DATABASE_URL="mysql+pymysql://ipfactory:root@mysql:3306/ip_factory_db?charset=utf8mb4"
export FRONTEND_URL="https://chiselware.org"
export GITHUB_APP_ID="<VALUE>"
export GITHUB_ORG="<VALUE>"
export GITHUB_CLIENT_ID="<VALUE>"
export GITHUB_CLIENT_SECRET="<VALUE>"
export GITHUB_REDIRECT_URI="https://chiselware.org/api/v1/auth/github/callback"
export LINKEDIN_CLIENT_ID="<VALUE>"
export LINKEDIN_CLIENT_SECRET="<VALUE>"
export LINKEDIN_REDIRECT_URI="https://chiselware.org/api/v1/auth/linkedin/callback"
export TOKEN_ENC_KEY_B64="<VALUE>"
export JWT_SECRET_KEY="<VALUE>"
export INVITE_TOKEN_SECRET="<VALUE>"
export SENDGRID_API_KEY="<VALUE>"
export EMAIL_FROM="<VALUE>"
export STRIPE_SECRET_KEY="<VALUE>"
export STRIPE_SUCCESS_URL="https://chiselware.org/checkout/success"
export STRIPE_CANCEL_URL="https://chiselware.org/checkout/cancel"
export STRIPE_WEBHOOK_SECRET="<VALUE>"
export MYSQL_ROOT_PASSWORD="root"
export MYSQL_DATABASE="ip_factory_db"
export MYSQL_USER="ipfactory"
export MYSQL_PASSWORD="root"
unset _ip_factory_repo_root
```

3. Source the environment variables:

```bash
source infra/terraform/environments/production/.env
```

4. Run Terraform commands:

```bash
cd infra/terraform/environments/production

# Initialize Terraform with remote backend
terraform init

# Preview changes
terraform plan

# Apply changes (creates AKS, ACR, Key Vault, VNet)
terraform apply

# Capture outputs for use in later phases
terraform output -json > /tmp/tf-outputs.json
export ACR_LOGIN_SERVER=$(terraform output -raw acr_login_server)
export KEY_VAULT_NAME=$(terraform output -raw key_vault_name)
```

## Phase 3: Populate Azure Key Vault

After Terraform completes, re-source the bootstrap file so `KEY_VAULT_NAME` resolves from Terraform output, then upload the runtime contract to Azure Key Vault.

```bash
source infra/terraform/environments/production/.env

az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "DATABASE-URL" --value "$DATABASE_URL"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "FRONTEND-URL" --value "$FRONTEND_URL"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "GITHUB-APP-ID" --value "$GITHUB_APP_ID"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "GITHUB-ORG" --value "$GITHUB_ORG"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "GITHUB-CLIENT-ID" --value "$GITHUB_CLIENT_ID"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "GITHUB-CLIENT-SECRET" --value "$GITHUB_CLIENT_SECRET"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "GITHUB-REDIRECT-URI" --value "$GITHUB_REDIRECT_URI"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "LINKEDIN-CLIENT-ID" --value "$LINKEDIN_CLIENT_ID"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "LINKEDIN-CLIENT-SECRET" --value "$LINKEDIN_CLIENT_SECRET"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "LINKEDIN-REDIRECT-URI" --value "$LINKEDIN_REDIRECT_URI"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "TOKEN-ENC-KEY-B64" --value "$TOKEN_ENC_KEY_B64"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "JWT-SECRET-KEY" --value "$JWT_SECRET_KEY"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "INVITE-TOKEN-SECRET" --value "$INVITE_TOKEN_SECRET"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "SENDGRID-API-KEY" --value "$SENDGRID_API_KEY"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "EMAIL-FROM" --value "$EMAIL_FROM"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "STRIPE-SECRET-KEY" --value "$STRIPE_SECRET_KEY"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "STRIPE-SUCCESS-URL" --value "$STRIPE_SUCCESS_URL"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "STRIPE-CANCEL-URL" --value "$STRIPE_CANCEL_URL"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "STRIPE-WEBHOOK-SECRET" --value "$STRIPE_WEBHOOK_SECRET"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "MYSQL-ROOT-PASSWORD" --value "$MYSQL_ROOT_PASSWORD"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "MYSQL-DATABASE" --value "$MYSQL_DATABASE"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "MYSQL-USER" --value "$MYSQL_USER"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "MYSQL-PASSWORD" --value "$MYSQL_PASSWORD"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "GITHUB-APP-PRIVATE-KEY" --file "$GITHUB_APP_PRIVATE_KEY_FILE"
```

## Phase 4: Build and Push Docker Images

```bash
# Set variables
ACR_LOGIN_SERVER=$(cd infra/terraform/environments/production && terraform output -raw acr_login_server)
TAG=$(git rev-parse --short HEAD)

# Login to ACR
az acr login --name ipfactoryprod

# Build and push API image (run from repo root)
docker build -f infra/docker/production/api.Dockerfile -t $ACR_LOGIN_SERVER/ip-factory/api:$TAG .
docker push $ACR_LOGIN_SERVER/ip-factory/api:$TAG

# Build and push UI image (VITE_SERVER_URL must stay on the origin host, not include /api/v1)
docker build \
  -f infra/docker/production/ui.Dockerfile \
  --build-arg VITE_SERVER_URL=https://chiselware.org \
  -t $ACR_LOGIN_SERVER/ip-factory/ui:$TAG \
  .
docker push $ACR_LOGIN_SERVER/ip-factory/ui:$TAG

echo "Images pushed: $ACR_LOGIN_SERVER/ip-factory/api:$TAG and $ACR_LOGIN_SERVER/ip-factory/ui:$TAG"
```

## Phase 5: Configure kubectl

```bash
az aks get-credentials \
  --resource-group ip-factory-production-rg \
  --name ip-factory-production-aks \
  --overwrite-existing

# Verify connection
kubectl get nodes
```

## Phase 6: Install ingress-nginx

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.6/deploy/static/provider/cloud/deploy.yaml

# Wait for controller to be ready
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s
```

## Phase 7: Install cert-manager

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.4/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --namespace cert-manager \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/instance=cert-manager \
  --timeout=90s
```

## Phase 8: Update Manifests and Deploy Application

Before deploying, update placeholder values in the manifests:

1. **secret-provider-class.yaml**: Replace `<AZURE_TENANT_ID>` with your Azure tenant ID:

   ```bash
   TENANT_ID=$(az account show --query tenantId -o tsv)
   sed -i '' "s/<AZURE_TENANT_ID>/$TENANT_ID/g" infra/k8s/production/secret-provider-class.yaml
   ```

2. **backend-deployment.yaml** and **frontend-deployment.yaml**: Replace `<ACR_LOGIN_SERVER>` and `<TAG>`:
   ```bash
   ACR_LOGIN_SERVER=$(cd infra/terraform/environments/production && terraform output -raw acr_login_server)
   TAG=$(git rev-parse --short HEAD)
   sed -i '' "s|<ACR_LOGIN_SERVER>|$ACR_LOGIN_SERVER|g" infra/k8s/production/backend-deployment.yaml
   sed -i '' "s|<ACR_LOGIN_SERVER>|$ACR_LOGIN_SERVER|g" infra/k8s/production/frontend-deployment.yaml
   sed -i '' "s|<TAG>|$TAG|g" infra/k8s/production/backend-deployment.yaml
   sed -i '' "s|<TAG>|$TAG|g" infra/k8s/production/frontend-deployment.yaml
   ```

Deploy in order:

```bash
# Create namespace
kubectl apply -f infra/k8s/production/namespace.yaml

# Apply CSI Secret Store classes (must be before workloads)
kubectl apply -f infra/k8s/production/secret-provider-class.yaml

# Deploy MySQL
kubectl apply -f infra/k8s/production/mysql-statefulset.yaml

# Wait for MySQL to be ready
kubectl wait --namespace ip-factory \
  --for=condition=ready pod \
  --selector=app=mysql \
  --timeout=120s

# Apply ConfigMap and ClusterIssuer
kubectl apply -f infra/k8s/production/configmap.yaml
kubectl apply -f infra/k8s/production/cert-manager/cluster-issuer.yaml

# Deploy backend and frontend
kubectl apply -f infra/k8s/production/backend-deployment.yaml
kubectl apply -f infra/k8s/production/frontend-deployment.yaml

# Apply Ingress, HPA, PDB
kubectl apply -f infra/k8s/production/ingress.yaml
kubectl apply -f infra/k8s/production/hpa.yaml
kubectl apply -f infra/k8s/production/pdb.yaml
```

## Phase 9: Configure DNS

The public entrypoint is the `ingress-nginx-controller` `LoadBalancer` service external IP. Create an apex `A` record for `chiselware.org` that points to that IP. Do not point DNS at `backend-svc`, `frontend-svc`, pod IPs, or node IPs. A low TTL is helpful for cutover.

```bash
# Get external IP (may take 2-3 minutes)
kubectl get svc -n ingress-nginx ingress-nginx-controller -w

# Once EXTERNAL-IP is assigned, create the apex A record:
INGRESS_IP=$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "Create A record: chiselware.org → $INGRESS_IP"

# Using Azure DNS (if domain is in Azure DNS):
RESOURCE_GROUP="ip-factory-production-rg"
az network dns record-set a add-record \
  --resource-group $RESOURCE_GROUP \
  --zone-name chiselware.org \
  --record-set-name "@" \
  --ipv4-address $INGRESS_IP
```

## Phase 10: Verify Deployment

```bash
# Check pod status
kubectl get pods -n ip-factory

# Confirm ingress external IP
kubectl get svc -n ingress-nginx ingress-nginx-controller

# Check frontend
curl https://chiselware.org/

# Check API
curl https://chiselware.org/api/v1/

# Check TLS certificate issuance
kubectl describe certificate ip-factory-tls -n ip-factory

# Check cert-manager logs if certificate is not ready
kubectl logs -n cert-manager -l app=cert-manager --tail=50
```

## Rollback

To rollback a deployment:

```bash
kubectl rollout undo deployment/backend -n ip-factory
kubectl rollout undo deployment/frontend -n ip-factory
```

To rollback to a specific revision:

```bash
kubectl rollout history deployment/backend -n ip-factory
kubectl rollout undo deployment/backend --to-revision=<N> -n ip-factory
```
