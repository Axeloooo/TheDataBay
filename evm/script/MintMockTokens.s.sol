// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";
import {MockUSDC} from "../src/MockUSDC.sol";
import {MockCADC} from "../src/MockCADC.sol";

/// @notice Mints MockUSDC and/or MockCADC to a recipient address.
///
/// Required env vars:
///   PRIVATE_KEY       — broadcaster private key (set by Makefile per network)
///   MINT_RECIPIENT    — address that receives the tokens
///
/// Optional env vars (skip token if address is zero or amount is zero):
///   USDC_ADDRESS      — deployed MockUSDC contract address (default: address(0))
///   CADC_ADDRESS      — deployed MockCADC contract address (default: address(0))
///   MINT_USDC_AMOUNT  — atomic units to mint (default: 10_000 * 10^6)
///   MINT_CADC_AMOUNT  — atomic units to mint (default: 10_000 * 10^18)
contract MintMockTokens is Script {
    function run() external {
        uint256 privateKey = vm.envUint("PRIVATE_KEY");
        address recipient = vm.envAddress("MINT_RECIPIENT");
        address usdcAddress = vm.envOr("USDC_ADDRESS", address(0));
        address cadcAddress = vm.envOr("CADC_ADDRESS", address(0));
        uint256 usdcAmount = vm.envOr("MINT_USDC_AMOUNT", uint256(10_000 * 10 ** 6));
        uint256 cadcAmount = vm.envOr("MINT_CADC_AMOUNT", uint256(10_000 * 10 ** 18));

        vm.startBroadcast(privateKey);
        _mintTokens(recipient, usdcAddress, cadcAddress, usdcAmount, cadcAmount);
        vm.stopBroadcast();
    }

    function _mintTokens(
        address recipient,
        address usdcAddress,
        address cadcAddress,
        uint256 usdcAmount,
        uint256 cadcAmount
    ) public {
        if (usdcAddress != address(0) && usdcAmount > 0) {
            MockUSDC(usdcAddress).mint(recipient, usdcAmount);
            console2.log("Minted USDC atomic units to recipient:", usdcAmount);
        }
        if (cadcAddress != address(0) && cadcAmount > 0) {
            MockCADC(cadcAddress).mint(recipient, cadcAmount);
            console2.log("Minted CADC atomic units to recipient:", cadcAmount);
        }
    }
}
