// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Test} from "forge-std/Test.sol";
import {Marketplace} from "../src/Marketplace.sol";
import {MockUSDC} from "../src/MockUSDC.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";

contract MarketplaceTest is Test {
    Marketplace public marketplace;
    MockUSDC public usdc;
    MockUSDC public altToken;

    address owner = address(0xA11CE);
    address feeRecipient = address(0xFEE);
    address seller = address(0xB0B);
    address buyer = address(0xCAFE);
    address poorBuyer = address(0xDEAD);

    uint256 feeBps = 250; // 2.5%
    uint8 constant USDC_DECIMALS = 6;
    uint256 constant USDC_MAX_PRICE = 1_000_000 * 10 ** 6;

    string constant TITLE = "Test Dataset";
    string constant DESC = "Synthetic dataset for testing";
    string constant DATASET_URL = "ipfs://dataset";
    bytes32 constant DATASET_HASH = bytes32(uint256(0x1111));
    string constant SIG_URL = "ipfs://signature.json.gz";
    bytes32 constant SIG_HASH = bytes32(uint256(0x2222));
    uint256 constant PRICE = 1_000_000;

    uint256 private idCounter = 0;

    function setUp() public {
        usdc = new MockUSDC();
        altToken = new MockUSDC();
        marketplace = new Marketplace(owner, address(usdc), USDC_DECIMALS, USDC_MAX_PRICE, feeRecipient, feeBps);
        usdc.mint(buyer, 100_000_000);
        altToken.mint(buyer, 100_000_000);
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
        marketplace.createItem(
            itemId, TITLE, DESC, seller, address(usdc), PRICE, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH
        );
    }

    function _createDefaultItemWithToken(address paymentToken) internal returns (bytes32 itemId) {
        itemId = bytes32(idCounter);
        idCounter += 1;
        vm.prank(seller);
        marketplace.createItem(
            itemId, TITLE, DESC, seller, paymentToken, PRICE, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH
        );
    }

    function _buy(bytes32 itemId, address _buyer, uint256 value) internal {
        vm.prank(_buyer);
        usdc.approve(address(marketplace), value);
        vm.prank(_buyer);
        marketplace.buyItem(itemId);
    }

    function _buyWithToken(bytes32 itemId, address _buyer, MockUSDC token, uint256 value) internal {
        vm.prank(_buyer);
        token.approve(address(marketplace), value);
        vm.prank(_buyer);
        marketplace.buyItem(itemId);
    }

    function test_createItem_requires_seller() public {
        vm.prank(address(123));
        vm.expectRevert(Marketplace.Marketplace__SellerRequired.selector);
        marketplace.createItem(
            bytes32(uint256(1)), TITLE, DESC, seller, address(usdc), PRICE, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH
        );
    }

    function test_createItem_storesView() public {
        bytes32 itemId = _createDefaultItem();
        Marketplace.DataItemView memory v = marketplace.getItemView(itemId);
        assertEq(v.itemId, itemId);
        assertEq(v.title, TITLE);
        assertEq(v.description, DESC);
        assertEq(v.seller, seller);
        assertEq(v.price, PRICE);
        assertEq(v.paymentToken, address(usdc));
    }

    function test_constructor_registers_initial_token() public view {
        (bool enabled, uint8 decimals, uint256 maxPrice) = marketplace.acceptedTokens(address(usdc));
        assertTrue(enabled);
        assertEq(decimals, USDC_DECIMALS);
        assertEq(maxPrice, USDC_MAX_PRICE);
        assertEq(marketplace.acceptedTokenCount(), 1);
        assertEq(marketplace.acceptedTokenAt(0), address(usdc));

        address[] memory tokens = marketplace.getAcceptedTokens();
        assertEq(tokens.length, 1);
        assertEq(tokens[0], address(usdc));
    }

    function test_constructor_rejects_invalid_initial_token_config() public {
        vm.expectRevert(Marketplace.Marketplace__SettlementTokenRequired.selector);
        new Marketplace(owner, address(0), USDC_DECIMALS, USDC_MAX_PRICE, feeRecipient, feeBps);

        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__PriceExceedsMaximum.selector, 0, 0));
        new Marketplace(owner, address(usdc), USDC_DECIMALS, 0, feeRecipient, feeBps);
    }

    function test_addAcceptedToken_registers_token_without_duplicates() public {
        vm.prank(owner);
        marketplace.addAcceptedToken(address(altToken), USDC_DECIMALS, USDC_MAX_PRICE);

        (bool enabled, uint8 decimals, uint256 maxPrice) = marketplace.acceptedTokens(address(altToken));
        assertTrue(enabled);
        assertEq(decimals, USDC_DECIMALS);
        assertEq(maxPrice, USDC_MAX_PRICE);
        assertEq(marketplace.acceptedTokenCount(), 2);

        vm.prank(owner);
        marketplace.addAcceptedToken(address(altToken), USDC_DECIMALS, USDC_MAX_PRICE / 2);
        assertEq(marketplace.acceptedTokenCount(), 2);
        (enabled, decimals, maxPrice) = marketplace.acceptedTokens(address(altToken));
        assertTrue(enabled);
        assertEq(decimals, USDC_DECIMALS);
        assertEq(maxPrice, USDC_MAX_PRICE / 2);
    }

    function test_addAcceptedToken_validation() public {
        vm.prank(address(123));
        vm.expectRevert();
        marketplace.addAcceptedToken(address(altToken), USDC_DECIMALS, USDC_MAX_PRICE);

        vm.prank(owner);
        vm.expectRevert(Marketplace.Marketplace__SettlementTokenRequired.selector);
        marketplace.addAcceptedToken(address(0), USDC_DECIMALS, USDC_MAX_PRICE);

        vm.prank(owner);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__PriceExceedsMaximum.selector, 0, 0));
        marketplace.addAcceptedToken(address(altToken), USDC_DECIMALS, 0);
    }

    function test_setTokenEnabled_updates_existing_token_only() public {
        vm.prank(owner);
        marketplace.addAcceptedToken(address(altToken), USDC_DECIMALS, USDC_MAX_PRICE);

        vm.prank(owner);
        marketplace.setTokenEnabled(address(altToken), false);
        (bool enabled,,) = marketplace.acceptedTokens(address(altToken));
        assertFalse(enabled);

        vm.prank(owner);
        marketplace.setTokenEnabled(address(altToken), true);
        (enabled,,) = marketplace.acceptedTokens(address(altToken));
        assertTrue(enabled);

        address unknownToken = address(0x1234);
        vm.prank(owner);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__TokenNotAccepted.selector, unknownToken));
        marketplace.setTokenEnabled(unknownToken, true);
    }

    function test_createItem_rejects_empty_fields() public {
        bytes32 itemId = bytes32(uint256(1));
        vm.prank(seller);
        vm.expectRevert(Marketplace.Marketplace__TitleRequired.selector);
        marketplace.createItem(
            itemId, "", DESC, seller, address(usdc), PRICE, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH
        );

        vm.prank(seller);
        vm.expectRevert(Marketplace.Marketplace__DescriptionRequired.selector);
        marketplace.createItem(
            itemId, TITLE, "", seller, address(usdc), PRICE, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH
        );

        vm.prank(seller);
        vm.expectRevert(Marketplace.Marketplace__DatasetUrlRequired.selector);
        marketplace.createItem(itemId, TITLE, DESC, seller, address(usdc), PRICE, "", DATASET_HASH, SIG_URL, SIG_HASH);

        vm.prank(seller);
        vm.expectRevert(Marketplace.Marketplace__SignatureUrlRequired.selector);
        marketplace.createItem(
            itemId, TITLE, DESC, seller, address(usdc), PRICE, DATASET_URL, DATASET_HASH, "", SIG_HASH
        );
    }

    function test_createItem_rejects_invalid_price() public {
        bytes32 itemId = bytes32(uint256(1));
        vm.prank(seller);
        vm.expectRevert(Marketplace.Marketplace__PriceMustBeGreaterThanZero.selector);
        marketplace.createItem(
            itemId, TITLE, DESC, seller, address(usdc), 0, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH
        );

        uint256 maxPrice = USDC_MAX_PRICE;
        vm.prank(seller);
        vm.expectRevert(
            abi.encodeWithSelector(Marketplace.Marketplace__PriceExceedsMaximum.selector, maxPrice + 1, maxPrice)
        );
        marketplace.createItem(
            itemId, TITLE, DESC, seller, address(usdc), maxPrice + 1, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH
        );
    }

    function test_createItem_rejects_unaccepted_or_disabled_token() public {
        bytes32 itemId = bytes32(uint256(1));

        vm.prank(seller);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__TokenNotAccepted.selector, address(altToken)));
        marketplace.createItem(
            itemId, TITLE, DESC, seller, address(altToken), PRICE, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH
        );

        vm.prank(owner);
        marketplace.addAcceptedToken(address(altToken), USDC_DECIMALS, USDC_MAX_PRICE);
        vm.prank(owner);
        marketplace.setTokenEnabled(address(altToken), false);

        vm.prank(seller);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__TokenNotAccepted.selector, address(altToken)));
        marketplace.createItem(
            itemId, TITLE, DESC, seller, address(altToken), PRICE, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH
        );
    }

    function test_createItem_rejects_duplicate() public {
        bytes32 itemId = _createDefaultItem();
        vm.prank(seller);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__ItemAlreadyExists.selector, itemId));
        marketplace.createItem(
            itemId, TITLE, DESC, seller, address(usdc), PRICE, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH
        );
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
        marketplace.buyItem(bytes32(uint256(999)));
    }

    function test_buyItem_rejects_insufficient_allowance() public {
        bytes32 itemId = _createDefaultItem();
        uint256 fee = (PRICE * feeBps) / 10_000;
        uint256 totalPrice = PRICE + fee;
        vm.prank(buyer);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__InsufficientAllowance.selector, totalPrice, 0));
        marketplace.buyItem(itemId);
    }

    function test_buyItem_rejects_insufficient_balance() public {
        bytes32 itemId = _createDefaultItem();
        uint256 fee = (PRICE * feeBps) / 10_000;
        uint256 totalPrice = PRICE + fee;
        usdc.mint(poorBuyer, totalPrice - 1);
        vm.prank(poorBuyer);
        usdc.approve(address(marketplace), totalPrice);
        vm.prank(poorBuyer);
        vm.expectRevert(
            abi.encodeWithSelector(Marketplace.Marketplace__InsufficientBalance.selector, totalPrice, totalPrice - 1)
        );
        marketplace.buyItem(itemId);
    }

    function test_buyItem_prevents_double_purchase() public {
        bytes32 itemId = _createDefaultItem();
        uint256 fee = (PRICE * feeBps) / 10_000;
        uint256 totalPrice = PRICE + fee;
        _buy(itemId, buyer, totalPrice);
        vm.prank(buyer);
        usdc.approve(address(marketplace), totalPrice);
        vm.prank(buyer);
        vm.expectRevert(
            abi.encodeWithSelector(Marketplace.Marketplace__AlreadyHasAccess.selector, _walletId(buyer), itemId)
        );
        marketplace.buyItem(itemId);
    }

    function test_buyItem_transfers_funds() public {
        bytes32 itemId = _createDefaultItem();
        uint256 fee = (PRICE * feeBps) / 10_000;
        uint256 totalPrice = PRICE + fee;
        uint256 sellerBalanceBefore = usdc.balanceOf(seller);
        uint256 feeBalanceBefore = usdc.balanceOf(feeRecipient);
        uint256 buyerBalanceBefore = usdc.balanceOf(buyer);

        _buy(itemId, buyer, totalPrice);

        assertEq(usdc.balanceOf(seller), sellerBalanceBefore + PRICE);
        assertEq(usdc.balanceOf(feeRecipient), feeBalanceBefore + fee);
        assertEq(usdc.balanceOf(buyer), buyerBalanceBefore - totalPrice);
    }

    function test_buyItem_uses_item_payment_token() public {
        vm.prank(owner);
        marketplace.addAcceptedToken(address(altToken), USDC_DECIMALS, USDC_MAX_PRICE);
        bytes32 itemId = _createDefaultItemWithToken(address(altToken));
        uint256 fee = (PRICE * feeBps) / 10_000;
        uint256 totalPrice = PRICE + fee;
        uint256 sellerBalanceBefore = altToken.balanceOf(seller);
        uint256 feeBalanceBefore = altToken.balanceOf(feeRecipient);
        uint256 buyerBalanceBefore = altToken.balanceOf(buyer);

        _buyWithToken(itemId, buyer, altToken, totalPrice);

        assertEq(altToken.balanceOf(seller), sellerBalanceBefore + PRICE);
        assertEq(altToken.balanceOf(feeRecipient), feeBalanceBefore + fee);
        assertEq(altToken.balanceOf(buyer), buyerBalanceBefore - totalPrice);
        assertEq(usdc.balanceOf(seller), 0);
        assertEq(usdc.balanceOf(feeRecipient), 0);
    }

    function test_buyItem_rejects_disabled_item_payment_token() public {
        vm.prank(owner);
        marketplace.addAcceptedToken(address(altToken), USDC_DECIMALS, USDC_MAX_PRICE);
        bytes32 itemId = _createDefaultItemWithToken(address(altToken));
        uint256 fee = (PRICE * feeBps) / 10_000;
        uint256 totalPrice = PRICE + fee;

        vm.prank(owner);
        marketplace.setTokenEnabled(address(altToken), false);

        vm.prank(buyer);
        altToken.approve(address(marketplace), totalPrice);
        vm.prank(buyer);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__TokenNotAccepted.selector, address(altToken)));
        marketplace.buyItem(itemId);
    }

    function test_buyItem_rejects_seller_purchase() public {
        bytes32 itemId = _createDefaultItem();
        uint256 fee = (PRICE * feeBps) / 10_000;
        uint256 totalPrice = PRICE + fee;
        usdc.mint(seller, totalPrice);
        vm.prank(seller);
        usdc.approve(address(marketplace), totalPrice);
        vm.prank(seller);
        vm.expectRevert(Marketplace.Marketplace__SellerCannotBuyOwnItem.selector);
        marketplace.buyItem(itemId);
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
        marketplace.updatePrice(itemId, 2_000_000);

        vm.prank(seller);
        vm.expectRevert(Marketplace.Marketplace__PriceMustBeGreaterThanZero.selector);
        marketplace.updatePrice(itemId, 0);

        uint256 maxPrice = USDC_MAX_PRICE;
        vm.prank(seller);
        vm.expectRevert(
            abi.encodeWithSelector(Marketplace.Marketplace__PriceExceedsMaximum.selector, maxPrice + 1, maxPrice)
        );
        marketplace.updatePrice(itemId, maxPrice + 1);

        uint256 fee = (PRICE * feeBps) / 10_000;
        _buy(itemId, buyer, PRICE + fee);

        vm.prank(seller);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__ItemFrozen.selector, itemId));
        marketplace.updatePrice(itemId, 2_000_000);
    }

    function test_updatePrice_rejects_disabled_item_payment_token() public {
        vm.prank(owner);
        marketplace.addAcceptedToken(address(altToken), USDC_DECIMALS, USDC_MAX_PRICE);
        bytes32 itemId = _createDefaultItemWithToken(address(altToken));

        vm.prank(owner);
        marketplace.setTokenEnabled(address(altToken), false);

        vm.prank(seller);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__TokenNotAccepted.selector, address(altToken)));
        marketplace.updatePrice(itemId, 2_000_000);
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
