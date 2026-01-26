// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Script} from "forge-std/Script.sol";
import {HelperConfig} from "./HelperConfig.s.sol";
import {Marketplace} from "../src/Marketplace.sol";

contract DeployMarketplace is Script {
    /**
     * @notice Marketplace instance
     */
    Marketplace public marketplace;

    /**
     * @notice Deploys the Marketplace contract using network-specific configuration
     */
    function run() public {
        HelperConfig config = new HelperConfig();

        (uint256 deployKey, address feeRecipient, uint256 feeBps) = config.activeNetworkConfig();

        vm.startBroadcast(deployKey);

        marketplace = new Marketplace(vm.addr(deployKey), feeRecipient, feeBps);

        vm.stopBroadcast();
    }
}
