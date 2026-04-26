// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Test} from "forge-std/Test.sol";
import {MockCADC} from "../src/MockCADC.sol";

contract MockCADCTest is Test {
    MockCADC public cadc;

    address recipient = address(0xCA);

    function setUp() public {
        cadc = new MockCADC();
    }

    function test_metadata_and_decimals() public view {
        assertEq(cadc.name(), "Mock CAD Coin");
        assertEq(cadc.symbol(), "CADC");
        assertEq(cadc.decimals(), 18);
    }

    function test_mint_increases_recipient_balance_and_total_supply(uint256 amount) public {
        cadc.mint(recipient, amount);

        assertEq(cadc.balanceOf(recipient), amount);
        assertEq(cadc.totalSupply(), amount);
    }
}
