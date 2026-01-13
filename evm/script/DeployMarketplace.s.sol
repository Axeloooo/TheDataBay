// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Script} from "forge-std/Script.sol";
import {Marketplace} from "../src/Marketplace.sol";

contract DeployMarketplace is Script {
    uint256 public constant DEFAULT_ANVIL_KEY = 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80;

    Marketplace public marketplace;

    function setUp() public {}

    function run() public {
        vm.startBroadcast();

        marketplace = new Marketplace(vm.addr(DEFAULT_ANVIL_KEY));

        vm.stopBroadcast();
    }
}
