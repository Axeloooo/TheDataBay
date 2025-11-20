// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Script} from "forge-std/Script.sol";
import {CifarMarketplace} from "../src/CifarMarketplace.sol";

contract DeployCifarMarketplace is Script {
    CifarMarketplace public marketplace;

    function setUp() public {}

    function run() public {
        vm.startBroadcast();

        marketplace = new CifarMarketplace();

        vm.stopBroadcast();
    }
}
