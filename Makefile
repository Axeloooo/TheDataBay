# =============================================================================
# TheDataBay monorepo Makefile
# Run from the repo root. Requires: forge, cast, anvil, tilt, kubectl, terraform
# Copy .env.example → .env and fill in secrets before running EVM targets.
# =============================================================================

SHELL := /bin/bash
-include .env

# ── Paths ────────────────────────────────────────────────────────────────────
EVM_DIR            := evm
DEPLOY_SCRIPT      := script/DeployMarketplace.s.sol:DeployMarketplace
MINT_SCRIPT        := script/MintMockTokens.s.sol:MintMockTokens
DEPLOYMENTS_DIR    := $(EVM_DIR)/deployments
ANVIL_ADDR_FILE    := $(DEPLOYMENTS_DIR)/anvil_marketplace.addr
ANVIL_USDC_ADDR_FILE := $(DEPLOYMENTS_DIR)/anvil_usdc.addr
ANVIL_CADC_ADDR_FILE := $(DEPLOYMENTS_DIR)/anvil_cadc.addr
TF_DIR             := infra/terraform/environments/production
ANVIL_HOST         ?= 0.0.0.0
ANVIL_PORT         ?= 8545

.PHONY: help \
        dev-up dev-down \
        anvil stop-anvil \
        deploy-anvil seed-anvil mint-tokens-anvil \
        deploy-base-sepolia mint-tokens-base-sepolia \
        evm-build evm-test evm-fmt \
        api-test \
        client-build client-lint \
        tf-init tf-plan tf-apply \
        k8s-deploy-prod k8s-status k8s-rollback \
        test fmt build \
        sync-contract-config

# ── Help ─────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "TheDataBay Makefile"
	@echo ""
	@echo "Dev environment:"
	@echo "  dev-up                   Start full local stack (Tilt + Minikube)"
	@echo "  dev-down                 Stop Tilt session"
	@echo ""
	@echo "EVM / Anvil (local):"
	@echo "  anvil                    Start local Anvil node on $$(ANVIL_HOST):$$(ANVIL_PORT)"
	@echo "  stop-anvil               Stop local Anvil node"
	@echo "  deploy-anvil             Deploy Marketplace to Anvil, sync addresses to .env"
	@echo "  seed-anvil               Seed demo listings on local Anvil"
	@echo "  mint-tokens-anvil        Mint MockUSDC + MockCADC on Anvil (MINT_RECIPIENT=0x...)"
	@echo ""
	@echo "EVM / Base Sepolia (testnet):"
	@echo "  deploy-base-sepolia      Deploy Marketplace to Base Sepolia"
	@echo "  mint-tokens-base-sepolia Mint MockUSDC + MockCADC on Base Sepolia"
	@echo ""
	@echo "EVM build & test:"
	@echo "  evm-build                Compile contracts, export ABI to api/app/contracts/"
	@echo "  evm-test                 Run Foundry test suite"
	@echo "  evm-fmt                  Format Solidity files"
	@echo ""
	@echo "API:"
	@echo "  api-test                 Run pytest suite"
	@echo ""
	@echo "Client:"
	@echo "  client-build             Type-check + production build"
	@echo "  client-lint              ESLint"
	@echo ""
	@echo "Terraform (production):"
	@echo "  tf-init                  terraform init"
	@echo "  tf-plan                  terraform plan"
	@echo "  tf-apply                 terraform apply"
	@echo ""
	@echo "Kubernetes (production):"
	@echo "  k8s-deploy-prod          Apply all production manifests in order"
	@echo "  k8s-status               Show pod and ingress status"
	@echo "  k8s-rollback             Roll back backend and frontend deployments"
	@echo ""
	@echo "Meta:"
	@echo "  test                     Run all test suites (EVM + API)"
	@echo "  fmt                      Format all code (Solidity + Python)"
	@echo "  build                    Build all artefacts (contracts + client)"

# ── Dev environment ───────────────────────────────────────────────────────────
dev-up:
	tilt up

dev-down:
	tilt down

# ── EVM / Anvil ───────────────────────────────────────────────────────────────
anvil:
	@anvil --host $(ANVIL_HOST) --port $(ANVIL_PORT)

stop-anvil:
	@pkill -f "anvil --host $(ANVIL_HOST) --port $(ANVIL_PORT)" || pkill -f "anvil .*--port $(ANVIL_PORT)" || true

