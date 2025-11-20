// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

contract CifarNFT is ERC721, Ownable {
    constructor() ERC721("CifarNFT", "CIFAR") {}
}
