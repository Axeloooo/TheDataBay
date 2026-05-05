// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Test} from "forge-std/Test.sol";
import {MockUSDC} from "../src/MockUSDC.sol";

contract MockUSDCTest is Test {
    MockUSDC public usdc;

    address recipient = address(0xAB);

    function setUp() public {
        usdc = new MockUSDC();
    }

    function test_metadata_and_decimals() public view {
        assertEq(usdc.name(), "Mock USD Coin");
        assertEq(usdc.symbol(), "USDC");
        assertEq(usdc.decimals(), 6);
    }

    function test_mint_increases_recipient_balance_and_total_supply(uint256 amount) public {
        usdc.mint(recipient, amount);

        assertEq(usdc.balanceOf(recipient), amount);
        assertEq(usdc.totalSupply(), amount);
    }
}
