# Makefile for local Anvil deployment/testing
# Requires: foundry (forge, cast), and a .env file

SHELL := /bin/bash

-include .env

DEPLOY_SCRIPT := script/DeployMarketplace.s.sol:DeployMarketplace
DEPLOYMENTS_DIR := deployments
ANVIL_ADDR_FILE := $(DEPLOYMENTS_DIR)/anvil_marketplace.addr
ANVIL_USDC_ADDR_FILE := $(DEPLOYMENTS_DIR)/anvil_usdc.addr

.PHONY: help anvil stop-anvil clean deploy-anvil addr usdc-addr fee getall create-item buy-item seed-anvil mint-usdc sync-local-contract-config

help:
	@echo "Targets:"
	@echo "  anvil         - start anvil (port 8545)"
	@echo "  deploy-anvil  - deploy Marketplace to anvil and save address"
	@echo "  sync-local-contract-config - update local app config files with deployed address"
	@echo "  addr          - print deployed Marketplace address"
	@echo "  usdc-addr     - print deployed USDC token address"
	@echo "  fee           - call fee config getters"
	@echo "  getall        - call getAllItems()"
	@echo "  seed-anvil    - seed deterministic sample items for UI testing"
	@echo "  create-item   - create a sample item"
	@echo "  mint-usdc     - mint mock USDC to an address on Anvil"
	@echo "  buy-item      - approve USDC and buy itemId=0"
	@echo ""
	@echo "Env in .env:"
	@echo "  ANVIL_RPC_URL, ANVIL_PRIVATE_KEY, ANVIL_FEE_RECIPIENT, ANVIL_FEE_BPS, SEPOLIA_USDC_ADDRESS"

build:
	mkdir -p ../server/app/contracts
	forge build
	jq '.abi' out/Marketplace.sol/Marketplace.json > ../server/app/contracts/Marketplace.json


anvil:
	@anvil --host 127.0.0.1 --port 8545

# If you run anvil in background yourself, ignore this.
stop-anvil:
	@pkill -f "anvil --host 127.0.0.1 --port 8545" || true

clean:
	@rm -rf $(DEPLOYMENTS_DIR)

deploy-anvil:
	@mkdir -p $(DEPLOYMENTS_DIR)
	@echo "Deploying to Anvil at $(ANVIL_RPC_URL)..."
	@forge script $(DEPLOY_SCRIPT) \
		--rpc-url $(ANVIL_RPC_URL) \
		--broadcast \
		--private-key $(ANVIL_PRIVATE_KEY)
	@echo "Extracting deployed addresses..."
	@if ! command -v jq >/dev/null 2>&1; then \
		echo "ERROR: jq is required but not installed. Please install jq."; \
		exit 1; \
	fi; \
	ADDR=$$(jq -r '.transactions[] | select(.transactionType=="CREATE") | .contractAddress' broadcast/DeployMarketplace.s.sol/31337/run-latest.json | tail -n 1); \
	if [ -z "$$ADDR" ]; then \
		echo "ERROR: Could not extract deployed address from broadcast JSON"; \
		exit 1; \
	fi; \
	echo $$ADDR > $(ANVIL_ADDR_FILE); \
	USDC_ADDR=$$(cast call $$ADDR "settlementToken()(address)" --rpc-url $(ANVIL_RPC_URL)); \
	echo $$USDC_ADDR > $(ANVIL_USDC_ADDR_FILE); \
	echo "Saved marketplace address to $(ANVIL_ADDR_FILE): $$ADDR"; \
	echo "Saved USDC address to $(ANVIL_USDC_ADDR_FILE): $$USDC_ADDR"
	@$(MAKE) sync-local-contract-config

sync-local-contract-config:
	@ADDR=$$(cat $(ANVIL_ADDR_FILE)); \
	echo "Syncing local config files to marketplace address $$ADDR..."; \
	if [ -f "../infra/k8s/development/secrets.yaml" ]; then \
		cp "../infra/k8s/development/secrets.yaml" "../infra/k8s/development/secrets.yaml.bak"; \
		perl -0pi -e 's/CONTRACT_ADDRESS: "[^"]+"/CONTRACT_ADDRESS: "'"$$ADDR"'"/' ../infra/k8s/development/secrets.yaml; \
		echo "Updated ../infra/k8s/development/secrets.yaml"; \
	fi; \
	if [ -f "../server/.env" ]; then \
		cp "../server/.env" "../server/.env.bak"; \
		perl -0pi -e 's/CONTRACT_ADDRESS="[^"]+"/CONTRACT_ADDRESS="'"$$ADDR"'"/' ../server/.env; \
		echo "Updated ../server/.env"; \
	fi

addr:
	@if [ -f "$(ANVIL_ADDR_FILE)" ]; then cat $(ANVIL_ADDR_FILE); else echo "No address file. Run: make deploy-anvil"; fi

usdc-addr:
	@if [ -f "$(ANVIL_USDC_ADDR_FILE)" ]; then cat $(ANVIL_USDC_ADDR_FILE); else echo "No USDC address file. Run: make deploy-anvil"; fi

fee:
	@ADDR=$$(cat $(ANVIL_ADDR_FILE)); \
	echo "feeBps:"; cast call $$ADDR "feeBps()(uint256)" --rpc-url $(ANVIL_RPC_URL); \
	echo "feeRecipient:"; cast call $$ADDR "feeRecipient()(address)" --rpc-url $(ANVIL_RPC_URL)

