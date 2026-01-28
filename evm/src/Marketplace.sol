// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title BridgeMart Marketplace (single-chain now, CCIP-ready later)
 * @author Axel Sanchez (@Axeloooo)
 * @notice ETH purchases on one chain. Later: CCIP can call _purchase() after cross-chain funds arrive.
 */
contract Marketplace is Ownable, ReentrancyGuard {
    // ========= Errors =========
    error ItemDoesNotExist(uint256 itemId);
    error PriceMustBeGreaterThanZero();
    error DatasetUrlRequired();
    error SignatureUrlRequired();
    error InvalidPayment(uint256 required, uint256 provided);
    error AlreadyHasAccess(address buyer, uint256 itemId);
    error TransferFailed();
    error InvalidFeeBps(uint256 bps);
    error FeeRecipientRequired();
    error ItemFrozen(uint256 itemId);

    // ========= Storage =========

    struct DataItem {
        string title;
        string description;
        address seller;
        uint256 price; // wei

        string datasetUrl;
        bytes32 datasetHash;

        string signatureUrl;
        bytes32 signatureHash; // bytes32 sha256(compressed signature bytes) off-chain (recommended)

        bool exists;

        uint256 purchaseCount; // used to freeze metadata after first sale
        mapping(address => bool) accessList;
    }

    // View-only struct (no mappings)
    struct DataItemView {
        uint256 itemId;
        string title;
        string description;
        address seller;
        uint256 price;

        string datasetUrl;
        bytes32 datasetHash;

        string signatureUrl;
        bytes32 signatureHash;

        bool exists;
        uint256 purchaseCount;
    }

    uint256 public nextItemId;
    mapping(uint256 => DataItem) private items;

    // fee in basis points (bps): 100 = 1%, 250 = 2.5%, 10000 = 100%
    uint256 public feeBps;
    address public feeRecipient;

    // ========= Events =========
    event FeeConfigUpdated(uint256 oldFeeBps, uint256 newFeeBps, address oldRecipient, address newRecipient);

    event ItemCreated(
        uint256 indexed itemId,
        address indexed seller,
        uint256 price,
        string datasetUrl,
        bytes32 datasetHash,
        string signatureUrl,
        bytes32 signatureHash
    );

    event ItemPurchased(
        uint256 indexed itemId, address indexed buyer, uint256 pricePaid, uint256 feePaid, uint256 sellerPaid
    );

    event ItemFrozenAfterSale(uint256 indexed itemId);

    event DatasetUrlUpdated(uint256 indexed itemId, string oldUrl, string newUrl);
    event SignatureUpdated(uint256 indexed itemId, string oldUrl, string newUrl, bytes32 oldHash, bytes32 newHash);
    event PriceUpdated(uint256 indexed itemId, uint256 oldPrice, uint256 newPrice);

    // ========= Modifiers =========
    modifier onlyExistingItem(uint256 itemId) {
        if (!items[itemId].exists) revert ItemDoesNotExist(itemId);
        _;
    }

    modifier onlyIfNotFrozen(uint256 itemId) {
        if (items[itemId].purchaseCount > 0) revert ItemFrozen(itemId);
        _;
    }

    // ========= Constructor =========
    constructor(address initialOwner, address _feeRecipient, uint256 _feeBps) Ownable(initialOwner) {
        if (_feeRecipient == address(0)) revert FeeRecipientRequired();
        if (_feeBps > 10_000) revert InvalidFeeBps(_feeBps);
        feeRecipient = _feeRecipient;
        feeBps = _feeBps;
    }

    // ========= Admin =========
    /**
     *
     * @notice Set marketplace fee configuration
     *
     * @param _feeRecipient The address that will receive marketplace fees
     * @param _feeBps The fee in basis points (bps)
     */
    function setFeeConfig(address _feeRecipient, uint256 _feeBps) external onlyOwner {
        if (_feeRecipient == address(0)) revert FeeRecipientRequired();
        if (_feeBps > 10_000) revert InvalidFeeBps(_feeBps);

        address oldR = feeRecipient;
        uint256 oldB = feeBps;

        feeRecipient = _feeRecipient;
        feeBps = _feeBps;

        emit FeeConfigUpdated(oldB, _feeBps, oldR, _feeRecipient);
    }

    /**
     *
     * @notice Create a new dataset listing. For now onlyOwner (marketplace admin) creates items.
     *
     * @param title The title of the dataset
     * @param description The description of the dataset
     * @param seller The address of the dataset seller
     * @param price The price in wei
     * @param datasetUrl The URL of the dataset
     * @param datasetHash The hash of the dataset
     * @param signatureUrl The URL of the signature
     * @param signatureHash The hash of the signature
     */
    function createItem(
        string calldata title,
        string calldata description,
        address seller,
        uint256 price,
        string calldata datasetUrl,
        bytes32 datasetHash,
        string calldata signatureUrl,
        bytes32 signatureHash
    ) external onlyOwner returns (uint256 itemId) {
        if (price == 0) revert PriceMustBeGreaterThanZero();
        if (bytes(datasetUrl).length == 0) revert DatasetUrlRequired();
        if (bytes(signatureUrl).length == 0) revert SignatureUrlRequired();
        if (seller == address(0)) revert FeeRecipientRequired(); // reuse simple error

        itemId = nextItemId;
        nextItemId = itemId + 1;

        DataItem storage it = items[itemId];
        it.title = title;
        it.description = description;
        it.seller = seller;
        it.price = price;
        it.datasetUrl = datasetUrl;
        it.datasetHash = datasetHash;
        it.signatureUrl = signatureUrl;
        it.signatureHash = signatureHash;
        it.exists = true;

        emit ItemCreated(itemId, seller, price, datasetUrl, datasetHash, signatureUrl, signatureHash);
    }

    /**
     *
     * @notice Once an item is purchased once, we freeze it to prevent bait-and-switch.
     *
     * @param itemId The ID of the item to update
     * @param newDatasetUrl The new URL of the dataset
     */
    function updateDatasetUrl(uint256 itemId, string calldata newDatasetUrl)
        external
        onlyOwner
        onlyExistingItem(itemId)
        onlyIfNotFrozen(itemId)
    {
        if (bytes(newDatasetUrl).length == 0) revert DatasetUrlRequired();
        DataItem storage it = items[itemId];
        string memory old = it.datasetUrl;
        it.datasetUrl = newDatasetUrl;
        emit DatasetUrlUpdated(itemId, old, newDatasetUrl);
    }

    /**
     *
     * @notice Updating signature changes what semantic search indexes; disallow after any purchase.
     *
     * @param itemId The ID of the item to update
     * @param newSignatureUrl The new URL of the signature
     * @param newSignatureHash The new hash of the signature
     */
    function updateSignature(uint256 itemId, string calldata newSignatureUrl, bytes32 newSignatureHash)
        external
        onlyOwner
        onlyExistingItem(itemId)
        onlyIfNotFrozen(itemId)
    {
        if (bytes(newSignatureUrl).length == 0) revert SignatureUrlRequired();
        DataItem storage it = items[itemId];

        string memory oldUrl = it.signatureUrl;
        bytes32 oldHash = it.signatureHash;

        it.signatureUrl = newSignatureUrl;
        it.signatureHash = newSignatureHash;

        emit SignatureUpdated(itemId, oldUrl, newSignatureUrl, oldHash, newSignatureHash);
    }

    /**
     *
     * @notice Update price of an item, only if not yet purchased.
     *
     * @param itemId The ID of the item to update
     * @param newPrice The new price of the item
     */
    function updatePrice(uint256 itemId, uint256 newPrice)
        external
        onlyOwner
        onlyExistingItem(itemId)
        onlyIfNotFrozen(itemId)
    {
        if (newPrice == 0) revert PriceMustBeGreaterThanZero();
        DataItem storage it = items[itemId];
        uint256 old = it.price;
        it.price = newPrice;
        emit PriceUpdated(itemId, old, newPrice);
    }

    // ========= Purchase (single chain now) =========
    /**
     * @notice Purchase an item by paying the exact amount (price + fee).
     *
     * @param itemId The ID of the item to purchase
     */
    function buyItem(uint256 itemId) external payable nonReentrant onlyExistingItem(itemId) {
        _purchase(itemId, msg.sender, msg.value);
    }

    /**
     *
     * @notice Internal purchase logic, can be called by CCIP handler later for cross-chain purchases.
     *
     * @dev Internal purchase path. Later CCIP receiver can call this after receiving bridged USDC (or ETH).
     *
     * @param itemId The ID of the item to purchase
     * @param buyer The address of the buyer
     * @param amountPaid The amount paid by the buyer
     */
    function _purchase(uint256 itemId, address buyer, uint256 amountPaid) internal {
        DataItem storage it = items[itemId];

        uint256 fee = (it.price * feeBps) / 10_000;
        uint256 totalPrice = it.price + fee;

        if (amountPaid != totalPrice) revert InvalidPayment(totalPrice, amountPaid);
        if (it.accessList[buyer]) revert AlreadyHasAccess(buyer, itemId);

        if (fee > 0) {
            (bool okFee,) = feeRecipient.call{value: fee}("");
            if (!okFee) revert TransferFailed();
        }

        (bool okSeller,) = it.seller.call{value: it.price}("");
        if (!okSeller) revert TransferFailed();

        it.accessList[buyer] = true;

        // Freeze after first purchase (integrity guarantee)
        it.purchaseCount += 1;
        if (it.purchaseCount == 1) emit ItemFrozenAfterSale(itemId);

        emit ItemPurchased(itemId, buyer, amountPaid, fee, it.price);
    }

    // ========= Views =========

    /**
     * @notice Check if a user has access to a specific item.
     *
     * @param itemId The ID of the item
     * @param user The address of the user
     * @return bool Whether the user has access
     */
    function hasAccess(uint256 itemId, address user) external view onlyExistingItem(itemId) returns (bool) {
        return items[itemId].accessList[user];
    }

    /**
     *
     * @notice Get the view data of an item.
     *
     * @param itemId The ID of the item
     */
    function getItemView(uint256 itemId) public view onlyExistingItem(itemId) returns (DataItemView memory) {
        DataItem storage it = items[itemId];
        return DataItemView({
            itemId: itemId,
            title: it.title,
            description: it.description,
            seller: it.seller,
            price: it.price,
            datasetUrl: it.datasetUrl,
            datasetHash: it.datasetHash,
            signatureUrl: it.signatureUrl,
            signatureHash: it.signatureHash,
            exists: it.exists,
            purchaseCount: it.purchaseCount
        });
    }

    /**
     * @notice Get all items in the marketplace.
     */
    function getAllItems() external view returns (DataItemView[] memory) {
        DataItemView[] memory out = new DataItemView[](nextItemId);
        for (uint256 i = 0; i < nextItemId; i++) {
            out[i] = getItemView(i);
        }
        return out;
    }
}
