// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";
import {HelperConfig} from "./HelperConfig.s.sol";
import {Marketplace} from "../src/Marketplace.sol";
import {MockCADC} from "../src/MockCADC.sol";
import {MockUSDC} from "../src/MockUSDC.sol";

contract DeployMarketplace is Script {
    /**
     * @notice Marketplace instance
     */
    Marketplace public marketplace;
    MockUSDC public mockUsdc;
    MockCADC public mockCadc;

    /**
     * @notice Deploys the Marketplace contract using network-specific configuration
     */
    function run() public {
        HelperConfig config = new HelperConfig();
        HelperConfig.NetworkConfig memory networkConfig = config.getActiveNetworkConfig();

        vm.startBroadcast(networkConfig.deployKey);

        if (networkConfig.usdcToken == address(0)) {
            mockUsdc = new MockUSDC();
            networkConfig.usdcToken = address(mockUsdc);
            address mintRecipient = vm.envOr("ANVIL_USDC_RECIPIENT", vm.addr(networkConfig.deployKey));
            mockUsdc.mint(mintRecipient, 5_000_000 * 10 ** networkConfig.usdcDecimals);
        }

        if (networkConfig.cadcToken == address(0)) {
            mockCadc = new MockCADC();
            networkConfig.cadcToken = address(mockCadc);
            address mintRecipient = vm.envOr("ANVIL_CADC_RECIPIENT", vm.addr(networkConfig.deployKey));
            mockCadc.mint(mintRecipient, 5_000_000 * 10 ** networkConfig.cadcDecimals);
        }

        marketplace = new Marketplace(
            vm.addr(networkConfig.deployKey),
            networkConfig.usdcToken,
            networkConfig.usdcDecimals,
            networkConfig.usdcMaxPrice,
            networkConfig.feeRecipient,
            networkConfig.feeBps
        );
        marketplace.addAcceptedToken(networkConfig.cadcToken, networkConfig.cadcDecimals, networkConfig.cadcMaxPrice);

        _logAcceptedTokens();

        vm.stopBroadcast();
    }

    function _logAcceptedTokens() internal view {
        address[] memory tokens = marketplace.getAcceptedTokens();
        console2.log("Accepted token count:", tokens.length);

        for (uint256 i; i < tokens.length; ++i) {
            (bool enabled, uint8 decimals, uint256 maxPrice) = marketplace.acceptedTokens(tokens[i]);
            console2.log("Accepted token index:", i);
            console2.log("Token:", tokens[i]);
            console2.log("Enabled:", enabled);
            console2.log("Decimals:", decimals);
            console2.log("Max price:", maxPrice);
        }
    }
}
