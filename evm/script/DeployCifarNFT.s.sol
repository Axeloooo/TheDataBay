// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Script} from "forge-std/Script.sol";
import {CifarNFT} from "../src/CifarNFT.sol";

contract DeployCifarNFT is Script {
    CifarNFT public nft;

    function setUp() public {}

    function run() public {
        vm.startBroadcast();

        nft = new CifarNFT();

        vm.stopBroadcast();
    }
}
