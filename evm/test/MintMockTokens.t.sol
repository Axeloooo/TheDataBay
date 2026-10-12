// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Test} from "forge-std/Test.sol";
import {MintMockTokens} from "../script/MintMockTokens.s.sol";
import {MockUSDC} from "../src/MockUSDC.sol";
import {MockCADC} from "../src/MockCADC.sol";

contract MintMockTokensTest is Test {
    MintMockTokens public minter;
    MockUSDC public usdc;
    MockCADC public cadc;

    address recipient = address(0xBEEF);

    function setUp() public {
        minter = new MintMockTokens();
        usdc = new MockUSDC();
        cadc = new MockCADC();
    }

    function test_mints_usdc_only_when_cadc_address_is_zero() public {
        minter._mintTokens(recipient, address(usdc), address(0), 1_000 * 10 ** 6, 0);

        assertEq(usdc.balanceOf(recipient), 1_000 * 10 ** 6);
        assertEq(cadc.balanceOf(recipient), 0);
    }

    function test_mints_cadc_only_when_usdc_address_is_zero() public {
        minter._mintTokens(recipient, address(0), address(cadc), 0, 1_000 * 10 ** 18);

        assertEq(usdc.balanceOf(recipient), 0);
        assertEq(cadc.balanceOf(recipient), 1_000 * 10 ** 18);
    }

    function test_mints_both_tokens() public {
        minter._mintTokens(recipient, address(usdc), address(cadc), 500 * 10 ** 6, 500 * 10 ** 18);

        assertEq(usdc.balanceOf(recipient), 500 * 10 ** 6);
        assertEq(cadc.balanceOf(recipient), 500 * 10 ** 18);
    }

    function test_skips_both_tokens_when_amounts_are_zero() public {
        minter._mintTokens(recipient, address(usdc), address(cadc), 0, 0);

        assertEq(usdc.balanceOf(recipient), 0);
        assertEq(cadc.balanceOf(recipient), 0);
    }
}
