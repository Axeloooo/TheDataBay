// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MockCADC is ERC20 {
    constructor() ERC20("Mock CAD Coin", "CADC") {}

    function decimals() public pure override returns (uint8) {
        return 18;
    }

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}
