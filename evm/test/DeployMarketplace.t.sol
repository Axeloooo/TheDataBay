// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {Test} from "forge-std/Test.sol";
import {DeployMarketplace} from "../script/DeployMarketplace.s.sol";
import {HelperConfig} from "../script/HelperConfig.s.sol";
import {Marketplace} from "../src/Marketplace.sol";

contract DeployMarketplaceTest is Test {
    function test_run_deploys_anvil_mocks_and_registers_usdc_then_cadc() public {
        DeployMarketplace deployScript = new DeployMarketplace();
        HelperConfig config = new HelperConfig();
        uint256 deployKey = config.DEFAULT_ANVIL_KEY();
        address deployer = vm.addr(deployKey);
        address usdcRecipient = address(0xA11CE);
        address cadcRecipient = address(0xB0B);

        vm.setEnv("ANVIL_USDC_RECIPIENT", vm.toString(usdcRecipient));
        vm.setEnv("ANVIL_CADC_RECIPIENT", vm.toString(cadcRecipient));

        deployScript.run();

        Marketplace marketplace = deployScript.marketplace();
        address usdc = address(deployScript.mockUsdc());
        address cadc = address(deployScript.mockCadc());

        assertEq(marketplace.owner(), deployer);
        assertEq(marketplace.acceptedTokenCount(), 2);
        assertEq(marketplace.acceptedTokenAt(0), usdc);
        assertEq(marketplace.acceptedTokenAt(1), cadc);

        (bool usdcEnabled, uint8 usdcDecimals, uint256 usdcMaxPrice) = marketplace.acceptedTokens(usdc);
        assertTrue(usdcEnabled);
        assertEq(usdcDecimals, config.DEFAULT_USDC_DECIMALS());
        assertEq(usdcMaxPrice, config.DEFAULT_USDC_MAX_PRICE());

        (bool cadcEnabled, uint8 cadcDecimals, uint256 cadcMaxPrice) = marketplace.acceptedTokens(cadc);
        assertTrue(cadcEnabled);
        assertEq(cadcDecimals, config.DEFAULT_CADC_DECIMALS());
        assertEq(cadcMaxPrice, config.DEFAULT_CADC_MAX_PRICE());

        assertEq(IERC20(usdc).balanceOf(usdcRecipient), 5_000_000 * 10 ** config.DEFAULT_USDC_DECIMALS());
        assertEq(IERC20(cadc).balanceOf(cadcRecipient), 5_000_000 * 10 ** config.DEFAULT_CADC_DECIMALS());
    }
}
