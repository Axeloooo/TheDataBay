// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Test} from "forge-std/Test.sol";
import {Marketplace} from "../src/Marketplace.sol";
import {MockCADC} from "../src/MockCADC.sol";
import {MockUSDC} from "../src/MockUSDC.sol";

contract MarketplacePriceFuzzTest is Test {
    Marketplace public marketplace;
    MockUSDC public usdc;
    MockCADC public cadc;

    address public owner = address(0xA11CE);
    address public feeRecipient = address(0xFEE);
    address public seller = address(0xB0B);

    uint256 public constant FEE_BPS = 250;
    uint8 public constant USDC_DECIMALS = 6;
    uint8 public constant CADC_DECIMALS = 18;
    uint256 public constant USDC_MAX_PRICE = 1_000_000 * 10 ** 6;
    uint256 public constant CADC_MAX_PRICE = 1_000_000 * 10 ** 18;

    string public constant TITLE = "Test Dataset";
    string public constant DESC = "Synthetic dataset for testing";
    string public constant DATASET_URL = "ipfs://dataset";
    bytes32 public constant DATASET_HASH = bytes32(uint256(0x1111));
    string public constant SIG_URL = "ipfs://signature.json.gz";
    bytes32 public constant SIG_HASH = bytes32(uint256(0x2222));

    uint256 private idCounter;

    function setUp() public {
        usdc = new MockUSDC();
        cadc = new MockCADC();
        marketplace = new Marketplace(owner, address(usdc), USDC_DECIMALS, USDC_MAX_PRICE, feeRecipient, FEE_BPS);

        vm.prank(owner);
        marketplace.addAcceptedToken(address(cadc), CADC_DECIMALS, CADC_MAX_PRICE);
    }

    function testFuzz_createItem_acceptsValidUSDCPrice(uint256 price) public {
        vm.assume(price > 0 && price <= USDC_MAX_PRICE);

        bytes32 itemId = _createItem(address(usdc), price);

        Marketplace.DataItemView memory item = marketplace.getItemView(itemId);
        assertEq(item.price, price);
        assertEq(item.paymentToken, address(usdc));
    }

    function testFuzz_createItem_acceptsValidCADCPrice(uint256 price) public {
        vm.assume(price > 0 && price <= CADC_MAX_PRICE);

        bytes32 itemId = _createItem(address(cadc), price);

        Marketplace.DataItemView memory item = marketplace.getItemView(itemId);
        assertEq(item.price, price);
        assertEq(item.paymentToken, address(cadc));
    }

    function testFuzz_updatePrice_acceptsValidUSDCPrice(uint256 price) public {
        vm.assume(price > 0 && price <= USDC_MAX_PRICE);
        bytes32 itemId = _createItem(address(usdc), 1);

        vm.prank(seller);
        marketplace.updatePrice(itemId, price);

        assertEq(marketplace.getItemView(itemId).price, price);
    }

    function testFuzz_updatePrice_acceptsValidCADCPrice(uint256 price) public {
        vm.assume(price > 0 && price <= CADC_MAX_PRICE);
        bytes32 itemId = _createItem(address(cadc), 1);

        vm.prank(seller);
        marketplace.updatePrice(itemId, price);

        assertEq(marketplace.getItemView(itemId).price, price);
    }

    function test_createItem_acceptsUSDCMaxBoundary() public {
        bytes32 itemId = _createItem(address(usdc), USDC_MAX_PRICE);

        assertEq(marketplace.getItemView(itemId).price, USDC_MAX_PRICE);
    }

    function test_createItem_acceptsCADCMaxBoundary() public {
        bytes32 itemId = _createItem(address(cadc), CADC_MAX_PRICE);

        assertEq(marketplace.getItemView(itemId).price, CADC_MAX_PRICE);
    }

    function test_updatePrice_acceptsUSDCMaxBoundary() public {
        bytes32 itemId = _createItem(address(usdc), 1);

        vm.prank(seller);
        marketplace.updatePrice(itemId, USDC_MAX_PRICE);

        assertEq(marketplace.getItemView(itemId).price, USDC_MAX_PRICE);
    }

    function test_updatePrice_acceptsCADCMaxBoundary() public {
        bytes32 itemId = _createItem(address(cadc), 1);

        vm.prank(seller);
        marketplace.updatePrice(itemId, CADC_MAX_PRICE);

        assertEq(marketplace.getItemView(itemId).price, CADC_MAX_PRICE);
    }

    function test_createItem_revertsForZeroUSDCPrice() public {
        bytes32 itemId = _nextItemId();

        vm.prank(seller);
        vm.expectRevert(Marketplace.Marketplace__PriceMustBeGreaterThanZero.selector);
        marketplace.createItem(
            itemId, TITLE, DESC, seller, address(usdc), 0, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH
        );
    }

    function test_createItem_revertsForZeroCADCPrice() public {
        bytes32 itemId = _nextItemId();

        vm.prank(seller);
        vm.expectRevert(Marketplace.Marketplace__PriceMustBeGreaterThanZero.selector);
        marketplace.createItem(
            itemId, TITLE, DESC, seller, address(cadc), 0, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH
        );
    }

    function test_updatePrice_revertsForZeroUSDCPrice() public {
        bytes32 itemId = _createItem(address(usdc), 1);

        vm.prank(seller);
        vm.expectRevert(Marketplace.Marketplace__PriceMustBeGreaterThanZero.selector);
        marketplace.updatePrice(itemId, 0);
    }

    function test_updatePrice_revertsForZeroCADCPrice() public {
        bytes32 itemId = _createItem(address(cadc), 1);

        vm.prank(seller);
        vm.expectRevert(Marketplace.Marketplace__PriceMustBeGreaterThanZero.selector);
        marketplace.updatePrice(itemId, 0);
    }

    function test_createItem_revertsAboveUSDCMax() public {
        bytes32 itemId = _nextItemId();

        vm.prank(seller);
        vm.expectRevert(
            abi.encodeWithSelector(
                Marketplace.Marketplace__PriceExceedsMaximum.selector, USDC_MAX_PRICE + 1, USDC_MAX_PRICE
            )
        );
        marketplace.createItem(
            itemId, TITLE, DESC, seller, address(usdc), USDC_MAX_PRICE + 1, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH
        );
    }

    function test_createItem_revertsAboveCADCMax() public {
        bytes32 itemId = _nextItemId();

        vm.prank(seller);
        vm.expectRevert(
            abi.encodeWithSelector(
                Marketplace.Marketplace__PriceExceedsMaximum.selector, CADC_MAX_PRICE + 1, CADC_MAX_PRICE
            )
        );
        marketplace.createItem(
            itemId, TITLE, DESC, seller, address(cadc), CADC_MAX_PRICE + 1, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH
        );
    }

    function test_updatePrice_revertsAboveUSDCMax() public {
        bytes32 itemId = _createItem(address(usdc), 1);

        vm.prank(seller);
        vm.expectRevert(
            abi.encodeWithSelector(
                Marketplace.Marketplace__PriceExceedsMaximum.selector, USDC_MAX_PRICE + 1, USDC_MAX_PRICE
            )
        );
        marketplace.updatePrice(itemId, USDC_MAX_PRICE + 1);
    }

    function test_updatePrice_revertsAboveCADCMax() public {
        bytes32 itemId = _createItem(address(cadc), 1);

        vm.prank(seller);
        vm.expectRevert(
            abi.encodeWithSelector(
                Marketplace.Marketplace__PriceExceedsMaximum.selector, CADC_MAX_PRICE + 1, CADC_MAX_PRICE
            )
        );
        marketplace.updatePrice(itemId, CADC_MAX_PRICE + 1);
    }

    function _createItem(address paymentToken, uint256 price) internal returns (bytes32 itemId) {
        itemId = _nextItemId();
        vm.prank(seller);
        marketplace.createItem(
            itemId, TITLE, DESC, seller, paymentToken, price, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH
        );
    }

    function _nextItemId() internal returns (bytes32 itemId) {
        itemId = bytes32(idCounter);
        idCounter += 1;
    }
}
