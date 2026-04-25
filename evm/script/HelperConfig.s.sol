// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Script} from "forge-std/Script.sol";

contract HelperConfig is Script {
    /**
     * @notice Network configuration struct
     */
    struct NetworkConfig {
        uint256 deployKey;
        address paymentToken;
        uint8 tokenDecimals;
        uint256 tokenMaxPrice;
        address feeRecipient;
        uint256 feeBps;
    }

    /**
     * @notice Default values for Anvil local network
     */
    uint256 public constant DEFAULT_ANVIL_KEY = 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80;
    uint256 public constant DEFAULT_FEE_BPS = 0;
    uint8 public constant DEFAULT_USDC_DECIMALS = 6;
    uint256 public constant DEFAULT_USDC_MAX_PRICE = 1_000_000 * 10 ** 6;

    /**
     * @notice Active network configuration
     */
    NetworkConfig public activeNetworkConfig;

    /**
     * @dev Sets the active network configuration based on the chain ID.
     *
     * Sepolia: Reads from environment variables.
     * Anvil (default): Uses default values.
     */
    constructor() {
        if (block.chainid == 11155111) {
            activeNetworkConfig = getSepoliaEthConfig();
        } else {
            activeNetworkConfig = getOrCreateAnvilEthConfig();
        }
    }

    /**
     * @dev Returns the Sepolia network configuration.
     */
    function getSepoliaEthConfig() public view returns (NetworkConfig memory) {
        uint256 pk = vm.envUint("SEPOLIA_PRIVATE_KEY");
        address deployer = vm.addr(pk);

        address paymentToken = vm.envAddress("SEPOLIA_USDC_ADDRESS");
        uint8 tokenDecimals = uint8(vm.envOr("SEPOLIA_USDC_DECIMALS", uint256(DEFAULT_USDC_DECIMALS)));
        uint256 tokenMaxPrice = vm.envOr("SEPOLIA_USDC_MAX_PRICE", DEFAULT_USDC_MAX_PRICE);
        address feeR = vm.envOr("SEPOLIA_FEE_RECIPIENT", deployer);
        uint256 feeBps = vm.envOr("SEPOLIA_FEE_BPS", uint256(250));
        return NetworkConfig({
            deployKey: pk,
            paymentToken: paymentToken,
            tokenDecimals: tokenDecimals,
            tokenMaxPrice: tokenMaxPrice,
            feeRecipient: feeR,
            feeBps: feeBps
        });
    }

    /**
     * @dev Returns the Anvil network configuration.
     */
    function getOrCreateAnvilEthConfig() public view returns (NetworkConfig memory) {
        if (activeNetworkConfig.deployKey != 0) {
            return activeNetworkConfig;
        }

        address defaultFeeRecipient = vm.addr(DEFAULT_ANVIL_KEY);

        return NetworkConfig({
            deployKey: DEFAULT_ANVIL_KEY,
            paymentToken: address(0),
            tokenDecimals: DEFAULT_USDC_DECIMALS,
            tokenMaxPrice: DEFAULT_USDC_MAX_PRICE,
            feeRecipient: defaultFeeRecipient,
            feeBps: DEFAULT_FEE_BPS
        });
    }
}