deploy-anvil:
	@mkdir -p $(DEPLOYMENTS_DIR)
	@echo "Deploying to Anvil at $(ANVIL_RPC_URL)..."
	@cd $(EVM_DIR) && forge script $(DEPLOY_SCRIPT) \
		--rpc-url $(ANVIL_RPC_URL) \
		--broadcast \
		--private-key $(ANVIL_PRIVATE_KEY)
	@echo "Extracting deployed addresses..."
	@if ! command -v jq >/dev/null 2>&1; then \
		echo "ERROR: jq is required but not installed."; exit 1; \
	fi
	@ADDR=$$(jq -r '.transactions[] | select(.transactionType=="CREATE") | .contractAddress' \
		$(EVM_DIR)/broadcast/DeployMarketplace.s.sol/31337/run-latest.json | tail -n 1); \
	if [ -z "$$ADDR" ]; then echo "ERROR: could not extract deployed address"; exit 1; fi; \
	echo $$ADDR > $(ANVIL_ADDR_FILE); \
	USDC=$$(cast call $$ADDR "acceptedTokenAt(uint256)(address)" 0 --rpc-url $(ANVIL_RPC_URL)); \
	CADC=$$(cast call $$ADDR "acceptedTokenAt(uint256)(address)" 1 --rpc-url $(ANVIL_RPC_URL)); \
	echo $$USDC > $(ANVIL_USDC_ADDR_FILE); \
	echo $$CADC > $(ANVIL_CADC_ADDR_FILE); \
	echo "Marketplace: $$ADDR"; \
	echo "USDC:        $$USDC"; \
	echo "CADC:        $$CADC"
	@$(MAKE) sync-contract-config

seed-anvil:
	@ADDR=$$(cat $(ANVIL_ADDR_FILE)); \
	echo "Seeding Marketplace at $$ADDR..."; \
	cd $(EVM_DIR) && forge script script/SeedMarketplace.s.sol:SeedMarketplace \
		--sig "run(address)" $$ADDR \
		--rpc-url $(ANVIL_RPC_URL) \
		--broadcast \
		--private-key $(ANVIL_PRIVATE_KEY)

mint-tokens-anvil:
	@USDC=$$(cat $(ANVIL_USDC_ADDR_FILE)); \
	CADC=$$(cat $(ANVIL_CADC_ADDR_FILE)); \
	TO=$${MINT_RECIPIENT:-$$(cast wallet address --private-key $(ANVIL_PRIVATE_KEY))}; \
	echo "Minting to $$TO..."; \
	cd $(EVM_DIR) && PRIVATE_KEY=$(ANVIL_PRIVATE_KEY) \
	USDC_ADDRESS=$$USDC \
	CADC_ADDRESS=$$CADC \
	MINT_RECIPIENT=$$TO \
	forge script $(MINT_SCRIPT) \
		--rpc-url $(ANVIL_RPC_URL) \
		--broadcast

# ── EVM / Base Sepolia ────────────────────────────────────────────────────────
deploy-base-sepolia:
	@echo "Deploying to Base Sepolia..."
	@cd $(EVM_DIR) && forge script $(DEPLOY_SCRIPT) \
		--rpc-url $(BASE_SEPOLIA_RPC_URL) \
		--broadcast \
		--verify \
		--etherscan-api-key $(ETHERSCAN_API_KEY) \
		--private-key $(BASE_SEPOLIA_PRIVATE_KEY)

mint-tokens-base-sepolia:
	@TO=$${MINT_RECIPIENT:-$$(cast wallet address --private-key $(BASE_SEPOLIA_PRIVATE_KEY))}; \
	echo "Minting to $$TO on Base Sepolia..."; \
	cd $(EVM_DIR) && PRIVATE_KEY=$(BASE_SEPOLIA_PRIVATE_KEY) \
	USDC_ADDRESS=$(BASE_SEPOLIA_USDC_ADDRESS) \
	CADC_ADDRESS=$(BASE_SEPOLIA_CADC_ADDRESS) \
	MINT_RECIPIENT=$$TO \
	forge script $(MINT_SCRIPT) \
		--rpc-url $(BASE_SEPOLIA_RPC_URL) \
		--broadcast

# ── EVM build & test ──────────────────────────────────────────────────────────
evm-build:
	@mkdir -p api/app/contracts
	@cd $(EVM_DIR) && forge build
	@jq '.abi' $(EVM_DIR)/out/Marketplace.sol/Marketplace.json > api/app/contracts/Marketplace.json
	@echo "ABI exported to api/app/contracts/Marketplace.json"

