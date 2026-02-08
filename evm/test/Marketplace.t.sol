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
        vm.prank(seller);
        marketplace.createItem(itemId, TITLE, DESC, seller, PRICE, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH);
    }

    function _buy(bytes32 itemId, address _buyer, uint256 value) internal {
        vm.prank(_buyer);
        marketplace.buyItem{value: value}(itemId);
    }

    function test_createItem_requires_seller() public {
        vm.prank(address(123));
        vm.expectRevert(Marketplace.Marketplace__SellerRequired.selector);
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

    function test_createItem_rejects_empty_fields() public {
        bytes32 itemId = bytes32(uint256(1));
        vm.prank(seller);
        vm.expectRevert(Marketplace.Marketplace__TitleRequired.selector);
        marketplace.createItem(itemId, "", DESC, seller, PRICE, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH);

        vm.prank(seller);
        vm.expectRevert(Marketplace.Marketplace__DescriptionRequired.selector);
        marketplace.createItem(itemId, TITLE, "", seller, PRICE, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH);

        vm.prank(seller);
        vm.expectRevert(Marketplace.Marketplace__DatasetUrlRequired.selector);
        marketplace.createItem(itemId, TITLE, DESC, seller, PRICE, "", DATASET_HASH, SIG_URL, SIG_HASH);

        vm.prank(seller);
        vm.expectRevert(Marketplace.Marketplace__SignatureUrlRequired.selector);
        marketplace.createItem(itemId, TITLE, DESC, seller, PRICE, DATASET_URL, DATASET_HASH, "", SIG_HASH);
    }

    function test_createItem_rejects_invalid_price() public {
        bytes32 itemId = bytes32(uint256(1));
        vm.prank(seller);
        vm.expectRevert(Marketplace.Marketplace__PriceMustBeGreaterThanZero.selector);
        marketplace.createItem(itemId, TITLE, DESC, seller, 0, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH);

        uint256 maxPrice = marketplace.MAX_PRICE();
        vm.prank(seller);
        vm.expectRevert(
            abi.encodeWithSelector(Marketplace.Marketplace__PriceExceedsMaximum.selector, maxPrice + 1, maxPrice)
        );
        marketplace.createItem(itemId, TITLE, DESC, seller, maxPrice + 1, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH);
    }

    function test_createItem_rejects_duplicate() public {
        bytes32 itemId = _createDefaultItem();
        vm.prank(seller);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__ItemAlreadyExists.selector, itemId));
        marketplace.createItem(itemId, TITLE, DESC, seller, PRICE, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH);
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

    function test_getItems_out_of_range_returns_empty() public {
        _createDefaultItem();
        Marketplace.DataItemView[] memory items = marketplace.getItems(5, 2);
        assertEq(items.length, 0);
    }

    function test_getAllItems_empty() public view {
        Marketplace.DataItemView[] memory items = marketplace.getAllItems();
        assertEq(items.length, 0);
    }

    function test_getAllItems_returns_all() public {
        for (uint256 i = 0; i < 3; i++) {
            _createDefaultItem();
        }
        Marketplace.DataItemView[] memory items = marketplace.getAllItems();
        assertEq(items.length, 3);
        assertEq(items[0].itemId, bytes32(uint256(0)));
        assertEq(items[2].itemId, bytes32(uint256(2)));
    }

    function test_buyItem_setsAccess() public {
        bytes32 itemId = _createDefaultItem();
        uint256 fee = (PRICE * feeBps) / 10_000;
        uint256 totalPrice = PRICE + fee;
        _buy(itemId, buyer, totalPrice);
        assertTrue(marketplace.hasAccess(itemId, _walletId(buyer)));
    }

    function test_buyItem_reverts_for_missing_item() public {
        vm.prank(buyer);
        vm.expectRevert(
            abi.encodeWithSelector(Marketplace.Marketplace__ItemDoesNotExist.selector, bytes32(uint256(999)))
        );
        marketplace.buyItem{value: 1}(bytes32(uint256(999)));
    }

    function test_buyItem_rejects_underpayment() public {
        bytes32 itemId = _createDefaultItem();
        uint256 fee = (PRICE * feeBps) / 10_000;
        uint256 totalPrice = PRICE + fee;
        vm.prank(buyer);
        vm.expectRevert(
            abi.encodeWithSelector(Marketplace.Marketplace__InvalidPayment.selector, totalPrice, totalPrice - 1)
        );
        marketplace.buyItem{value: totalPrice - 1}(itemId);
    }

    function test_buyItem_rejects_overpayment() public {
        bytes32 itemId = _createDefaultItem();
        uint256 fee = (PRICE * feeBps) / 10_000;
        uint256 totalPrice = PRICE + fee;
        vm.prank(buyer);
        vm.expectRevert(
            abi.encodeWithSelector(Marketplace.Marketplace__InvalidPayment.selector, totalPrice, totalPrice + 1)
        );
        marketplace.buyItem{value: totalPrice + 1}(itemId);
    }

    function test_buyItem_prevents_double_purchase() public {
        bytes32 itemId = _createDefaultItem();
        uint256 fee = (PRICE * feeBps) / 10_000;
        uint256 totalPrice = PRICE + fee;
        _buy(itemId, buyer, totalPrice);
        vm.prank(buyer);
        vm.expectRevert(
            abi.encodeWithSelector(Marketplace.Marketplace__AlreadyHasAccess.selector, _walletId(buyer), itemId)
        );
        marketplace.buyItem{value: totalPrice}(itemId);
    }

    function test_buyItem_transfers_funds() public {
        bytes32 itemId = _createDefaultItem();
        uint256 fee = (PRICE * feeBps) / 10_000;
        uint256 totalPrice = PRICE + fee;
        uint256 sellerBalanceBefore = seller.balance;
        uint256 feeBalanceBefore = feeRecipient.balance;

        _buy(itemId, buyer, totalPrice);

        assertEq(seller.balance, sellerBalanceBefore + PRICE);
        assertEq(feeRecipient.balance, feeBalanceBefore + fee);
    }

    function test_updateDatasetUrl_onlySeller_and_notFrozen() public {
        bytes32 itemId = _createDefaultItem();
        vm.prank(address(123));
        vm.expectRevert(Marketplace.Marketplace__SellerRequired.selector);
        marketplace.updateDatasetUrl(itemId, "ipfs://new");

        vm.prank(seller);
        vm.expectRevert(Marketplace.Marketplace__DatasetUrlRequired.selector);
        marketplace.updateDatasetUrl(itemId, "");

        uint256 fee = (PRICE * feeBps) / 10_000;
        _buy(itemId, buyer, PRICE + fee);

        vm.prank(seller);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__ItemFrozen.selector, itemId));
        marketplace.updateDatasetUrl(itemId, "ipfs://new");
    }

    function test_updateSignature_onlySeller_and_notFrozen() public {
        bytes32 itemId = _createDefaultItem();
        vm.prank(address(123));
        vm.expectRevert(Marketplace.Marketplace__SellerRequired.selector);
        marketplace.updateSignature(itemId, "ipfs://sig2", bytes32(uint256(0x3333)));

        vm.prank(seller);
        vm.expectRevert(Marketplace.Marketplace__SignatureUrlRequired.selector);
        marketplace.updateSignature(itemId, "", bytes32(uint256(0x3333)));

        uint256 fee = (PRICE * feeBps) / 10_000;
        _buy(itemId, buyer, PRICE + fee);

        vm.prank(seller);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__ItemFrozen.selector, itemId));
        marketplace.updateSignature(itemId, "ipfs://sig2", bytes32(uint256(0x3333)));
    }

    function test_updatePrice_onlySeller_and_notFrozen() public {
        bytes32 itemId = _createDefaultItem();
        vm.prank(address(123));
        vm.expectRevert(Marketplace.Marketplace__SellerRequired.selector);
        marketplace.updatePrice(itemId, 2 ether);

        vm.prank(seller);
        vm.expectRevert(Marketplace.Marketplace__PriceMustBeGreaterThanZero.selector);
        marketplace.updatePrice(itemId, 0);

        uint256 maxPrice = marketplace.MAX_PRICE();
        vm.prank(seller);
        vm.expectRevert(
            abi.encodeWithSelector(Marketplace.Marketplace__PriceExceedsMaximum.selector, maxPrice + 1, maxPrice)
        );
        marketplace.updatePrice(itemId, maxPrice + 1);

        uint256 fee = (PRICE * feeBps) / 10_000;
        _buy(itemId, buyer, PRICE + fee);

        vm.prank(seller);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__ItemFrozen.selector, itemId));
        marketplace.updatePrice(itemId, 2 ether);
    }

    function test_hasAccess_reverts_for_missing_item() public {
        vm.expectRevert(
            abi.encodeWithSelector(Marketplace.Marketplace__ItemDoesNotExist.selector, bytes32(uint256(123)))
        );
        marketplace.hasAccess(bytes32(uint256(123)), bytes32(uint256(1)));
    }

    function test_grantAccess_rejects_duplicate() public {
        bytes32 itemId = _createDefaultItem();
        vm.prank(owner);
        marketplace.grantAccess(itemId, bytes32(uint256(999)));
        vm.prank(owner);
        vm.expectRevert(
            abi.encodeWithSelector(Marketplace.Marketplace__AlreadyHasAccess.selector, bytes32(uint256(999)), itemId)
        );
        marketplace.grantAccess(itemId, bytes32(uint256(999)));
    }

    function test_setFeeConfig_onlyOwner() public {
        vm.prank(address(123));
        vm.expectRevert();
        marketplace.setFeeConfig(address(0xBEEF), 500);
    }

    function test_setFeeConfig_validation() public {
        vm.prank(owner);
        vm.expectRevert(Marketplace.Marketplace__FeeRecipientRequired.selector);
        marketplace.setFeeConfig(address(0), 500);

        vm.prank(owner);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__InvalidFeeBps.selector, 10001));
        marketplace.setFeeConfig(address(0xBEEF), 10001);
    }

    function test_transferOwnership_onlyOwner() public {
        vm.prank(address(123));
        vm.expectRevert();
        marketplace.transferOwnership(address(0xBEEF));
    }

    function test_transferOwnership_changes_owner() public {
        vm.prank(owner);
        marketplace.transferOwnership(address(0xBEEF));
        assertEq(marketplace.owner(), address(0xBEEF));
    }

    function test_renounceOwnership_onlyOwner() public {
        vm.prank(address(123));
        vm.expectRevert();
        marketplace.renounceOwnership();
    }

    function test_renounceOwnership_sets_zero_owner() public {
        vm.prank(owner);
        marketplace.renounceOwnership();
        assertEq(marketplace.owner(), address(0));
    }

    function test_grantAccess_requires_owner_reverts() public {
        bytes32 itemId = _createDefaultItem();
        vm.prank(address(123));
        vm.expectRevert();
        marketplace.grantAccess(itemId, bytes32(uint256(999)));
    }

    function test_grantAccess_sets_access() public {
        bytes32 itemId = _createDefaultItem();
        vm.prank(owner);
        marketplace.grantAccess(itemId, bytes32(uint256(999)));
        assertTrue(marketplace.hasAccess(itemId, bytes32(uint256(999))));
    }
}
