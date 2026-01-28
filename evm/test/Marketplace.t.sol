// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Test} from "forge-std/Test.sol";
import {Marketplace} from "../src/Marketplace.sol";

contract MarketplaceTest is Test {
    Marketplace public marketplace;

    address owner = address(0xA11CE);
    address feeRecipient = address(0xFEE);
    address seller = address(0xB0B);
    address buyer = address(0xCAFE);

    uint256 feeBps = 250; // 2.5%

    // Sample item data
    string constant TITLE = "Test Dataset";
    string constant DESC = "Synthetic dataset for testing";
    string constant DATASET_URL = "ipfs://dataset";
    bytes32 constant DATASET_HASH = bytes32(uint256(0x1111));
    string constant SIG_URL = "ipfs://signature.json.gz";
    bytes32 constant SIG_HASH = bytes32(uint256(0x2222));
    uint256 constant PRICE = 1 ether;

    // ========= Events =========
    event FeeConfigUpdated(uint256 oldFeeBps, uint256 newFeeBps, address oldRecipient, address newRecipient);

    function setUp() public {
        // deploy as test contract; but owner is set in constructor
        marketplace = new Marketplace(owner, feeRecipient, feeBps);

        // fund buyer for purchase tests
        vm.deal(buyer, 100 ether);
    }

    // ========= Helpers =========

    /**
     * @notice Creates a default item and returns its ID
     */
    function _createDefaultItem() internal returns (uint256 itemId) {
        vm.prank(owner);
        itemId = marketplace.createItem(TITLE, DESC, seller, PRICE, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH);
    }

    /**
     * @notice Simulates a buyer purchasing an item
     */
    function _buy(uint256 itemId, address _buyer, uint256 value) internal {
        vm.prank(_buyer);
        marketplace.buyItem{value: value}(itemId);
    }

    // ========= Constructor =========

    /**
     * @notice Tests that constructor sets fee config and owner correctly
     */
    function test_constructor_setsFeeConfigAndOwner() public view {
        assertEq(marketplace.feeBps(), feeBps);
        assertEq(marketplace.feeRecipient(), feeRecipient);
        assertEq(marketplace.owner(), owner);
    }

    /**
     * @notice Tests that constructor reverts on invalid parameters
     */
    function test_constructor_revert_feeRecipientZero() public {
        vm.expectRevert(Marketplace.Marketplace__FeeRecipientRequired.selector);
        new Marketplace(owner, address(0), feeBps);
    }

    /**
     * @notice Tests that constructor reverts on invalid fee bps
     */
    function test_constructor_revert_invalidFeeBps() public {
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__InvalidFeeBps.selector, uint256(10001)));
        new Marketplace(owner, feeRecipient, 10001);
    }

    // ========= setFeeConfig =========

    /**
     * @notice Tests that only owner can call setFeeConfig
     */
    function test_setFeeConfig_onlyOwner() public {
        vm.prank(address(123));
        vm.expectRevert(); // Ownable: caller is not the owner (OZ revert string)
        marketplace.setFeeConfig(address(0xBEEF), 100);
    }

    /**
     * @notice Tests that setFeeConfig reverts on invalid parameters
     */
    function test_setFeeConfig_revert_feeRecipientZero() public {
        vm.prank(owner);
        vm.expectRevert(Marketplace.Marketplace__FeeRecipientRequired.selector);
        marketplace.setFeeConfig(address(0), 100);
    }

    /**
     * @notice Tests that setFeeConfig reverts on invalid fee bps
     */
    function test_setFeeConfig_revert_invalidFeeBps() public {
        vm.prank(owner);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__InvalidFeeBps.selector, uint256(10001)));
        marketplace.setFeeConfig(address(0xBEEF), 10001);
    }

    /**
     * @notice Tests that setFeeConfig updates state correctly
     */
    function test_setFeeConfig_updatesState() public {
        address newRecipient = address(0xBEEF);
        uint256 newBps = 500;

        vm.prank(owner);

        vm.expectEmit(true, false, false, false);
        emit FeeConfigUpdated(feeBps, newBps, feeRecipient, newRecipient);

        marketplace.setFeeConfig(newRecipient, newBps);

        assertEq(marketplace.feeRecipient(), newRecipient);
        assertEq(marketplace.feeBps(), newBps);
    }

    /**
     * @notice Tests that feeBps = 0 works correctly (no fees, seller receives all payment)
     */
    function test_setFeeConfig_zeroFee_sellerReceivesAll() public {
        // Set fee to 0%
        vm.prank(owner);
        marketplace.setFeeConfig(feeRecipient, 0);

        uint256 itemId = _createDefaultItem();

        uint256 feeBalBefore = feeRecipient.balance;
        uint256 sellerBalBefore = seller.balance;

        // Buy with zero fee means buyer pays only the price
        _buy(itemId, buyer, PRICE);

        // Verify seller receives full price and fee recipient receives nothing
        assertEq(feeRecipient.balance, feeBalBefore);
        assertEq(seller.balance, sellerBalBefore + PRICE);
        assertTrue(marketplace.hasAccess(itemId, buyer));
    }

    /**
     * @notice Tests that feeBps = 10000 (100%) works correctly (buyer pays 2x price: seller receives price, fee recipient receives price as fee)
     */
    function test_setFeeConfig_maxFee_feeRecipientReceivesAll() public {
        // Set fee to 100%
        vm.prank(owner);
        marketplace.setFeeConfig(feeRecipient, 10000);

        uint256 itemId = _createDefaultItem();

        uint256 totalPrice = PRICE + PRICE; // price + 100% fee

        uint256 feeBalBefore = feeRecipient.balance;
        uint256 sellerBalBefore = seller.balance;

        // Buy with 100% fee
        _buy(itemId, buyer, totalPrice);

        // Verify fee recipient receives price as fee and seller receives original price
        assertEq(feeRecipient.balance, feeBalBefore + PRICE);
        assertEq(seller.balance, sellerBalBefore + PRICE);
        assertTrue(marketplace.hasAccess(itemId, buyer));
    }

    /**
     * @notice Tests that high but valid feeBps (9999 = 99.99%) works correctly
     */
    function test_setFeeConfig_highFee_distributionCorrect() public {
        // Set fee to 99.99%
        uint256 highFeeBps = 9999;
        vm.prank(owner);
        marketplace.setFeeConfig(feeRecipient, highFeeBps);

        uint256 itemId = _createDefaultItem();

        uint256 fee = (PRICE * highFeeBps) / 10_000; // 99.99% of price
        uint256 totalPrice = PRICE + fee;

        uint256 feeBalBefore = feeRecipient.balance;
        uint256 sellerBalBefore = seller.balance;

        // Buy with high fee
        _buy(itemId, buyer, totalPrice);

        // Verify correct distribution
        assertEq(feeRecipient.balance, feeBalBefore + fee);
        assertEq(seller.balance, sellerBalBefore + PRICE);
        assertTrue(marketplace.hasAccess(itemId, buyer));
    }

    // ========= createItem =========

    /**
     * @notice Tests that only owner can create items
     */
    function test_createItem_onlyOwner() public {
        vm.prank(address(123));
        vm.expectRevert(); // Ownable: caller is not the owner
        marketplace.createItem(TITLE, DESC, seller, PRICE, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH);
    }

    /**
     * @notice Tests that createItem reverts on invalid parameters
     */
    function test_createItem_revert_priceZero() public {
        vm.prank(owner);
        vm.expectRevert(Marketplace.Marketplace__PriceMustBeGreaterThanZero.selector);
        marketplace.createItem(TITLE, DESC, seller, 0, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH);
    }

    /**
     * @notice Tests that createItem reverts on empty title
     */
    function test_createItem_revert_titleEmpty() public {
        vm.prank(owner);
        vm.expectRevert(Marketplace.Marketplace__TitleRequired.selector);
        marketplace.createItem("", DESC, seller, PRICE, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH);
    }

    /**
     * @notice Tests that createItem reverts on empty description
     */
    function test_createItem_revert_descriptionEmpty() public {
        vm.prank(owner);
        vm.expectRevert(Marketplace.Marketplace__DescriptionRequired.selector);
        marketplace.createItem(TITLE, "", seller, PRICE, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH);
    }

    /**
     * @notice Tests that createItem reverts on empty dataset URL
     */
    function test_createItem_revert_datasetUrlEmpty() public {
        vm.prank(owner);
        vm.expectRevert(Marketplace.Marketplace__DatasetUrlRequired.selector);
        marketplace.createItem(TITLE, DESC, seller, PRICE, "", DATASET_HASH, SIG_URL, SIG_HASH);
    }

    /**
     * @notice Tests that createItem reverts on empty signature URL
     */
    function test_createItem_revert_signatureUrlEmpty() public {
        vm.prank(owner);
        vm.expectRevert(Marketplace.Marketplace__SignatureUrlRequired.selector);
        marketplace.createItem(TITLE, DESC, seller, PRICE, DATASET_URL, DATASET_HASH, "", SIG_HASH);
    }

    /**
     * @notice Tests that createItem increments ID and stores view correctly
     */
    function test_createItem_incrementsIdAndStoresView() public {
        uint256 id0 = _createDefaultItem();
        assertEq(id0, 0);
        assertEq(marketplace.nextItemId(), 1);

        Marketplace.DataItemView memory v = marketplace.getItemView(id0);
        assertEq(v.itemId, id0);
        assertEq(v.title, TITLE);
        assertEq(v.description, DESC);
        assertEq(v.seller, seller);
        assertEq(v.price, PRICE);
        assertEq(v.datasetUrl, DATASET_URL);
        assertEq(v.datasetHash, DATASET_HASH);
        assertEq(v.signatureUrl, SIG_URL);
        assertEq(v.signatureHash, SIG_HASH);
        assertTrue(v.exists);
        assertEq(v.purchaseCount, 0);
    }

    /**
     * @notice Tests that createItem reverts on zero address seller
     */
    function test_createItem_revert_sellerZero() public {
        vm.prank(owner);
        vm.expectRevert(Marketplace.Marketplace__SellerRequired.selector);
        marketplace.createItem(TITLE, DESC, address(0), PRICE, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH);
    }

    /**
     * @notice Tests that createItem reverts when price exceeds MAX_PRICE
     */
    function test_createItem_revert_priceExceedsMaximum() public {
        uint256 maxPrice = marketplace.MAX_PRICE();
        uint256 tooHighPrice = maxPrice + 1;

        vm.prank(owner);
        vm.expectRevert(
            abi.encodeWithSelector(Marketplace.Marketplace__PriceExceedsMaximum.selector, tooHighPrice, maxPrice)
        );
        marketplace.createItem(TITLE, DESC, seller, tooHighPrice, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH);
    }

    /**
     * @notice Tests that createItem succeeds at MAX_PRICE
     */
    function test_createItem_succeedsAtMaxPrice() public {
        uint256 maxPrice = marketplace.MAX_PRICE();

        vm.prank(owner);
        uint256 itemId =
            marketplace.createItem(TITLE, DESC, seller, maxPrice, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH);

        Marketplace.DataItemView memory v = marketplace.getItemView(itemId);
        assertEq(v.price, maxPrice);
    }

    /**
     * @notice Tests that getAllItems returns all created items
     */
    function test_getAllItems_returnsAll() public {
        _createDefaultItem();

        vm.prank(owner);
        marketplace.createItem(
            "Another",
            "Two",
            address(0xD00D),
            2 ether,
            "ipfs://d2",
            bytes32(uint256(0x3333)),
            "ipfs://s2",
            bytes32(uint256(0x4444))
        );

        Marketplace.DataItemView[] memory all = marketplace.getAllItems();
        assertEq(all.length, 2);
        assertEq(all[0].itemId, 0);
        assertEq(all[1].itemId, 1);
    }

    /**
     * @notice Tests that getItems returns empty array when startId >= nextItemId
     */
    function test_getItems_emptyWhenStartIdBeyondRange() public {
        _createDefaultItem();

        Marketplace.DataItemView[] memory items = marketplace.getItems(5, 10);
        assertEq(items.length, 0);
    }

    /**
     * @notice Tests that getItems returns correct subset of items
     */
    function test_getItems_returnsCorrectSubset() public {
        // Create 5 items
        for (uint256 i = 0; i < 5; i++) {
            vm.prank(owner);
            marketplace.createItem(
                string(abi.encodePacked("Dataset ", i)),
                "Description",
                seller,
                (i + 1) * 1 ether,
                "ipfs://dataset",
                bytes32(i),
                "ipfs://sig",
                bytes32(i)
            );
        }

        // Get items 1-3 (3 items)
        Marketplace.DataItemView[] memory items = marketplace.getItems(1, 3);
        assertEq(items.length, 3);
        assertEq(items[0].itemId, 1);
        assertEq(items[1].itemId, 2);
        assertEq(items[2].itemId, 3);
        assertEq(items[0].price, 2 ether);
        assertEq(items[1].price, 3 ether);
        assertEq(items[2].price, 4 ether);
    }

    /**
     * @notice Tests that getItems handles count exceeding available items
     */
    function test_getItems_handlesCountExceedingAvailable() public {
        // Create 3 items
        for (uint256 i = 0; i < 3; i++) {
            _createDefaultItem();
        }

        // Request 10 items starting from 0, should return only 3
        Marketplace.DataItemView[] memory items = marketplace.getItems(0, 10);
        assertEq(items.length, 3);
        assertEq(items[0].itemId, 0);
        assertEq(items[1].itemId, 1);
        assertEq(items[2].itemId, 2);
    }

    /**
     * @notice Tests that getItems handles partial range at the end
     */
    function test_getItems_handlesPartialRange() public {
        // Create 5 items
        for (uint256 i = 0; i < 5; i++) {
            _createDefaultItem();
        }

        // Request 3 items starting from 3, should return only 2 (items 3 and 4)
        Marketplace.DataItemView[] memory items = marketplace.getItems(3, 3);
        assertEq(items.length, 2);
        assertEq(items[0].itemId, 3);
        assertEq(items[1].itemId, 4);
    }

    /**
     * @notice Tests that getItems with count=0 returns empty array
     */
    function test_getItems_zeroCount() public {
        _createDefaultItem();

        Marketplace.DataItemView[] memory items = marketplace.getItems(0, 0);
        assertEq(items.length, 0);
    }

    /**
     * @notice Tests that getItems can return single item
     */
    function test_getItems_singleItem() public {
        // Create 3 items
        for (uint256 i = 0; i < 3; i++) {
            _createDefaultItem();
        }

        // Get just item 1
        Marketplace.DataItemView[] memory items = marketplace.getItems(1, 1);
        assertEq(items.length, 1);
        assertEq(items[0].itemId, 1);
    }

    // ========= buyItem =========

    /**
     * @notice Tests that buyItem reverts when the item does not exist
     */
    function test_buyItem_revert_nonexistentItem() public {
        vm.prank(buyer);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__ItemDoesNotExist.selector, uint256(0)));
        marketplace.buyItem{value: PRICE}(0);
    }

    /**
     * @notice Tests that buyItem reverts when payment is incorrect (underpayment)
     */
    function test_buyItem_revert_wrongPayment() public {
        uint256 itemId = _createDefaultItem();

        uint256 fee = (PRICE * feeBps) / 10_000;
        uint256 totalPrice = PRICE + fee;

        vm.prank(buyer);
        vm.expectRevert(
            abi.encodeWithSelector(Marketplace.Marketplace__InvalidPayment.selector, totalPrice, uint256(PRICE))
        );
        marketplace.buyItem{value: PRICE}(itemId);
    }

    /**
     * @notice Tests that buyItem reverts when buyer overpays
     */
    function test_buyItem_revert_overpayment() public {
        uint256 itemId = _createDefaultItem();

        uint256 fee = (PRICE * feeBps) / 10_000;
        uint256 totalPrice = PRICE + fee;
        uint256 overpayment = totalPrice + 0.1 ether;

        vm.prank(buyer);
        vm.expectRevert(
            abi.encodeWithSelector(Marketplace.Marketplace__InvalidPayment.selector, totalPrice, overpayment)
        );
        marketplace.buyItem{value: overpayment}(itemId);
    }

    /**
     * @notice Tests that buyItem transfers fee and seller amount, sets access, and freezes item after first purchase
     */
    function test_buyItem_transfersFeeAndSellerAndSetsAccessAndFreezes() public {
        uint256 itemId = _createDefaultItem();

        uint256 fee = (PRICE * feeBps) / 10_000;
        uint256 totalPrice = PRICE + fee;

        uint256 feeBalBefore = feeRecipient.balance;
        uint256 sellerBalBefore = seller.balance;

        // buy
        _buy(itemId, buyer, totalPrice);

        // access
        bool has = marketplace.hasAccess(itemId, buyer);
        assertTrue(has);

        // payouts - seller receives full price, fee recipient receives fee
        assertEq(feeRecipient.balance, feeBalBefore + fee);
        assertEq(seller.balance, sellerBalBefore + PRICE);

        // frozen via purchaseCount
        Marketplace.DataItemView memory v = marketplace.getItemView(itemId);
        assertEq(v.purchaseCount, 1);
    }

    /**
     * @notice Tests that buyItem reverts if buyer already has access
     */
    function test_buyItem_revert_alreadyHasAccess() public {
        uint256 itemId = _createDefaultItem();
        uint256 fee = (PRICE * feeBps) / 10_000;
        uint256 totalPrice = PRICE + fee;
        _buy(itemId, buyer, totalPrice);

        vm.prank(buyer);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__AlreadyHasAccess.selector, buyer, itemId));
        marketplace.buyItem{value: totalPrice}(itemId);
    }

    /**
     * @notice Tests that multiple different buyers can successfully purchase the same item
     */
    function test_buyItem_multipleBuyers_success() public {
        uint256 itemId = _createDefaultItem();

        uint256 fee = (PRICE * feeBps) / 10_000;
        uint256 totalPrice = PRICE + fee;

        address buyer2 = address(0xBEEF);
        address buyer3 = address(0xDEAD);
        vm.deal(buyer2, 100 ether);
        vm.deal(buyer3, 100 ether);

        uint256 feeBalBefore = feeRecipient.balance;
        uint256 sellerBalBefore = seller.balance;

        // First buyer purchases
        _buy(itemId, buyer, totalPrice);

        // Verify first buyer has access and item is frozen
        assertTrue(marketplace.hasAccess(itemId, buyer));
        Marketplace.DataItemView memory v = marketplace.getItemView(itemId);
        assertEq(v.purchaseCount, 1);

        // Verify first payment distribution
        assertEq(feeRecipient.balance, feeBalBefore + fee);
        assertEq(seller.balance, sellerBalBefore + PRICE);

        // Second buyer purchases (item already frozen but should still succeed)
        _buy(itemId, buyer2, totalPrice);

        // Verify second buyer has access
        assertTrue(marketplace.hasAccess(itemId, buyer2));
        v = marketplace.getItemView(itemId);
        assertEq(v.purchaseCount, 2);

        // Verify second payment distribution
        assertEq(feeRecipient.balance, feeBalBefore + (fee * 2));
        assertEq(seller.balance, sellerBalBefore + (PRICE * 2));

        // Third buyer purchases
        _buy(itemId, buyer3, totalPrice);

        // Verify third buyer has access
        assertTrue(marketplace.hasAccess(itemId, buyer3));
        v = marketplace.getItemView(itemId);
        assertEq(v.purchaseCount, 3);

        // Verify third payment distribution
        assertEq(feeRecipient.balance, feeBalBefore + (fee * 3));
        assertEq(seller.balance, sellerBalBefore + (PRICE * 3));

        // Verify all three buyers have independent access
        assertTrue(marketplace.hasAccess(itemId, buyer));
        assertTrue(marketplace.hasAccess(itemId, buyer2));
        assertTrue(marketplace.hasAccess(itemId, buyer3));
    }

    // ========= update functions (freeze rules) =========

    /**
     * @notice Tests that update functions work before any purchase is made
     */
    function test_updateDatasetUrl_allowedBeforePurchase() public {
        uint256 itemId = _createDefaultItem();

        vm.prank(owner);
        marketplace.updateDatasetUrl(itemId, "ipfs://dataset-updated");

        Marketplace.DataItemView memory v = marketplace.getItemView(itemId);
        assertEq(v.datasetUrl, "ipfs://dataset-updated");
    }

    /**
     * @notice Tests that update functions work before any purchase is made
     */
    function test_updateSignature_allowedBeforePurchase() public {
        uint256 itemId = _createDefaultItem();

        vm.prank(owner);
        marketplace.updateSignature(itemId, "ipfs://sig-updated", bytes32(uint256(0x9999)));

        Marketplace.DataItemView memory v = marketplace.getItemView(itemId);
        assertEq(v.signatureUrl, "ipfs://sig-updated");
        assertEq(v.signatureHash, bytes32(uint256(0x9999)));
    }

    /**
     * @notice Tests that update functions work before any purchase is made
     */
    function test_updatePrice_allowedBeforePurchase() public {
        uint256 itemId = _createDefaultItem();

        vm.prank(owner);
        marketplace.updatePrice(itemId, 2 ether);

        Marketplace.DataItemView memory v = marketplace.getItemView(itemId);
        assertEq(v.price, 2 ether);
    }

    /**
     * @notice Tests that updatePrice reverts when new price exceeds MAX_PRICE
     */
    function test_updatePrice_revert_priceExceedsMaximum() public {
        uint256 itemId = _createDefaultItem();
        uint256 maxPrice = marketplace.MAX_PRICE();
        uint256 tooHighPrice = maxPrice + 1;

        vm.prank(owner);
        vm.expectRevert(
            abi.encodeWithSelector(Marketplace.Marketplace__PriceExceedsMaximum.selector, tooHighPrice, maxPrice)
        );
        marketplace.updatePrice(itemId, tooHighPrice);
    }

    /**
     * @notice Tests that updatePrice succeeds at MAX_PRICE
     */
    function test_updatePrice_succeedsAtMaxPrice() public {
        uint256 itemId = _createDefaultItem();
        uint256 maxPrice = marketplace.MAX_PRICE();

        vm.prank(owner);
        marketplace.updatePrice(itemId, maxPrice);

        Marketplace.DataItemView memory v = marketplace.getItemView(itemId);
        assertEq(v.price, maxPrice);
    }

    /**
     * @notice Tests that update functions revert after first purchase (item frozen)
     */
    function test_updates_revertAfterFirstPurchase_itemFrozen() public {
        uint256 itemId = _createDefaultItem();
        uint256 fee = (PRICE * feeBps) / 10_000;
        uint256 totalPrice = PRICE + fee;
        _buy(itemId, buyer, totalPrice);

        vm.prank(owner);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__ItemFrozen.selector, itemId));
        marketplace.updateDatasetUrl(itemId, "ipfs://nope");

        vm.prank(owner);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__ItemFrozen.selector, itemId));
        marketplace.updateSignature(itemId, "ipfs://nope", bytes32(uint256(123)));

        vm.prank(owner);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__ItemFrozen.selector, itemId));
        marketplace.updatePrice(itemId, 2 ether);
    }

    /**
     * @notice Tests that updateDatasetUrl reverts for nonexistent items
     */
    function test_updateDatasetUrl_revert_nonexistent() public {
        vm.prank(owner);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__ItemDoesNotExist.selector, uint256(0)));
        marketplace.updateDatasetUrl(0, "ipfs://dataset-updated");
    }

    /**
     * @notice Tests that updateSignature reverts for nonexistent items
     */
    function test_updateSignature_revert_nonexistent() public {
        vm.prank(owner);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__ItemDoesNotExist.selector, uint256(0)));
        marketplace.updateSignature(0, "ipfs://sig-updated", bytes32(uint256(0x9999)));
    }

    /**
     * @notice Tests that updatePrice reverts for nonexistent items
     */
    function test_updatePrice_revert_nonexistent() public {
        vm.prank(owner);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__ItemDoesNotExist.selector, uint256(0)));
        marketplace.updatePrice(0, 2 ether);
    }

    // ========= hasAccess / getItemView guards =========

    /**
     * @notice Tests that hasAccess and getItemView revert for nonexistent items
     */
    function test_getItemView_revert_nonexistent() public {
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__ItemDoesNotExist.selector, uint256(0)));
        marketplace.getItemView(0);
    }

    /**
     * @notice Tests that hasAccess and getItemView revert for nonexistent items
     */
    function test_hasAccess_revert_nonexistent() public {
        vm.expectRevert(abi.encodeWithSelector(Marketplace.Marketplace__ItemDoesNotExist.selector, uint256(0)));
        marketplace.hasAccess(0, buyer);
    }
}
