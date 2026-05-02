// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Script} from "forge-std/Script.sol";

contract HelperConfig is Script {
    /**
     * @notice Network configuration struct
     */
    struct NetworkConfig {
        uint256 deployKey;
        address usdcToken;
        uint8 usdcDecimals;
        uint256 usdcMaxPrice;
        address cadcToken;
        uint8 cadcDecimals;
        uint256 cadcMaxPrice;
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
    uint8 public constant DEFAULT_CADC_DECIMALS = 18;
    uint256 public constant DEFAULT_CADC_MAX_PRICE = 1_000_000 * 10 ** 18;

    /**
     * @notice Active network configuration
     */
    NetworkConfig public activeNetworkConfig;

    /**
     * @dev Sets the active network configuration based on the chain ID.
     *
     * Base Sepolia (84532): Reads from BASE_SEPOLIA_* environment variables.
     * Sepolia (11155111): Reads from SEPOLIA_* environment variables.
     * Anvil (default): Uses default values.
     */
    constructor() {
        if (block.chainid == 84532) {
            activeNetworkConfig = getBaseSepoliaConfig();
        } else if (block.chainid == 11155111) {
            activeNetworkConfig = getSepoliaEthConfig();
        } else {
            activeNetworkConfig = getOrCreateAnvilEthConfig();
        }
    }

    /**
     * @dev Returns the Base Sepolia network configuration.
     */
    function getBaseSepoliaConfig() public view returns (NetworkConfig memory) {
        uint256 pk = vm.envUint("BASE_SEPOLIA_PRIVATE_KEY");
        address deployer = vm.addr(pk);

        return NetworkConfig({
            deployKey: pk,
            usdcToken: vm.envOr("BASE_SEPOLIA_USDC_ADDRESS", address(0)),
            usdcDecimals: uint8(vm.envOr("BASE_SEPOLIA_USDC_DECIMALS", uint256(DEFAULT_USDC_DECIMALS))),
            usdcMaxPrice: vm.envOr("BASE_SEPOLIA_USDC_MAX_PRICE", DEFAULT_USDC_MAX_PRICE),
            cadcToken: vm.envOr("BASE_SEPOLIA_CADC_ADDRESS", address(0)),
            cadcDecimals: uint8(vm.envOr("BASE_SEPOLIA_CADC_DECIMALS", uint256(DEFAULT_CADC_DECIMALS))),
            cadcMaxPrice: vm.envOr("BASE_SEPOLIA_CADC_MAX_PRICE", DEFAULT_CADC_MAX_PRICE),
            feeRecipient: vm.envOr("BASE_SEPOLIA_FEE_RECIPIENT", deployer),
            feeBps: vm.envOr("BASE_SEPOLIA_FEE_BPS", uint256(250))
        });
    }

    /**
     * @dev Returns the Sepolia network configuration.
     */
    function getSepoliaEthConfig() public view returns (NetworkConfig memory) {
        uint256 pk = vm.envUint("SEPOLIA_PRIVATE_KEY");
        address deployer = vm.addr(pk);

        return NetworkConfig({
            deployKey: pk,
            usdcToken: vm.envOr("SEPOLIA_USDC_ADDRESS", address(0)),
            usdcDecimals: uint8(vm.envOr("SEPOLIA_USDC_DECIMALS", uint256(DEFAULT_USDC_DECIMALS))),
            usdcMaxPrice: vm.envOr("SEPOLIA_USDC_MAX_PRICE", DEFAULT_USDC_MAX_PRICE),
            cadcToken: vm.envOr("SEPOLIA_CADC_ADDRESS", address(0)),
            cadcDecimals: uint8(vm.envOr("SEPOLIA_CADC_DECIMALS", uint256(DEFAULT_CADC_DECIMALS))),
            cadcMaxPrice: vm.envOr("SEPOLIA_CADC_MAX_PRICE", DEFAULT_CADC_MAX_PRICE),
            feeRecipient: vm.envOr("SEPOLIA_FEE_RECIPIENT", deployer),
            feeBps: vm.envOr("SEPOLIA_FEE_BPS", uint256(250))
        });
    }

    /**
     * @dev Returns the active network configuration as a struct for scripts and tests.
     */
    function getActiveNetworkConfig() public view returns (NetworkConfig memory) {
        return activeNetworkConfig;
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
            usdcToken: address(0),
            usdcDecimals: DEFAULT_USDC_DECIMALS,
            usdcMaxPrice: DEFAULT_USDC_MAX_PRICE,
            cadcToken: address(0),
            cadcDecimals: DEFAULT_CADC_DECIMALS,
            cadcMaxPrice: DEFAULT_CADC_MAX_PRICE,
            feeRecipient: defaultFeeRecipient,
            feeBps: DEFAULT_FEE_BPS
        });
    }
}
