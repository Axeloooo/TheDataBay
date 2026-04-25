// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Script} from "forge-std/Script.sol";
import {HelperConfig} from "./HelperConfig.s.sol";
import {Marketplace} from "../src/Marketplace.sol";
import {MockUSDC} from "../src/MockUSDC.sol";

contract DeployMarketplace is Script {
    /**
     * @notice Marketplace instance
     */
    Marketplace public marketplace;
    MockUSDC public mockUsdc;

    /**
     * @notice Deploys the Marketplace contract using network-specific configuration
     */
    function run() public {
        HelperConfig config = new HelperConfig();

        (
            uint256 deployKey,
            address paymentToken,
            uint8 tokenDecimals,
            uint256 tokenMaxPrice,
            address feeRecipient,
            uint256 feeBps
        ) = config.activeNetworkConfig();

        vm.startBroadcast(deployKey);

        if (paymentToken == address(0)) {
            mockUsdc = new MockUSDC();
            paymentToken = address(mockUsdc);
            address mintRecipient = vm.envOr("ANVIL_USDC_RECIPIENT", vm.addr(deployKey));
            mockUsdc.mint(mintRecipient, 5_000_000 * 10 ** 6);
        }

        marketplace =
            new Marketplace(vm.addr(deployKey), paymentToken, tokenDecimals, tokenMaxPrice, feeRecipient, feeBps);

        vm.stopBroadcast();
    }
}