evm-test:
	@cd $(EVM_DIR) && forge test -v

evm-fmt:
	@cd $(EVM_DIR) && forge fmt

# ── API ───────────────────────────────────────────────────────────────────────
api-test:
	@cd api && source .venv/bin/activate && pytest -q

# ── Client ────────────────────────────────────────────────────────────────────
client-build:
	@cd client && npm run build

client-lint:
	@cd client && npm run lint

# ── Terraform (production) ────────────────────────────────────────────────────
tf-init:
	@cd $(TF_DIR) && terraform init

tf-plan:
	@cd $(TF_DIR) && terraform plan

tf-apply:
	@cd $(TF_DIR) && terraform apply

# ── Kubernetes (production) ───────────────────────────────────────────────────
k8s-deploy-prod:
	@echo "Applying production manifests..."
	@kubectl apply -f infra/k8s/production/namespace.yaml
	@kubectl apply -f infra/k8s/production/secret-provider-class.yaml
	@kubectl apply -f infra/k8s/production/postgres-statefulset.yaml
	@kubectl wait --namespace thedatabay --for=condition=ready pod \
		--selector=app=postgres --timeout=180s
	@kubectl apply -f infra/k8s/production/cert-manager/cluster-issuer.yaml
	@kubectl apply -f infra/k8s/production/backend-deployment.yaml
	@kubectl apply -f infra/k8s/production/frontend-deployment.yaml
	@kubectl apply -f infra/k8s/production/ingress.yaml
	@kubectl apply -f infra/k8s/production/hpa.yaml
	@kubectl apply -f infra/k8s/production/pdb.yaml
	@kubectl rollout status deployment/backend -n thedatabay --timeout=180s
	@kubectl rollout status deployment/frontend -n thedatabay --timeout=180s
	@echo "Production deploy complete."

k8s-status:
	@kubectl get pods -n thedatabay
	@echo ""
	@kubectl get svc -n ingress-nginx ingress-nginx-controller 2>/dev/null || true

k8s-rollback:
	@kubectl rollout undo deployment/backend -n thedatabay
	@kubectl rollout undo deployment/frontend -n thedatabay

# ── Meta ─────────────────────────────────────────────────────────────────────
test: evm-test api-test

fmt: evm-fmt
	@cd api && source .venv/bin/activate && ruff format . 2>/dev/null || true

build: evm-build client-build

# ── Internal: sync deployed Anvil addresses back into root .env and secrets ──
sync-contract-config:
	@ADDR=$$(cat $(ANVIL_ADDR_FILE)); \
	TOKEN=$$(cat $(ANVIL_USDC_ADDR_FILE)); \
	CADC_TOKEN=$$(cat $(ANVIL_CADC_ADDR_FILE)); \
	echo "Syncing deployed addresses to .env and secrets.yaml..."; \
	if [ -f ".env" ]; then \
		perl -0pi -e 's/^CONTRACT_ADDRESS=.*$$/CONTRACT_ADDRESS="'"$$ADDR"'"/m' .env; \
		perl -0pi -e 's/^USDC_TOKEN_ADDRESS=.*$$/USDC_TOKEN_ADDRESS="'"$$TOKEN"'"/m' .env; \
		perl -0pi -e 's/^CADC_TOKEN_ADDRESS=.*$$/CADC_TOKEN_ADDRESS="'"$$CADC_TOKEN"'"/m' .env; \
		echo "Updated .env"; \
	fi; \
	if [ -f "infra/k8s/development/secrets.yaml" ]; then \
		cp "infra/k8s/development/secrets.yaml" "infra/k8s/development/secrets.yaml.bak"; \
		perl -0pi -e 's/CONTRACT_ADDRESS: *"?[^"\n]*"?/CONTRACT_ADDRESS: "'"$$ADDR"'"/' \
			infra/k8s/development/secrets.yaml; \
		perl -0pi -e 's/USDC_TOKEN_ADDRESS: *"?[^"\n]*"?/USDC_TOKEN_ADDRESS: "'"$$TOKEN"'"/' \
			infra/k8s/development/secrets.yaml; \
		perl -0pi -e 's/CADC_TOKEN_ADDRESS: *"?[^"\n]*"?/CADC_TOKEN_ADDRESS: "'"$$CADC_TOKEN"'"/' \
			infra/k8s/development/secrets.yaml; \
		echo "Updated infra/k8s/development/secrets.yaml"; \
	fi
