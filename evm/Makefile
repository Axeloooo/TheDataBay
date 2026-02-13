# Makefile for local Anvil deployment/testing
# Requires: foundry (forge, cast), and a .env file

SHELL := /bin/bash

-include .env

DEPLOY_SCRIPT := script/DeployMarketplace.s.sol:DeployMarketplace
DEPLOYMENTS_DIR := deployments
ANVIL_ADDR_FILE := $(DEPLOYMENTS_DIR)/anvil_marketplace.addr

.PHONY: help anvil stop-anvil clean deploy-anvil addr fee getall create-item buy-item seed-anvil

help:
	@echo "Targets:"
	@echo "  anvil         - start anvil (port 8545)"
	@echo "  deploy-anvil  - deploy Marketplace to anvil and save address"
	@echo "  addr          - print deployed Marketplace address"
	@echo "  fee           - call fee config getters"
	@echo "  getall        - call getAllItems()"
	@echo "  seed-anvil    - seed deterministic sample items for UI testing"
	@echo "  create-item   - create a sample item"
	@echo "  buy-item      - buy itemId=0 with msg.value=PRICE_WEI"
	@echo ""
	@echo "Env in .env:"
	@echo "  ANVIL_RPC_URL, ANVIL_PRIVATE_KEY, ANVIL_FEE_RECIPIENT, ANVIL_FEE_BPS"

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
	@echo "Extracting deployed address..."
	@ADDR=$$(grep -o '"contractAddress": *"0x[^"]*"' broadcast/DeployMarketplace.s.sol/31337/run-latest.json | head -n 1 | sed 's/.*"0x/0x/' | sed 's/".*//'); \
	if [ -z "$$ADDR" ]; then \
		echo "ERROR: Could not extract deployed address from broadcast JSON"; \
		exit 1; \
	fi; \
	echo $$ADDR > $(ANVIL_ADDR_FILE); \
	echo "Saved address to $(ANVIL_ADDR_FILE): $$ADDR"

addr:
	@if [ -f "$(ANVIL_ADDR_FILE)" ]; then cat $(ANVIL_ADDR_FILE); else echo "No address file. Run: make deploy-anvil"; fi

fee:
	@ADDR=$$(cat $(ANVIL_ADDR_FILE)); \
	echo "feeBps:"; cast call $$ADDR "feeBps()(uint256)" --rpc-url $(ANVIL_RPC_URL); \
	echo "feeRecipient:"; cast call $$ADDR "feeRecipient()(address)" --rpc-url $(ANVIL_RPC_URL)

getall:
	@ADDR=$$(cat $(ANVIL_ADDR_FILE)); \
	cast call $$ADDR "getAllItems()((bytes32,string,string,address,uint256,string,bytes32,string,bytes32,bool,uint256)[])" --rpc-url $(ANVIL_RPC_URL)

# Create a sample item. Set these vars when running:
# make create-item ITEM_ID=0x... SELLER=0x... PRICE_WEI=10000000000000000 DATASET_URL=... SIG_URL=... DATASET_HASH=0x... SIG_HASH=0x...
create-item:
	@ADDR=$$(cat $(ANVIL_ADDR_FILE)); \
	SELLER=$${SELLER:-$$(cast wallet address --private-key $(ANVIL_PRIVATE_KEY))}; \
	ITEM_ID=$${ITEM_ID:-0x0000000000000000000000000000000000000000000000000000000000000001}; \
	PRICE_WEI=$${PRICE_WEI:-10000000000000000}; \
	TITLE=$${TITLE:-"Test Dataset"}; \
	DESC=$${DESC:-"Synthetic dataset for local testing"}; \
	DATASET_URL=$${DATASET_URL:-"ipfs://dataset"}; \
	SIG_URL=$${SIG_URL:-"ipfs://signature.json.gz"}; \
	DATASET_HASH=$${DATASET_HASH:-0x0000000000000000000000000000000000000000000000000000000000000000}; \
	SIG_HASH=$${SIG_HASH:-0x0000000000000000000000000000000000000000000000000000000000000000}; \
	echo "Creating item as owner..."; \
	cast send $$ADDR \
	  "createItem(bytes32,string,string,address,uint256,string,bytes32,string,bytes32)" \
	  $$ITEM_ID "$$TITLE" "$$DESC" $$SELLER $$PRICE_WEI "$$DATASET_URL" $$DATASET_HASH "$$SIG_URL" $$SIG_HASH \
	  --rpc-url $(ANVIL_RPC_URL) --private-key $(ANVIL_PRIVATE_KEY)

# Buy item by bytes32 ID. Calculates total price (price + fee) automatically.
# make buy-item BUYER_PK=0x... PRICE_WEI=... ITEM_ID=0x...
buy-item:
	@ADDR=$$(cat $(ANVIL_ADDR_FILE)); \
	PRICE_WEI=$${PRICE_WEI:-10000000000000000}; \
	BUYER_PK=$${BUYER_PK:-$(ANVIL_PRIVATE_KEY)}; \
	ITEM_ID=$${ITEM_ID:-0x0000000000000000000000000000000000000000000000000000000000000001}; \
	echo "Reading feeBps from contract..."; \
	FEE_BPS=$$(cast call $$ADDR "feeBps()(uint256)" --rpc-url $(ANVIL_RPC_URL)); \
	FEE_BPS_DEC=$$(printf "%d" $$FEE_BPS); \
	echo "Price: $$PRICE_WEI wei, Fee: $$FEE_BPS_DEC bps"; \
	FEE_AMOUNT=$$(echo "scale=0; $$PRICE_WEI * $$FEE_BPS_DEC / 10000" | bc); \
	TOTAL_PRICE=$$(echo "$$PRICE_WEI + $$FEE_AMOUNT" | bc); \
	echo "Fee amount: $$FEE_AMOUNT wei"; \
	echo "Total price to pay: $$TOTAL_PRICE wei"; \
	echo "Buying item $$ITEM_ID..."; \
	cast send $$ADDR "buyItem(bytes32)" $$ITEM_ID \
	  --rpc-url $(ANVIL_RPC_URL) --private-key $$BUYER_PK --value $$TOTAL_PRICE

seed-anvil:
	@ADDR=$$(cat $(ANVIL_ADDR_FILE)); \
	echo "Seeding Marketplace at $$ADDR..."; \
	forge script script/SeedMarketplace.s.sol:SeedMarketplace \
	  --sig "run(address)" $$ADDR \
	  --rpc-url $(ANVIL_RPC_URL) \
	  --broadcast \
	  --private-key $(ANVIL_PRIVATE_KEY)
