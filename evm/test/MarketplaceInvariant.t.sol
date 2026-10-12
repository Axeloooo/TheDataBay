// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {StdInvariant} from "forge-std/StdInvariant.sol";
import {Test} from "forge-std/Test.sol";
import {Marketplace} from "../src/Marketplace.sol";
import {MockCADC} from "../src/MockCADC.sol";
import {MockUSDC} from "../src/MockUSDC.sol";

contract MarketplaceInvariantTest is StdInvariant, Test {
    Marketplace public marketplace;
    MockUSDC public usdc;
    MockCADC public cadc;
    MarketplaceInvariantHandler public handler;

    address public owner = address(0xA11CE);
    address public feeRecipient = address(0xFEE);
    address public seller = address(0xB0B);
    address public buyer = address(0xCAFE);

    uint256 public constant FEE_BPS = 250;
    uint8 public constant USDC_DECIMALS = 6;
    uint8 public constant CADC_DECIMALS = 18;
    uint256 public constant USDC_MAX_PRICE = 1_000_000 * 10 ** 6;
    uint256 public constant CADC_MAX_PRICE = 1_000_000 * 10 ** 18;

    function setUp() public {
        usdc = new MockUSDC();
        cadc = new MockCADC();
        marketplace = new Marketplace(owner, address(usdc), USDC_DECIMALS, USDC_MAX_PRICE, feeRecipient, FEE_BPS);

        vm.prank(owner);
        marketplace.addAcceptedToken(address(cadc), CADC_DECIMALS, CADC_MAX_PRICE);

        usdc.mint(buyer, 10_000_000 * 10 ** USDC_DECIMALS);
        cadc.mint(buyer, 10_000_000 * 10 ** CADC_DECIMALS);

        handler = new MarketplaceInvariantHandler(marketplace, usdc, cadc, owner, seller, buyer, feeRecipient, FEE_BPS);
        targetContract(address(handler));
    }

    function invariant_itemPaymentTokenCannotChangeAfterCreation() public view {
        uint256 itemCount = handler.itemCount();
        for (uint256 i; i < itemCount; ++i) {
            bytes32 itemId = handler.itemIds(i);
            Marketplace.DataItemView memory item = marketplace.getItemView(itemId);

            assertEq(item.paymentToken, handler.initialPaymentTokens(itemId));
        }
    }

    function invariant_disabledTokenPurchaseAttemptsDoNotChangeStateOrBalances() public view {
        assertFalse(handler.disabledPurchaseSucceeded());
        assertFalse(handler.disabledPurchaseMutatedStateOrBalances());
    }
}

