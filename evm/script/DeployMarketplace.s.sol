// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Script} from "forge-std/Script.sol";
import {Marketplace} from "../src/Marketplace.sol";

contract DeployMarketplace is Script {
    Marketplace public marketplace;

    function setUp() public {}

    function run() public {
        vm.startBroadcast();

        marketplace = new Marketplace();

        vm.stopBroadcast();
    }
}
