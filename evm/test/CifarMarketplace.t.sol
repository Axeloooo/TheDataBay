// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Test} from "forge-std/Test.sol";
import {CifarMarketplace} from "../src/CifarMarketplace.sol";

contract CifarMarketplaceTest is Test {
    CifarMarketplace public marketplace;

    function setUp() public {
        marketplace = new CifarMarketplace();
    }
}
