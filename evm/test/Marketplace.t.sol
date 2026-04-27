// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Test} from "forge-std/Test.sol";
import {Marketplace} from "../src/Marketplace.sol";
import {MockCADC} from "../src/MockCADC.sol";
import {MockUSDC} from "../src/MockUSDC.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";

contract MarketplaceTest is Test {
    Marketplace public marketplace;
    MockUSDC public usdc;
    MockCADC public cadc;
    MockUSDC public altToken;

    address owner = address(0xA11CE);
    address feeRecipient = address(0xFEE);
    address seller = address(0xB0B);
    address buyer = address(0xCAFE);
    address poorBuyer = address(0xDEAD);

    uint256 feeBps = 250; // 2.5%
    uint8 constant USDC_DECIMALS = 6;
    uint256 constant USDC_MAX_PRICE = 1_000_000 * 10 ** 6;
    uint8 constant CADC_DECIMALS = 18;
    uint256 constant CADC_MAX_PRICE = 1_000_000 * 10 ** 18;

    string constant TITLE = "Test Dataset";
    string constant DESC = "Synthetic dataset for testing";
    string constant DATASET_URL = "ipfs://dataset";
    bytes32 constant DATASET_HASH = bytes32(uint256(0x1111));
    string constant SIG_URL = "ipfs://signature.json.gz";
    bytes32 constant SIG_HASH = bytes32(uint256(0x2222));
    uint256 constant PRICE = 1_000_000;
    uint256 constant CADC_PRICE = 1 ether;
    uint256 constant ONE_POINT_FIVE_USDC = 1_500_000;
    uint256 constant ONE_POINT_FIVE_CADC = 1_500_000_000_000_000_000;

    uint256 private idCounter = 0;

    event FeeConfigUpdated(uint256 oldFeeBps, uint256 newFeeBps, address oldRecipient, address newRecipient);
    event ItemCreated(
        bytes32 indexed itemId,
        address indexed seller,
        address indexed paymentToken,
        uint256 price,
        string datasetUrl,
        bytes32 datasetHash,
        string signatureUrl,
        bytes32 signatureHash
    );
    event ItemPurchased(
        bytes32 indexed itemId,
        address indexed buyer,
        address indexed paymentToken,
        uint256 pricePaid,
        uint256 feePaid,
        uint256 sellerPaid
    );
    event TokenConfigUpdated(address indexed token, bool enabled, uint8 decimals, uint256 maxPrice);
    event DatasetUrlUpdated(bytes32 indexed itemId, string oldUrl, string newUrl);
    event SignatureUpdated(bytes32 indexed itemId, string oldUrl, string newUrl, bytes32 oldHash, bytes32 newHash);
    event PriceUpdated(bytes32 indexed itemId, uint256 oldPrice, uint256 newPrice);

    function setUp() public {
        usdc = new MockUSDC();
        cadc = new MockCADC();
        altToken = new MockUSDC();
        marketplace = new Marketplace(owner, address(usdc), USDC_DECIMALS, USDC_MAX_PRICE, feeRecipient, feeBps);
        vm.prank(owner);
        marketplace.addAcceptedToken(address(cadc), CADC_DECIMALS, CADC_MAX_PRICE);
        usdc.mint(buyer, 100_000_000);
        cadc.mint(buyer, 100 ether);
        altToken.mint(buyer, 100_000_000);
    }

    function _walletId(address user) internal view returns (bytes32) {
        string memory chainStr = Strings.toString(block.chainid);
        string memory addrStr = Strings.toHexString(uint160(user), 20);
        return keccak256(abi.encodePacked("eip155:", chainStr, ":", addrStr));
    }

    function _createDefaultItem() internal returns (bytes32 itemId) {
        itemId = _createDefaultItemWithToken(address(usdc), PRICE);
    }

    function _createDefaultItemWithToken(address paymentToken, uint256 price) internal returns (bytes32 itemId) {
        itemId = bytes32(idCounter);
        idCounter += 1;
        vm.prank(seller);
        marketplace.createItem(
            itemId, TITLE, DESC, seller, paymentToken, price, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH
        );
    }

    function _buy(bytes32 itemId, address _buyer, uint256 value) internal {
        _buyWithToken(itemId, _buyer, IERC20(address(usdc)), value);
    }

    function _buyWithToken(bytes32 itemId, address _buyer, IERC20 token, uint256 value) internal {
        vm.prank(_buyer);
        token.approve(address(marketplace), value);
        vm.prank(_buyer);
        marketplace.buyItem(itemId);
    }

    function _expectedFee(uint256 price) internal view returns (uint256) {
        return (price * feeBps) / 10_000;
    }

    function _runCreateItemStoresView(address paymentToken, uint256 price) internal {
        bytes32 itemId = _createDefaultItemWithToken(paymentToken, price);
        Marketplace.DataItemView memory v = marketplace.getItemView(itemId);
        assertEq(v.itemId, itemId);
        assertEq(v.title, TITLE);
        assertEq(v.description, DESC);
        assertEq(v.seller, seller);
        assertEq(v.price, price);
        assertEq(v.paymentToken, paymentToken);
    }

    function _runBuyItemSetsAccess(address paymentToken, IERC20 token, uint256 price) internal {
        bytes32 itemId = _createDefaultItemWithToken(paymentToken, price);
        uint256 totalPrice = price + _expectedFee(price);
        _buyWithToken(itemId, buyer, token, totalPrice);
        assertTrue(marketplace.hasAccess(itemId, _walletId(buyer)));
    }

    function _runBuyItemTransfersFunds(address paymentToken, IERC20 token, uint256 price) internal {
        bytes32 itemId = _createDefaultItemWithToken(paymentToken, price);
        uint256 fee = _expectedFee(price);
        uint256 totalPrice = price + fee;
        uint256 sellerBalanceBefore = token.balanceOf(seller);
        uint256 feeBalanceBefore = token.balanceOf(feeRecipient);
        uint256 buyerBalanceBefore = token.balanceOf(buyer);

        _buyWithToken(itemId, buyer, token, totalPrice);

        assertEq(token.balanceOf(seller), sellerBalanceBefore + price);
        assertEq(token.balanceOf(feeRecipient), feeBalanceBefore + fee);
        assertEq(token.balanceOf(buyer), buyerBalanceBefore - totalPrice);
    }

    function test_createItem_requires_seller() public {
        vm.prank(address(123));
        vm.expectRevert(Marketplace.Marketplace__SellerRequired.selector);
        marketplace.createItem(
            bytes32(uint256(1)), TITLE, DESC, seller, address(usdc), PRICE, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH
        );

        vm.prank(address(0x123));
        vm.expectRevert(Marketplace.Marketplace__SellerRequired.selector);
        marketplace.createItem(
            bytes32(uint256(2)),
            TITLE,
            DESC,
            address(0),
            address(usdc),
            PRICE,
            DATASET_URL,
            DATASET_HASH,
            SIG_URL,
            SIG_HASH
        );
    }

    function test_createItem_storesView_usdc() public {
        _runCreateItemStoresView(address(usdc), PRICE);
    }

    function test_createItem_storesView_cadc() public {
        _runCreateItemStoresView(address(cadc), CADC_PRICE);
    }

    function test_createItem_emits_payment_token() public {
        bytes32 itemId = bytes32(uint256(500));

        vm.expectEmit(true, true, true, true);
        emit ItemCreated(itemId, seller, address(cadc), CADC_PRICE, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH);
        vm.prank(seller);
        marketplace.createItem(
            itemId, TITLE, DESC, seller, address(cadc), CADC_PRICE, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH
        );
    }

    function test_constructor_registers_initial_token() public view {
        (bool enabled, uint8 decimals, uint256 maxPrice) = marketplace.acceptedTokens(address(usdc));
        assertTrue(enabled);
        assertEq(decimals, USDC_DECIMALS);
        assertEq(maxPrice, USDC_MAX_PRICE);
        assertEq(marketplace.acceptedTokenCount(), 2);
        assertEq(marketplace.acceptedTokenAt(0), address(usdc));
        assertEq(marketplace.acceptedTokenAt(1), address(cadc));

        address[] memory tokens = marketplace.getAcceptedTokens();
        assertEq(tokens.length, 2);
        assertEq(tokens[0], address(usdc));
        assertEq(tokens[1], address(cadc));
    }

    function test_constructor_rejects_invalid_initial_token_config() public {
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableInvalidOwner.selector, address(0)));
        new Marketplace(address(0), address(usdc), USDC_DECIMALS, USDC_MAX_PRICE, feeRecipient, feeBps);

        vm.expectRevert(Marketplace.Marketplace__SettlementTokenRequired.selector);
        new Marketplace(owner, address(0), USDC_DECIMALS, USDC_MAX_PRICE, feeRecipient, feeBps);

        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__PriceExceedsMaximum.selector, 0, 0));
        new Marketplace(owner, address(usdc), USDC_DECIMALS, 0, feeRecipient, feeBps);

        vm.expectRevert(Marketplace.Marketplace__FeeRecipientRequired.selector);
        new Marketplace(owner, address(usdc), USDC_DECIMALS, USDC_MAX_PRICE, address(0), feeBps);

        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__InvalidFeeBps.selector, 10001));
        new Marketplace(owner, address(usdc), USDC_DECIMALS, USDC_MAX_PRICE, feeRecipient, 10001);
    }

    function test_addAcceptedToken_registers_token_without_duplicates() public {
        vm.prank(owner);
        marketplace.addAcceptedToken(address(altToken), USDC_DECIMALS, USDC_MAX_PRICE);

        (bool enabled, uint8 decimals, uint256 maxPrice) = marketplace.acceptedTokens(address(altToken));
        assertTrue(enabled);
        assertEq(decimals, USDC_DECIMALS);
        assertEq(maxPrice, USDC_MAX_PRICE);
        assertEq(marketplace.acceptedTokenCount(), 3);

        vm.prank(owner);
        marketplace.addAcceptedToken(address(altToken), USDC_DECIMALS, USDC_MAX_PRICE / 2);
        assertEq(marketplace.acceptedTokenCount(), 3);
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

        vm.expectEmit(true, true, true, true);
        emit TokenConfigUpdated(address(altToken), false, USDC_DECIMALS, USDC_MAX_PRICE);
        vm.prank(owner);
        marketplace.setTokenEnabled(address(altToken), false);
        (bool enabled,,) = marketplace.acceptedTokens(address(altToken));
        assertFalse(enabled);

        vm.expectEmit(true, true, true, true);
        emit TokenConfigUpdated(address(altToken), true, USDC_DECIMALS, USDC_MAX_PRICE);
        vm.prank(owner);
        marketplace.setTokenEnabled(address(altToken), true);
        (enabled,,) = marketplace.acceptedTokens(address(altToken));
        assertTrue(enabled);

        address unknownToken = address(0x1234);
        vm.prank(owner);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__TokenNotAccepted.selector, unknownToken));
        marketplace.setTokenEnabled(unknownToken, true);
    }

    function test_createItem_rejects_empty_required_fields() public {
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
    }

    function test_createItem_accepts_empty_signature_artifacts() public {
        bytes32 itemId = bytes32(uint256(2));

        vm.prank(seller);
        marketplace.createItem(
            itemId, TITLE, DESC, seller, address(usdc), PRICE, DATASET_URL, DATASET_HASH, "", bytes32(0)
        );

        Marketplace.DataItemView memory v = marketplace.getItemView(itemId);
        assertEq(v.datasetUrl, DATASET_URL);
        assertEq(v.datasetHash, DATASET_HASH);
        assertEq(v.signatureUrl, "");
        assertEq(v.signatureHash, bytes32(0));
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

    function test_getItems_clips_count_to_total() public {
        for (uint256 i = 0; i < 3; i++) {
            _createDefaultItem();
        }
        Marketplace.DataItemView[] memory items = marketplace.getItems(1, 10);
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

    function test_buyItem_setsAccess_usdc() public {
        _runBuyItemSetsAccess(address(usdc), IERC20(address(usdc)), PRICE);
    }

    function test_buyItem_setsAccess_cadc() public {
        _runBuyItemSetsAccess(address(cadc), IERC20(address(cadc)), CADC_PRICE);
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

    function test_buyItem_rejects_insufficient_balance_cadc() public {
        bytes32 itemId = _createDefaultItemWithToken(address(cadc), CADC_PRICE);
        uint256 fee = _expectedFee(CADC_PRICE);
        uint256 totalPrice = CADC_PRICE + fee;
        cadc.mint(poorBuyer, totalPrice - 1);
        vm.prank(poorBuyer);
        cadc.approve(address(marketplace), totalPrice);
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

    function test_buyItem_prevents_double_purchase_cadc() public {
        bytes32 itemId = _createDefaultItemWithToken(address(cadc), CADC_PRICE);
        uint256 fee = _expectedFee(CADC_PRICE);
        uint256 totalPrice = CADC_PRICE + fee;
        _buyWithToken(itemId, buyer, IERC20(address(cadc)), totalPrice);
        vm.prank(buyer);
        cadc.approve(address(marketplace), totalPrice);
        vm.prank(buyer);
        vm.expectRevert(
            abi.encodeWithSelector(Marketplace.Marketplace__AlreadyHasAccess.selector, _walletId(buyer), itemId)
        );
        marketplace.buyItem(itemId);
    }

    function test_buyItem_transfers_funds_usdc() public {
        _runBuyItemTransfersFunds(address(usdc), IERC20(address(usdc)), PRICE);
    }

    function test_buyItem_transfers_funds_cadc() public {
        _runBuyItemTransfersFunds(address(cadc), IERC20(address(cadc)), CADC_PRICE);
    }

    function test_buyItem_uses_item_payment_token() public {
        bytes32 itemId = _createDefaultItemWithToken(address(cadc), CADC_PRICE);
        uint256 fee = _expectedFee(CADC_PRICE);
        uint256 totalPrice = CADC_PRICE + fee;
        uint256 sellerBalanceBefore = cadc.balanceOf(seller);
        uint256 feeBalanceBefore = cadc.balanceOf(feeRecipient);
        uint256 buyerBalanceBefore = cadc.balanceOf(buyer);

        _buyWithToken(itemId, buyer, IERC20(address(cadc)), totalPrice);

        assertEq(cadc.balanceOf(seller), sellerBalanceBefore + CADC_PRICE);
        assertEq(cadc.balanceOf(feeRecipient), feeBalanceBefore + fee);
        assertEq(cadc.balanceOf(buyer), buyerBalanceBefore - totalPrice);
        assertEq(usdc.balanceOf(seller), 0);
        assertEq(usdc.balanceOf(feeRecipient), 0);
    }

    function test_buyItem_emits_payment_token() public {
        bytes32 itemId = _createDefaultItemWithToken(address(cadc), CADC_PRICE);
        uint256 fee = _expectedFee(CADC_PRICE);
        uint256 totalPrice = CADC_PRICE + fee;

        vm.prank(buyer);
        cadc.approve(address(marketplace), totalPrice);

        vm.expectEmit(true, true, true, true);
        emit ItemPurchased(itemId, buyer, address(cadc), totalPrice, fee, CADC_PRICE);
        vm.prank(buyer);
        marketplace.buyItem(itemId);
    }

    function test_buyItem_zero_fee_transfers_seller_only() public {
        vm.prank(owner);
        marketplace.setFeeConfig(feeRecipient, 0);

        bytes32 itemId = _createDefaultItem();
        uint256 sellerBalanceBefore = usdc.balanceOf(seller);
        uint256 feeBalanceBefore = usdc.balanceOf(feeRecipient);

        _buy(itemId, buyer, PRICE);

        assertEq(usdc.balanceOf(seller), sellerBalanceBefore + PRICE);
        assertEq(usdc.balanceOf(feeRecipient), feeBalanceBefore);
    }

    function test_buyItem_second_distinct_buyer_does_not_refreeze() public {
        address secondBuyer = address(0xBEEF);
        bytes32 itemId = _createDefaultItem();
        uint256 fee = _expectedFee(PRICE);
        uint256 totalPrice = PRICE + fee;

        _buy(itemId, buyer, totalPrice);
        usdc.mint(secondBuyer, totalPrice);
        _buy(itemId, secondBuyer, totalPrice);

        Marketplace.DataItemView memory v = marketplace.getItemView(itemId);
        assertEq(v.purchaseCount, 2);
        assertTrue(marketplace.hasAccess(itemId, _walletId(secondBuyer)));
    }

    function test_buyItem_rejects_disabled_item_payment_token() public {
        vm.prank(owner);
        marketplace.addAcceptedToken(address(altToken), USDC_DECIMALS, USDC_MAX_PRICE);
        bytes32 itemId = _createDefaultItemWithToken(address(altToken), PRICE);
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

    function test_buyItem_rejects_disabled_cadc_payment_token() public {
        bytes32 itemId = _createDefaultItemWithToken(address(cadc), CADC_PRICE);
        uint256 fee = _expectedFee(CADC_PRICE);
        uint256 totalPrice = CADC_PRICE + fee;

        vm.prank(owner);
        marketplace.setTokenEnabled(address(cadc), false);

        vm.prank(buyer);
        cadc.approve(address(marketplace), totalPrice);
        vm.prank(buyer);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__TokenNotAccepted.selector, address(cadc)));
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

        vm.expectEmit(true, true, true, true);
        emit DatasetUrlUpdated(itemId, DATASET_URL, "ipfs://new");
        vm.prank(seller);
        marketplace.updateDatasetUrl(itemId, "ipfs://new");

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

        vm.expectEmit(true, true, true, true);
        emit SignatureUpdated(itemId, SIG_URL, "ipfs://sig2", SIG_HASH, bytes32(uint256(0x3333)));
        vm.prank(seller);
        marketplace.updateSignature(itemId, "ipfs://sig2", bytes32(uint256(0x3333)));

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

        vm.expectEmit(true, true, true, true);
        emit PriceUpdated(itemId, PRICE, 2_000_000);
        vm.prank(seller);
        marketplace.updatePrice(itemId, 2_000_000);

        uint256 fee = (2_000_000 * feeBps) / 10_000;
        _buy(itemId, buyer, 2_000_000 + fee);

        vm.prank(seller);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__ItemFrozen.selector, itemId));
        marketplace.updatePrice(itemId, 2_000_000);
    }

    function test_updatePrice_rejects_disabled_item_payment_token() public {
        vm.prank(owner);
        marketplace.addAcceptedToken(address(altToken), USDC_DECIMALS, USDC_MAX_PRICE);
        bytes32 itemId = _createDefaultItemWithToken(address(altToken), PRICE);

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

    function test_setFeeConfig_updates_fee_and_emits_event() public {
        address newRecipient = address(0xBEEF);
        uint256 newFeeBps = 500;

        vm.expectEmit(true, true, true, true);
        emit FeeConfigUpdated(feeBps, newFeeBps, feeRecipient, newRecipient);
        vm.prank(owner);
        marketplace.setFeeConfig(newRecipient, newFeeBps);

        assertEq(marketplace.feeRecipient(), newRecipient);
        assertEq(marketplace.feeBps(), newFeeBps);
    }

    function test_setFeeConfig_validation() public {
        vm.prank(owner);
        vm.expectRevert(Marketplace.Marketplace__FeeRecipientRequired.selector);
        marketplace.setFeeConfig(address(0), 500);

        vm.prank(owner);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__InvalidFeeBps.selector, 10001));
        marketplace.setFeeConfig(address(0xBEEF), 10001);
    }

    function test_decimal_aware_price_flows_through_fee_math() public {
        bytes32 usdcItemId = _createDefaultItemWithToken(address(usdc), ONE_POINT_FIVE_USDC);
        bytes32 cadcItemId = _createDefaultItemWithToken(address(cadc), ONE_POINT_FIVE_CADC);
        address cadcBuyer = address(0xCADE);

        uint256 usdcFee = _expectedFee(ONE_POINT_FIVE_USDC);
        uint256 cadcFee = _expectedFee(ONE_POINT_FIVE_CADC);
        assertEq(usdcFee, 37_500);
        assertEq(cadcFee, 37_500_000_000_000_000);

        _buyWithToken(usdcItemId, buyer, IERC20(address(usdc)), ONE_POINT_FIVE_USDC + usdcFee);

        cadc.mint(cadcBuyer, ONE_POINT_FIVE_CADC + cadcFee);
        _buyWithToken(cadcItemId, cadcBuyer, IERC20(address(cadc)), ONE_POINT_FIVE_CADC + cadcFee);

        assertEq(usdc.balanceOf(seller), ONE_POINT_FIVE_USDC);
        assertEq(usdc.balanceOf(feeRecipient), usdcFee);
        assertEq(cadc.balanceOf(seller), ONE_POINT_FIVE_CADC);
        assertEq(cadc.balanceOf(feeRecipient), cadcFee);
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
