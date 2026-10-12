// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Test} from "forge-std/Test.sol";
import {Vm} from "forge-std/Vm.sol";
import {Marketplace} from "../src/Marketplace.sol";
import {MockCADC} from "../src/MockCADC.sol";
import {MockUSDC} from "../src/MockUSDC.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";

contract MarketplacePurchaseTest is Test {
    event ItemPurchased(
        bytes32 indexed itemId,
        address indexed buyer,
        address indexed paymentToken,
        uint256 pricePaid,
        uint256 feePaid,
        uint256 sellerPaid
    );
    event ItemFrozenAfterSale(bytes32 indexed itemId);

    Marketplace public marketplace;
    MockUSDC public usdc;
    MockCADC public cadc;

    address internal owner = address(0xA11CE);
    address internal feeRecipient = address(0xFEE);
    address internal seller = address(0xB0B);
    address internal buyer = address(0xCAFE);
    address internal secondBuyer = address(0xBEEF);
    address internal poorBuyer = address(0xDEAD);

    uint256 internal constant FEE_BPS = 250;
    uint8 internal constant USDC_DECIMALS = 6;
    uint8 internal constant CADC_DECIMALS = 18;
    uint256 internal constant USDC_MAX_PRICE = 1_000_000 * 10 ** USDC_DECIMALS;
    uint256 internal constant CADC_MAX_PRICE = 1_000_000 ether;
    uint256 internal constant USDC_PRICE = 1_000_000;
    uint256 internal constant CADC_PRICE = 20 ether;

    string internal constant TITLE = "Purchase Dataset";
    string internal constant DESC = "Synthetic dataset for purchase branch tests";
    string internal constant DATASET_URL = "ipfs://purchase-dataset";
    bytes32 internal constant DATASET_HASH = bytes32(uint256(0x1111));
    string internal constant SIG_URL = "ipfs://purchase-signature.json.gz";
    bytes32 internal constant SIG_HASH = bytes32(uint256(0x2222));

    uint256 private idCounter;

    modifier whenItemExists() {
        _;
    }

    modifier givenBuyerIsNotSellerAndTokenEnabled() {
        _;
    }

    modifier givenBuyerDoesNotHaveAccess() {
        _;
    }

    modifier givenFeeBpsGreaterThanZero() {
        _;
    }

    function setUp() public {
        usdc = new MockUSDC();
        cadc = new MockCADC();
        marketplace = new Marketplace(owner, address(usdc), USDC_DECIMALS, USDC_MAX_PRICE, feeRecipient, FEE_BPS);

        vm.prank(owner);
        marketplace.addAcceptedToken(address(cadc), CADC_DECIMALS, CADC_MAX_PRICE);

        usdc.mint(buyer, 100_000_000);
        usdc.mint(secondBuyer, 100_000_000);
        cadc.mint(buyer, 100 ether);
        cadc.mint(secondBuyer, 100 ether);
    }

    function test_RevertWhen_ItemDoesNotExist() external {
        bytes32 missingItemId = bytes32(uint256(999));

        vm.prank(buyer);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__ItemDoesNotExist.selector, missingItemId));
        marketplace.buyItem(missingItemId);
    }

    function test_RevertGiven_BuyerIsSeller() external whenItemExists {
        bytes32 itemId = _createUsdcItem();
        uint256 totalPrice = _totalPrice(USDC_PRICE);
        usdc.mint(seller, totalPrice);

        vm.prank(seller);
        usdc.approve(address(marketplace), totalPrice);
        vm.prank(seller);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__SellerCannotBuyOwnItem.selector));
        marketplace.buyItem(itemId);
    }

    function test_RevertGiven_ItemPaymentTokenDisabled() external whenItemExists {
        bytes32 itemId = _createCadcItem();

        vm.prank(owner);
        marketplace.setTokenEnabled(address(cadc), false);

        vm.prank(buyer);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__TokenNotAccepted.selector, address(cadc)));
        marketplace.buyItem(itemId);
    }

    function test_RevertGiven_InsufficientAllowance() external whenItemExists givenBuyerIsNotSellerAndTokenEnabled {
        bytes32 itemId = _createUsdcItem();
        uint256 totalPrice = _totalPrice(USDC_PRICE);
        uint256 allowance = totalPrice - 1;

        vm.prank(buyer);
        usdc.approve(address(marketplace), allowance);
        vm.prank(buyer);
        vm.expectRevert(
            abi.encodeWithSelector(Marketplace.Marketplace__InsufficientAllowance.selector, totalPrice, allowance)
        );
        marketplace.buyItem(itemId);
    }

    function test_RevertGiven_InsufficientBalance() external whenItemExists givenBuyerIsNotSellerAndTokenEnabled {
        bytes32 itemId = _createUsdcItem();
        uint256 totalPrice = _totalPrice(USDC_PRICE);
        uint256 balance = totalPrice - 1;

        usdc.mint(poorBuyer, balance);
        vm.prank(poorBuyer);
        usdc.approve(address(marketplace), totalPrice);
        vm.prank(poorBuyer);
        vm.expectRevert(
            abi.encodeWithSelector(Marketplace.Marketplace__InsufficientBalance.selector, totalPrice, balance)
        );
        marketplace.buyItem(itemId);
    }

    function test_RevertGiven_BuyerAlreadyHasAccess() external whenItemExists givenBuyerIsNotSellerAndTokenEnabled {
        bytes32 itemId = _createUsdcItem();
        uint256 totalPrice = _totalPrice(USDC_PRICE);

        _approveAndBuy(itemId, buyer, usdc, totalPrice);

        vm.prank(buyer);
        usdc.approve(address(marketplace), totalPrice);
        vm.prank(buyer);
        vm.expectRevert(
            abi.encodeWithSelector(Marketplace.Marketplace__AlreadyHasAccess.selector, _walletId(buyer), itemId)
        );
        marketplace.buyItem(itemId);
    }

    function test_WhenFirstPurchaseWithFee()
        external
        whenItemExists
        givenBuyerIsNotSellerAndTokenEnabled
        givenBuyerDoesNotHaveAccess
        givenFeeBpsGreaterThanZero
    {
        bytes32 itemId = _createUsdcItem();
        uint256 fee = _fee(USDC_PRICE);
        uint256 totalPrice = USDC_PRICE + fee;
        uint256 buyerBalanceBefore = usdc.balanceOf(buyer);

        vm.prank(buyer);
        usdc.approve(address(marketplace), totalPrice);
        vm.expectEmit(true, false, false, true, address(marketplace));
        emit ItemFrozenAfterSale(itemId);
        vm.expectEmit(true, true, true, true, address(marketplace));
        emit ItemPurchased(itemId, buyer, address(usdc), totalPrice, fee, USDC_PRICE);
        vm.prank(buyer);
        marketplace.buyItem(itemId);

        Marketplace.DataItemView memory item = marketplace.getItemView(itemId);
        assertEq(item.purchaseCount, 1);
        assertTrue(marketplace.hasAccess(itemId, _walletId(buyer)));
        assertEq(usdc.balanceOf(feeRecipient), fee);
        assertEq(usdc.balanceOf(seller), USDC_PRICE);
        assertEq(usdc.balanceOf(buyer), buyerBalanceBefore - totalPrice);
    }

    function test_WhenZeroFeePurchaseSkipsFeeRecipientTransfer()
        external
        whenItemExists
        givenBuyerIsNotSellerAndTokenEnabled
        givenBuyerDoesNotHaveAccess
    {
        marketplace = new Marketplace(owner, address(usdc), USDC_DECIMALS, USDC_MAX_PRICE, feeRecipient, 0);
        vm.prank(owner);
        marketplace.addAcceptedToken(address(cadc), CADC_DECIMALS, CADC_MAX_PRICE);
        bytes32 itemId = _createUsdcItem();
        uint256 buyerBalanceBefore = usdc.balanceOf(buyer);
        uint256 feeRecipientBalanceBefore = usdc.balanceOf(feeRecipient);

        vm.prank(buyer);
        usdc.approve(address(marketplace), USDC_PRICE);
        vm.expectEmit(true, false, false, true, address(marketplace));
        emit ItemFrozenAfterSale(itemId);
        vm.expectEmit(true, true, true, true, address(marketplace));
        emit ItemPurchased(itemId, buyer, address(usdc), USDC_PRICE, 0, USDC_PRICE);
        vm.prank(buyer);
        marketplace.buyItem(itemId);

        Marketplace.DataItemView memory item = marketplace.getItemView(itemId);
        assertEq(item.purchaseCount, 1);
        assertTrue(marketplace.hasAccess(itemId, _walletId(buyer)));
        assertEq(usdc.balanceOf(feeRecipient), feeRecipientBalanceBefore);
        assertEq(usdc.balanceOf(seller), USDC_PRICE);
        assertEq(usdc.balanceOf(buyer), buyerBalanceBefore - USDC_PRICE);
    }

    function test_WhenSecondDistinctBuyerPurchases() external whenItemExists givenFeeBpsGreaterThanZero {
        bytes32 itemId = _createUsdcItem();
        uint256 totalPrice = _totalPrice(USDC_PRICE);

        _approveAndBuy(itemId, buyer, usdc, totalPrice);
        vm.recordLogs();
        _approveAndBuy(itemId, secondBuyer, usdc, totalPrice);

        Marketplace.DataItemView memory item = marketplace.getItemView(itemId);
        assertEq(item.purchaseCount, 2);
        assertTrue(marketplace.hasAccess(itemId, _walletId(buyer)));
        assertTrue(marketplace.hasAccess(itemId, _walletId(secondBuyer)));
        _assertNoItemFrozenAfterSaleEvent();
    }

    function test_WhenCadcPurchaseWithFee() external whenItemExists givenFeeBpsGreaterThanZero {
        bytes32 itemId = _createCadcItem();
        uint256 fee = _fee(CADC_PRICE);
        uint256 totalPrice = CADC_PRICE + fee;
        uint256 buyerBalanceBefore = cadc.balanceOf(buyer);

        vm.prank(buyer);
        cadc.approve(address(marketplace), totalPrice);
        vm.expectEmit(true, false, false, true, address(marketplace));
        emit ItemFrozenAfterSale(itemId);
        vm.expectEmit(true, true, true, true, address(marketplace));
        emit ItemPurchased(itemId, buyer, address(cadc), totalPrice, fee, CADC_PRICE);
        vm.prank(buyer);
        marketplace.buyItem(itemId);

        Marketplace.DataItemView memory item = marketplace.getItemView(itemId);
        assertEq(item.purchaseCount, 1);
        assertTrue(marketplace.hasAccess(itemId, _walletId(buyer)));
        assertEq(cadc.balanceOf(feeRecipient), fee);
        assertEq(cadc.balanceOf(seller), CADC_PRICE);
        assertEq(cadc.balanceOf(buyer), buyerBalanceBefore - totalPrice);
        assertEq(usdc.balanceOf(seller), 0);
        assertEq(usdc.balanceOf(feeRecipient), 0);
    }

    function _createUsdcItem() internal returns (bytes32 itemId) {
        itemId = _nextItemId();
        _createItem(itemId, address(usdc), USDC_PRICE);
    }

    function _createCadcItem() internal returns (bytes32 itemId) {
        itemId = _nextItemId();
        _createItem(itemId, address(cadc), CADC_PRICE);
    }

    function _createItem(bytes32 itemId, address paymentToken, uint256 price) internal {
        vm.prank(seller);
        marketplace.createItem(
            itemId, TITLE, DESC, seller, paymentToken, price, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH
        );
    }

    function _approveAndBuy(bytes32 itemId, address purchaser, MockUSDC token, uint256 amount) internal {
        vm.prank(purchaser);
        token.approve(address(marketplace), amount);
        vm.prank(purchaser);
        marketplace.buyItem(itemId);
    }

    function _nextItemId() internal returns (bytes32 itemId) {
        itemId = bytes32(idCounter);
        idCounter += 1;
    }

    function _fee(uint256 price) internal pure returns (uint256) {
        return (price * FEE_BPS) / 10_000;
    }

    function _assertNoItemFrozenAfterSaleEvent() internal view {
        Vm.Log[] memory logs = vm.getRecordedLogs();
        bytes32 freezeTopic = ItemFrozenAfterSale.selector;
        for (uint256 i; i < logs.length; i++) {
            assertTrue(logs[i].topics.length == 0 || logs[i].topics[0] != freezeTopic);
        }
    }

    function _totalPrice(uint256 price) internal pure returns (uint256) {
        return price + _fee(price);
    }

    function _walletId(address user) internal view returns (bytes32) {
        string memory chainStr = Strings.toString(block.chainid);
        string memory addrStr = Strings.toHexString(uint160(user), 20);
        return keccak256(abi.encodePacked("eip155:", chainStr, ":", addrStr));
    }
}