contract MarketplaceInvariantHandler is Test {
    Marketplace public marketplace;
    MockUSDC public usdc;
    MockCADC public cadc;

    address public owner;
    address public seller;
    address public buyer;
    address public feeRecipient;
    uint256 public feeBps;

    uint256 public constant USDC_MAX_PRICE = 1_000_000 * 10 ** 6;
    uint256 public constant CADC_MAX_PRICE = 1_000_000 * 10 ** 18;

    string public constant TITLE = "Invariant Dataset";
    string public constant DESC = "Synthetic dataset for invariant testing";
    string public constant DATASET_URL = "ipfs://dataset";
    bytes32 public constant DATASET_HASH = bytes32(uint256(0x1111));
    string public constant SIG_URL = "ipfs://signature.json.gz";
    bytes32 public constant SIG_HASH = bytes32(uint256(0x2222));

    bytes32[] public itemIds;
    mapping(bytes32 itemId => address paymentToken) public initialPaymentTokens;

    bool public disabledPurchaseSucceeded;
    bool public disabledPurchaseMutatedStateOrBalances;

    uint256 private nextItemId;

    constructor(
        Marketplace _marketplace,
        MockUSDC _usdc,
        MockCADC _cadc,
        address _owner,
        address _seller,
        address _buyer,
        address _feeRecipient,
        uint256 _feeBps
    ) {
        marketplace = _marketplace;
        usdc = _usdc;
        cadc = _cadc;
        owner = _owner;
        seller = _seller;
        buyer = _buyer;
        feeRecipient = _feeRecipient;
        feeBps = _feeBps;
    }

    function createItem(uint8 tokenChoice, uint256 priceSeed) public {
        (address paymentToken, uint256 maxPrice) = _tokenConfig(tokenChoice);
        uint256 price = _bounded(priceSeed, 1, maxPrice);
        bytes32 itemId = bytes32(nextItemId);
        nextItemId += 1;

        _setTokenEnabled(paymentToken, true);

        vm.prank(seller);
        marketplace.createItem(
            itemId, TITLE, DESC, seller, paymentToken, price, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH
        );

        itemIds.push(itemId);
        initialPaymentTokens[itemId] = paymentToken;
    }

    function updatePrice(uint8 itemSeed, uint256 priceSeed) public {
        if (itemIds.length == 0) return;

        bytes32 itemId = itemIds[_bounded(uint256(itemSeed), 0, itemIds.length - 1)];
        Marketplace.DataItemView memory item = marketplace.getItemView(itemId);
        (, uint256 maxPrice) = _tokenConfigForAddress(item.paymentToken);
        uint256 price = _bounded(priceSeed, 1, maxPrice);

        _setTokenEnabled(item.paymentToken, true);

        vm.prank(seller);
        try marketplace.updatePrice(itemId, price) {} catch {}
    }

    function buyItem(uint8 itemSeed) public {
        if (itemIds.length == 0) return;

        bytes32 itemId = itemIds[_bounded(uint256(itemSeed), 0, itemIds.length - 1)];
        Marketplace.DataItemView memory item = marketplace.getItemView(itemId);
        uint256 totalPrice = _totalPrice(item.price);

        _setTokenEnabled(item.paymentToken, true);
        _approve(item.paymentToken, totalPrice);

        vm.prank(buyer);
        try marketplace.buyItem(itemId) {} catch {}
    }

    function setTokenEnabled(uint8 tokenChoice, bool enabled) public {
        (address paymentToken,) = _tokenConfig(tokenChoice);

        _setTokenEnabled(paymentToken, enabled);
    }

    function attemptDisabledTokenPurchase(uint8 itemSeed) public {
        if (itemIds.length == 0) return;

        bytes32 itemId = itemIds[_bounded(uint256(itemSeed), 0, itemIds.length - 1)];
        Marketplace.DataItemView memory beforeItem = marketplace.getItemView(itemId);
        address paymentToken = beforeItem.paymentToken;
        uint256 buyerBalanceBefore = _balanceOf(paymentToken, buyer);
        uint256 sellerBalanceBefore = _balanceOf(paymentToken, seller);
        uint256 feeBalanceBefore = _balanceOf(paymentToken, feeRecipient);
        bool hadAccessBefore = _hasAccess(itemId, buyer);

        _setTokenEnabled(paymentToken, false);
        _approve(paymentToken, _totalPrice(beforeItem.price));

        vm.prank(buyer);
        try marketplace.buyItem(itemId) {
            disabledPurchaseSucceeded = true;
        } catch {}

        Marketplace.DataItemView memory afterItem = marketplace.getItemView(itemId);
        bool mutated = afterItem.purchaseCount != beforeItem.purchaseCount
            || _balanceOf(paymentToken, buyer) != buyerBalanceBefore
            || _balanceOf(paymentToken, seller) != sellerBalanceBefore
            || _balanceOf(paymentToken, feeRecipient) != feeBalanceBefore
            || _hasAccess(itemId, buyer) != hadAccessBefore;

        if (mutated) {
            disabledPurchaseMutatedStateOrBalances = true;
        }
    }

    function itemCount() external view returns (uint256 count) {
        count = itemIds.length;
    }

    function _setTokenEnabled(address paymentToken, bool enabled) internal {
        vm.prank(owner);
        marketplace.setTokenEnabled(paymentToken, enabled);
    }

    function _approve(address paymentToken, uint256 amount) internal {
        vm.prank(buyer);
        if (paymentToken == address(usdc)) {
            usdc.approve(address(marketplace), amount);
        } else {
            cadc.approve(address(marketplace), amount);
        }
    }

    function _balanceOf(address paymentToken, address account) internal view returns (uint256 balance) {
        if (paymentToken == address(usdc)) {
            balance = usdc.balanceOf(account);
        } else {
            balance = cadc.balanceOf(account);
        }
    }

    function _hasAccess(bytes32 itemId, address account) internal view returns (bool hasAccess) {
        string memory chainStr = vm.toString(block.chainid);
        string memory addrStr = vm.toString(account);
        bytes32 walletId = keccak256(abi.encodePacked("eip155:", chainStr, ":", addrStr));
        hasAccess = marketplace.hasAccess(itemId, walletId);
    }

    function _totalPrice(uint256 price) internal view returns (uint256 totalPrice) {
        totalPrice = price + ((price * feeBps) / 10_000);
    }

    function _bounded(uint256 seed, uint256 min, uint256 max) internal pure returns (uint256 result) {
        result = min + (seed % (max - min + 1));
    }

    function _tokenConfig(uint8 tokenChoice) internal view returns (address paymentToken, uint256 maxPrice) {
        if (tokenChoice % 2 == 0) {
            paymentToken = address(usdc);
            maxPrice = USDC_MAX_PRICE;
        } else {
            paymentToken = address(cadc);
            maxPrice = CADC_MAX_PRICE;
        }
    }

    function _tokenConfigForAddress(address paymentToken) internal view returns (address token, uint256 maxPrice) {
        token = paymentToken;
        maxPrice = paymentToken == address(usdc) ? USDC_MAX_PRICE : CADC_MAX_PRICE;
    }
}
