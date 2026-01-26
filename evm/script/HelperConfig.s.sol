// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Script} from "forge-std/Script.sol";

contract HelperConfig is Script {
    /**
     * @notice Network configuration struct
     */
    struct NetworkConfig {
        uint256 deployKey;
        address feeRecipient;
        uint256 feeBps;
    }

    /**
     * @notice Default values for Anvil local network
     */
    uint256 public constant DEFAULT_ANVIL_KEY = 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80;
    uint256 public constant DEFAULT_FEE_BPS = 0;

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
        uint256 pk = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(pk);

        address feeR = vm.envOr("FEE_RECIPIENT", deployer);
        uint256 feeBps = vm.envOr("FEE_BPS", uint256(250));

        return NetworkConfig({deployKey: pk, feeRecipient: feeR, feeBps: feeBps});
    }

    /**
     * @dev Returns the Anvil network configuration.
     */
    function getOrCreateAnvilEthConfig() public view returns (NetworkConfig memory) {
        if (activeNetworkConfig.deployKey != 0) {
            return activeNetworkConfig;
        }

        address DEFAULT_FEE_RECIPIENT = vm.addr(DEFAULT_ANVIL_KEY);

        return
            NetworkConfig({deployKey: DEFAULT_ANVIL_KEY, feeRecipient: DEFAULT_FEE_RECIPIENT, feeBps: DEFAULT_FEE_BPS});
    }
}
