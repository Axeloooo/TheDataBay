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
    string TITLE = "Test Dataset";
    string DESC = "Synthetic dataset for testing";
    string DATASET_URL = "ipfs://dataset";
    bytes32 DATASET_HASH = bytes32(uint256(0x1111));
    string SIG_URL = "ipfs://signature.json.gz";
    bytes32 SIG_HASH = bytes32(uint256(0x2222));
    uint256 PRICE = 1 ether;

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
        vm.expectRevert(Marketplace.FeeRecipientRequired.selector);
        new Marketplace(owner, address(0), feeBps);
    }

    /**
     * @notice Tests that constructor reverts on invalid fee bps
     */
    function test_constructor_revert_invalidFeeBps() public {
        vm.expectRevert(abi.encodeWithSelector(Marketplace.InvalidFeeBps.selector, uint256(10001)));
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
        vm.expectRevert(Marketplace.FeeRecipientRequired.selector);
        marketplace.setFeeConfig(address(0), 100);
    }

    /**
     * @notice Tests that setFeeConfig reverts on invalid fee bps
     */
    function test_setFeeConfig_revert_invalidFeeBps() public {
        vm.prank(owner);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.InvalidFeeBps.selector, uint256(10001)));
        marketplace.setFeeConfig(address(0xBEEF), 10001);
    }

    /**
     * @notice Tests that setFeeConfig updates state correctly
     */
    function test_setFeeConfig_updatesState() public {
        address newRecipient = address(0xBEEF);
        uint256 newBps = 500;

        vm.prank(owner);
        marketplace.setFeeConfig(newRecipient, newBps);

        assertEq(marketplace.feeRecipient(), newRecipient);
        assertEq(marketplace.feeBps(), newBps);
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
        vm.expectRevert(Marketplace.PriceMustBeGreaterThanZero.selector);
        marketplace.createItem(TITLE, DESC, seller, 0, DATASET_URL, DATASET_HASH, SIG_URL, SIG_HASH);
    }

    /**
     * @notice Tests that createItem reverts on empty dataset URL
     */
    function test_createItem_revert_datasetUrlEmpty() public {
        vm.prank(owner);
        vm.expectRevert(Marketplace.DatasetUrlRequired.selector);
        marketplace.createItem(TITLE, DESC, seller, PRICE, "", DATASET_HASH, SIG_URL, SIG_HASH);
    }

    /**
     * @notice Tests that createItem reverts on empty signature URL
     */
    function test_createItem_revert_signatureUrlEmpty() public {
        vm.prank(owner);
        vm.expectRevert(Marketplace.SignatureUrlRequired.selector);
        marketplace.createItem(TITLE, DESC, seller, PRICE, DATASET_URL, DATASET_HASH, "", SIG_HASH);
    }

    /**
     * @notice Tests that createItem reverts on zero seller address
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

    // ========= buyItem =========

    /**
     * @notice Tests that buyItem reverts when the item does not exist
     */
    function test_buyItem_revert_nonexistentItem() public {
        vm.prank(buyer);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.ItemDoesNotExist.selector, uint256(0)));
        marketplace.buyItem{value: PRICE}(0);
    }

    /**
     * @notice Tests that buyItem reverts when payment is incorrect
     */
    function test_buyItem_revert_wrongPayment() public {
        uint256 itemId = _createDefaultItem();

        vm.prank(buyer);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.InvalidPayment.selector, PRICE, uint256(PRICE - 1)));
        marketplace.buyItem{value: PRICE - 1}(itemId);
    }

    /**
     * @notice Tests that buyItem transfers fee and seller amount, sets access, and freezes item after first purchase
     */
    function test_buyItem_transfersFeeAndSellerAndSetsAccessAndFreezes() public {
        uint256 itemId = _createDefaultItem();

        uint256 fee = (PRICE * feeBps) / 10_000;
        uint256 sellerAmount = PRICE - fee;

        uint256 feeBalBefore = feeRecipient.balance;
        uint256 sellerBalBefore = seller.balance;

        // buy
        _buy(itemId, buyer, PRICE);

        // access
        bool has = marketplace.hasAccess(itemId, buyer);
        assertTrue(has);

        // payouts
        assertEq(feeRecipient.balance, feeBalBefore + fee);
        assertEq(seller.balance, sellerBalBefore + sellerAmount);

        // frozen via purchaseCount
        Marketplace.DataItemView memory v = marketplace.getItemView(itemId);
        assertEq(v.purchaseCount, 1);
    }

    /**
     * @notice Tests that buyItem reverts if buyer already has access
     */
    function test_buyItem_revert_alreadyHasAccess() public {
        uint256 itemId = _createDefaultItem();
        _buy(itemId, buyer, PRICE);

        vm.prank(buyer);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.AlreadyHasAccess.selector, buyer, itemId));
        marketplace.buyItem{value: PRICE}(itemId);
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
     * @notice Tests that update functions revert after first purchase (item frozen)
     */
    function test_updates_revertAfterFirstPurchase_itemFrozen() public {
        uint256 itemId = _createDefaultItem();
        _buy(itemId, buyer, PRICE);

        vm.prank(owner);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.ItemFrozen.selector, itemId));
        marketplace.updateDatasetUrl(itemId, "ipfs://nope");

        vm.prank(owner);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.ItemFrozen.selector, itemId));
        marketplace.updateSignature(itemId, "ipfs://nope", bytes32(uint256(123)));

        vm.prank(owner);
        vm.expectRevert(abi.encodeWithSelector(Marketplace.ItemFrozen.selector, itemId));
        marketplace.updatePrice(itemId, 2 ether);
    }

    // ========= hasAccess / getItemView guards =========

    /**
     * @notice Tests that hasAccess and getItemView revert for nonexistent items
     */
    function test_getItemView_revert_nonexistent() public {
        vm.expectRevert(abi.encodeWithSelector(Marketplace.ItemDoesNotExist.selector, uint256(0)));
        marketplace.getItemView(0);
    }

    /**
     * @notice Tests that hasAccess and getItemView revert for nonexistent items
     */
    function test_hasAccess_revert_nonexistent() public {
        vm.expectRevert(abi.encodeWithSelector(Marketplace.ItemDoesNotExist.selector, uint256(0)));
        marketplace.hasAccess(0, buyer);
    }
}
