// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Test} from "forge-std/Test.sol";
import {HelperConfig} from "../script/HelperConfig.s.sol";

contract HelperConfigTest is Test {
    function test_anvil_config_uses_zero_addresses_for_deployable_mocks() public {
        HelperConfig config = new HelperConfig();
        HelperConfig.NetworkConfig memory networkConfig = config.getActiveNetworkConfig();

        assertEq(networkConfig.usdcToken, address(0));
        assertEq(networkConfig.usdcDecimals, config.DEFAULT_USDC_DECIMALS());
        assertEq(networkConfig.usdcMaxPrice, config.DEFAULT_USDC_MAX_PRICE());
        assertEq(networkConfig.cadcToken, address(0));
        assertEq(networkConfig.cadcDecimals, config.DEFAULT_CADC_DECIMALS());
        assertEq(networkConfig.cadcMaxPrice, config.DEFAULT_CADC_MAX_PRICE());
    }

    function test_sepolia_config_allows_zero_addresses_for_mock_deployments() public {
        vm.chainId(11155111);
        vm.setEnv("SEPOLIA_PRIVATE_KEY", vm.toString(uint256(1)));
        vm.setEnv("SEPOLIA_USDC_ADDRESS", "0x0000000000000000000000000000000000000000");
        vm.setEnv("SEPOLIA_CADC_ADDRESS", "0x0000000000000000000000000000000000000000");

        HelperConfig config = new HelperConfig();
        HelperConfig.NetworkConfig memory networkConfig = config.getActiveNetworkConfig();

        assertEq(networkConfig.usdcToken, address(0));
        assertEq(networkConfig.usdcDecimals, config.DEFAULT_USDC_DECIMALS());
        assertEq(networkConfig.usdcMaxPrice, config.DEFAULT_USDC_MAX_PRICE());
        assertEq(networkConfig.cadcToken, address(0));
        assertEq(networkConfig.cadcDecimals, config.DEFAULT_CADC_DECIMALS());
        assertEq(networkConfig.cadcMaxPrice, config.DEFAULT_CADC_MAX_PRICE());
    }

    function test_base_sepolia_config_allows_zero_addresses_for_mock_deployments() public {
        vm.chainId(84532);
        vm.setEnv("BASE_SEPOLIA_PRIVATE_KEY", vm.toString(uint256(1)));
        vm.setEnv("BASE_SEPOLIA_USDC_ADDRESS", "0x0000000000000000000000000000000000000000");
        vm.setEnv("BASE_SEPOLIA_CADC_ADDRESS", "0x0000000000000000000000000000000000000000");

        HelperConfig config = new HelperConfig();
        HelperConfig.NetworkConfig memory networkConfig = config.getActiveNetworkConfig();

        assertEq(networkConfig.usdcToken, address(0));
        assertEq(networkConfig.usdcDecimals, config.DEFAULT_USDC_DECIMALS());
        assertEq(networkConfig.cadcMaxPrice, config.DEFAULT_CADC_MAX_PRICE());
        assertEq(networkConfig.cadcToken, address(0));
        assertEq(networkConfig.cadcDecimals, config.DEFAULT_CADC_DECIMALS());
        assertEq(networkConfig.feeBps, uint256(250));
    }
}
