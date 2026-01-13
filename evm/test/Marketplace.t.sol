// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Test} from "forge-std/Test.sol";
import {Marketplace} from "../src/Marketplace.sol";

contract MarketplaceTest is Test {
    Marketplace public marketplace;
    address owner = address(1);

    function setUp() public {
        marketplace = new Marketplace(owner);
    }
}