getall:
	@ADDR=$$(cat $(ANVIL_ADDR_FILE)); \
	cast call $$ADDR "getAllItems()((bytes32,string,string,address,uint256,string,bytes32,string,bytes32,bool,uint256)[])" --rpc-url $(ANVIL_RPC_URL)

# Create a sample item. Set these vars when running:
# make create-item ITEM_ID=0x... SELLER=0x... PRICE_ATOMIC=1000000 DATASET_URL=... SIG_URL=... DATASET_HASH=0x... SIG_HASH=0x...
create-item:
	@ADDR=$$(cat $(ANVIL_ADDR_FILE)); \
	SELLER=$${SELLER:-$$(cast wallet address --private-key $(ANVIL_PRIVATE_KEY))}; \
	ITEM_ID=$${ITEM_ID:-0x0000000000000000000000000000000000000000000000000000000000000001}; \
	PRICE_ATOMIC=$${PRICE_ATOMIC:-1000000}; \
	TITLE=$${TITLE:-"Test Dataset"}; \
	DESC=$${DESC:-"Synthetic dataset for local testing"}; \
	DATASET_URL=$${DATASET_URL:-"ipfs://dataset"}; \
	SIG_URL=$${SIG_URL:-"ipfs://signature.json.gz"}; \
	DATASET_HASH=$${DATASET_HASH:-0x0000000000000000000000000000000000000000000000000000000000000000}; \
	SIG_HASH=$${SIG_HASH:-0x0000000000000000000000000000000000000000000000000000000000000000}; \
	echo "Creating item as owner..."; \
	cast send $$ADDR \
	  "createItem(bytes32,string,string,address,uint256,string,bytes32,string,bytes32)" \
	  $$ITEM_ID "$$TITLE" "$$DESC" $$SELLER $$PRICE_ATOMIC "$$DATASET_URL" $$DATASET_HASH "$$SIG_URL" $$SIG_HASH \
	  --rpc-url $(ANVIL_RPC_URL) --private-key $(ANVIL_PRIVATE_KEY)

# Mint mock USDC on Anvil for local testing.
# make mint-usdc TO=0x... AMOUNT=5000000
mint-usdc:
	@TOKEN=$$(cat $(ANVIL_USDC_ADDR_FILE)); \
	TO=$${TO:-$${ANVIL_USDC_RECIPIENT:-$$(cast wallet address --private-key $(ANVIL_PRIVATE_KEY))}}; \
	AMOUNT=$${AMOUNT:-5000000000}; \
	echo "Minting $$AMOUNT USDC atomic units to $$TO..."; \
	cast send $$TOKEN "mint(address,uint256)" $$TO $$AMOUNT \
	  --rpc-url $(ANVIL_RPC_URL) --private-key $(ANVIL_PRIVATE_KEY)

# Buy item by bytes32 ID. Calculates total price (price + fee) automatically and approves the marketplace.
# make buy-item BUYER_PK=0x... PRICE_ATOMIC=1000000 ITEM_ID=0x...
buy-item:
	@ADDR=$$(cat $(ANVIL_ADDR_FILE)); \
	TOKEN=$$(cat $(ANVIL_USDC_ADDR_FILE)); \
	PRICE_ATOMIC=$${PRICE_ATOMIC:-1000000}; \
	BUYER_PK=$${BUYER_PK:-$(ANVIL_PRIVATE_KEY)}; \
	ITEM_ID=$${ITEM_ID:-0x0000000000000000000000000000000000000000000000000000000000000001}; \
	echo "Reading feeBps from contract..."; \
	FEE_BPS=$$(cast call $$ADDR "feeBps()(uint256)" --rpc-url $(ANVIL_RPC_URL)); \
	FEE_BPS_DEC=$$(printf "%d" $$FEE_BPS); \
	echo "Price: $$PRICE_ATOMIC atomic units, Fee: $$FEE_BPS_DEC bps"; \
	FEE_AMOUNT=$$(echo "scale=0; $$PRICE_ATOMIC * $$FEE_BPS_DEC / 10000" | bc); \
	TOTAL_PRICE=$$(echo "$$PRICE_ATOMIC + $$FEE_AMOUNT" | bc); \
	echo "Fee amount: $$FEE_AMOUNT atomic units"; \
	echo "Total price to pay: $$TOTAL_PRICE atomic units"; \
	echo "Approving settlement token..."; \
	cast send $$TOKEN "approve(address,uint256)" $$ADDR $$TOTAL_PRICE \
	  --rpc-url $(ANVIL_RPC_URL) --private-key $$BUYER_PK > /dev/null; \
	echo "Buying item $$ITEM_ID..."; \
	cast send $$ADDR "buyItem(bytes32)" $$ITEM_ID \
	  --rpc-url $(ANVIL_RPC_URL) --private-key $$BUYER_PK

seed-anvil:
	@ADDR=$$(cat $(ANVIL_ADDR_FILE)); \
	echo "Seeding Marketplace at $$ADDR..."; \
	forge script script/SeedMarketplace.s.sol:SeedMarketplace \
	  --sig "run(address)" $$ADDR \
	  --rpc-url $(ANVIL_RPC_URL) \
	  --broadcast \
	  --private-key $(ANVIL_PRIVATE_KEY)
