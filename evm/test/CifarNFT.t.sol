// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Test} from "forge-std/Test.sol";
import {CifarNFT} from "../src/CifarNFT.sol";

contract CifarNFTTest is Test {
    CifarNFT public nft;

    function setUp() public {
        nft = new CifarNFT();
    }
}
