// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Test} from "forge-std/Test.sol";
import {Marketplace} from "../src/Marketplace.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";

contract MarketplaceTest is Test {
    Marketplace public marketplace;

    address owner = address(0xA11CE);
    address feeRecipient = address(0xFEE);
    address seller = address(0xB0B);
    address buyer = address(0xCAFE);

    uint256 feeBps = 250; // 2.5%

    string constant TITLE = "Test Dataset";
    string constant DESC = "Synthetic dataset for testing";
    string constant DATASET_URL = "ipfs://dataset";
    bytes32 constant DATASET_HASH = bytes32(uint256(0x1111));
    string constant SIG_URL = "ipfs://signature.json.gz";
    bytes32 constant SIG_HASH = bytes32(uint256(0x2222));
    uint256 constant PRICE = 1 ether;

    uint256 private idCounter = 0;

    function setUp() public {
        marketplace = new Marketplace(owner, feeRecipient, feeBps);
        vm.deal(buyer, 100 ether);
    }

    function _walletId(address user) internal view returns (bytes32) {
        string memory chainStr = Strings.toString(block.chainid);
        string memory addrStr = Strings.toHexString(uint160(user), 20);
        return keccak256(abi.encodePacked("eip155:", chainStr, ":", addrStr));
    }

    function _createDefaultItem() internal returns (bytes32 itemId) {
        itemId = bytes32(idCounter);
        idCounter += 1;
        vm.prank(owner);
        marketplace.createItem(
            itemId, TITLE, DESC, seller, PRICE, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH
        );
    }

    function _buy(bytes32 itemId, address _buyer, uint256 value) internal {
        vm.prank(_buyer);
        marketplace.buyItem{value: value}(itemId);
    }

    function test_createItem_onlyOwner() public {
        vm.prank(address(123));
        vm.expectRevert();
        marketplace.createItem(
            bytes32(uint256(1)), TITLE, DESC, seller, PRICE, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH
        );
    }

    function test_createItem_storesView() public {
        bytes32 itemId = _createDefaultItem();
        Marketplace.DataItemView memory v = marketplace.getItemView(itemId);
        assertEq(v.itemId, itemId);
        assertEq(v.title, TITLE);
        assertEq(v.description, DESC);
        assertEq(v.seller, seller);
    }

    function test_getItems_pagination() public {
        for (uint256 i = 0; i < 3; i++) {
            _createDefaultItem();
        }
        Marketplace.DataItemView[] memory items = marketplace.getItems(1, 2);
        assertEq(items.length, 2);
        assertEq(items[0].itemId, bytes32(uint256(1)));
        assertEq(items[1].itemId, bytes32(uint256(2)));
    }

    function test_buyItem_setsAccess() public {
        bytes32 itemId = _createDefaultItem();
        uint256 fee = (PRICE * feeBps) / 10_000;
        uint256 totalPrice = PRICE + fee;
        _buy(itemId, buyer, totalPrice);
        assertTrue(marketplace.hasAccess(itemId, _walletId(buyer)));
    }

    function test_grantAccess_onlyOwner() public {
        bytes32 itemId = _createDefaultItem();
        vm.prank(owner);
        marketplace.grantAccess(itemId, bytes32(uint256(999)));
        assertTrue(marketplace.hasAccess(itemId, bytes32(uint256(999))));
    }
}
