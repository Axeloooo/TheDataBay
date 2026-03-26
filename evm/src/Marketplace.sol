// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";

/**
 * @title BridgeMart Marketplace (single-chain now, CCIP-ready later)
 * @author Axel Sanchez (@Axeloooo)
 * @notice USDC purchases on one chain. Later: CCIP can call _purchase() after cross-chain funds arrive.
 * @custom:security-contact security@bridgemart.com
 */
contract Marketplace is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ========= Errors =========
    error Marketplace__InitialOwnerRequired();
    error Marketplace__ItemDoesNotExist(bytes32 itemId);
    error Marketplace__ItemAlreadyExists(bytes32 itemId);
    error Marketplace__PriceMustBeGreaterThanZero();
    error Marketplace__PriceExceedsMaximum(uint256 price, uint256 maxPrice);
    error Marketplace__TitleRequired();
    error Marketplace__DescriptionRequired();
    error Marketplace__DatasetUrlRequired();
    error Marketplace__SignatureUrlRequired();
    error Marketplace__AlreadyHasAccess(bytes32 walletId, bytes32 itemId);
    error Marketplace__InvalidFeeBps(uint256 bps);
    error Marketplace__FeeRecipientRequired();
    error Marketplace__SettlementTokenRequired();
    error Marketplace__SellerRequired();
    error Marketplace__SellerCannotBuyOwnItem();
    error Marketplace__ItemFrozen(bytes32 itemId);
    error Marketplace__InsufficientAllowance(uint256 required, uint256 available);
    error Marketplace__InsufficientBalance(uint256 required, uint256 available);

    // ========= Storage =========

    struct DataItem {
        string title;
        string description;
        address seller;
        uint256 price; // USDC atomic units (6 decimals)

        string datasetUrl;
        bytes32 datasetHash;

        string signatureUrl;
        bytes32 signatureHash; // bytes32 sha256(compressed signature bytes) off-chain (recommended)

        bool exists;

        uint256 purchaseCount; // used to freeze metadata after first sale
        mapping(bytes32 => bool) accessList;
    }

    // View-only struct (no mappings)
    struct DataItemView {
        bytes32 itemId;
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

    bytes32[] private itemIds;
    mapping(bytes32 => DataItem) private items;

    // fee in basis points (bps): 100 = 1%, 250 = 2.5%, 10000 = 100%
    uint256 public feeBps;
    address public feeRecipient;
    IERC20 public immutable settlementToken;
    uint8 public constant SETTLEMENT_DECIMALS = 6;

    // Maximum price to prevent overflow in totalPrice calculation (price + fee).
    // Set to 1,000,000 USDC with 6 decimals, which leaves ample room for fee addition.
    uint256 public constant MAX_PRICE = 1_000_000 * 10 ** 6;

    // ========= Events =========
    event FeeConfigUpdated(uint256 oldFeeBps, uint256 newFeeBps, address oldRecipient, address newRecipient);

    event ItemCreated(
        bytes32 indexed itemId,
        address indexed seller,
        uint256 price,
        string datasetUrl,
        bytes32 datasetHash,
        string signatureUrl,
        bytes32 signatureHash
    );

    event ItemPurchased(
        bytes32 indexed itemId, address indexed buyer, uint256 pricePaid, uint256 feePaid, uint256 sellerPaid
    );

    event ItemFrozenAfterSale(bytes32 indexed itemId);

    event DatasetUrlUpdated(bytes32 indexed itemId, string oldUrl, string newUrl);
    event SignatureUpdated(bytes32 indexed itemId, string oldUrl, string newUrl, bytes32 oldHash, bytes32 newHash);
    event PriceUpdated(bytes32 indexed itemId, uint256 oldPrice, uint256 newPrice);

    // ========= Modifiers =========
    modifier onlyExistingItem(bytes32 itemId) {
        if (!items[itemId].exists) revert Marketplace__ItemDoesNotExist(itemId);
        _;
    }

    modifier onlyIfNotFrozen(bytes32 itemId) {
        if (items[itemId].purchaseCount > 0) revert Marketplace__ItemFrozen(itemId);
        _;
    }

    modifier onlySeller(bytes32 itemId) {
        if (items[itemId].seller != msg.sender) revert Marketplace__SellerRequired();
        _;
    }

    // ========= Constructor =========
    /**
     *
     * @notice Marketplace constructor
     *
     * @param initialOwner The address of the initial owner
     * @param _settlementToken The USDC token address used for settlement
     * @param _feeRecipient The address that will receive marketplace fees
     * @param _feeBps The fee in basis points (bps)
     */
    constructor(address initialOwner, address _settlementToken, address _feeRecipient, uint256 _feeBps)
        Ownable(initialOwner)
    {
        if (initialOwner == address(0)) revert Marketplace__InitialOwnerRequired();
        if (_settlementToken == address(0)) revert Marketplace__SettlementTokenRequired();
        if (_feeRecipient == address(0)) revert Marketplace__FeeRecipientRequired();
        if (_feeBps > 10_000) revert Marketplace__InvalidFeeBps(_feeBps);
        settlementToken = IERC20(_settlementToken);
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
        if (_feeRecipient == address(0)) revert Marketplace__FeeRecipientRequired();
        if (_feeBps > 10_000) revert Marketplace__InvalidFeeBps(_feeBps);

        address oldR = feeRecipient;
        uint256 oldB = feeBps;

        feeRecipient = _feeRecipient;
        feeBps = _feeBps;

        emit FeeConfigUpdated(oldB, _feeBps, oldR, _feeRecipient);
    }

    /**
     *
     * @notice Create a new dataset listing.
     *
     * @param title The title of the dataset
     * @param description The description of the dataset
     * @param seller The address of the dataset seller
     * @param price The price in USDC atomic units
     * @param datasetUrl The URL of the dataset
     * @param datasetHash The hash of the dataset
     * @param signatureUrl The URL of the signature
     * @param signatureHash The hash of the signature
     *
     * @return createdItemId The ID of the created item
     */
    function createItem(
        bytes32 itemId,
        string calldata title,
        string calldata description,
        address seller,
        uint256 price,
        string calldata datasetUrl,
        bytes32 datasetHash,
        string calldata signatureUrl,
        bytes32 signatureHash
    ) external returns (bytes32 createdItemId) {
        if (bytes(title).length == 0) revert Marketplace__TitleRequired();
        if (bytes(description).length == 0) revert Marketplace__DescriptionRequired();
        if (price == 0) revert Marketplace__PriceMustBeGreaterThanZero();
        if (price > MAX_PRICE) revert Marketplace__PriceExceedsMaximum(price, MAX_PRICE);
        if (bytes(datasetUrl).length == 0) revert Marketplace__DatasetUrlRequired();
        if (bytes(signatureUrl).length == 0) revert Marketplace__SignatureUrlRequired();
        if (seller == address(0) || seller != msg.sender) revert Marketplace__SellerRequired();
        if (items[itemId].exists) revert Marketplace__ItemAlreadyExists(itemId);

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

        itemIds.push(itemId);

        emit ItemCreated(itemId, seller, price, datasetUrl, datasetHash, signatureUrl, signatureHash);
        createdItemId = itemId;
    }

    /**
     *
     * @notice Once an item is purchased once, we freeze it to prevent bait-and-switch.
     *
     * @param itemId The ID of the item to update
     * @param newDatasetUrl The new URL of the dataset
     */
    function updateDatasetUrl(bytes32 itemId, string calldata newDatasetUrl)
        external
        onlySeller(itemId)
        onlyExistingItem(itemId)
        onlyIfNotFrozen(itemId)
    {
        if (bytes(newDatasetUrl).length == 0) revert Marketplace__DatasetUrlRequired();
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
    function updateSignature(bytes32 itemId, string calldata newSignatureUrl, bytes32 newSignatureHash)
        external
        onlySeller(itemId)
        onlyExistingItem(itemId)
        onlyIfNotFrozen(itemId)
    {
        if (bytes(newSignatureUrl).length == 0) revert Marketplace__SignatureUrlRequired();
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
    function updatePrice(bytes32 itemId, uint256 newPrice)
        external
        onlySeller(itemId)
        onlyExistingItem(itemId)
        onlyIfNotFrozen(itemId)
    {
        if (newPrice == 0) revert Marketplace__PriceMustBeGreaterThanZero();
        if (newPrice > MAX_PRICE) revert Marketplace__PriceExceedsMaximum(newPrice, MAX_PRICE);
        DataItem storage it = items[itemId];
        uint256 old = it.price;
        it.price = newPrice;
        emit PriceUpdated(itemId, old, newPrice);
    }

    // ========= Purchase (single chain now) =========
    /**
     * @notice Purchase an item by transferring USDC (price + fee) from the buyer.
     *
     * @param itemId The ID of the item to purchase
     */
    function buyItem(bytes32 itemId) external nonReentrant onlyExistingItem(itemId) {
        _purchase(itemId, msg.sender);
    }

    /**
     *
     * @notice Internal purchase logic, can be called by CCIP handler later for cross-chain purchases.
     *
     * @dev Internal purchase path. Later CCIP receiver can call this after receiving bridged USDC.
     *      Fee and totalPrice calculations are overflow-safe due to MAX_PRICE enforcement.
     *      Follows checks-effects-interactions pattern: all state changes occur before external calls.
     *
     * @param itemId The ID of the item to purchase
     * @param buyer The address of the buyer
     */
    function _purchase(bytes32 itemId, address buyer) internal {
        DataItem storage it = items[itemId];
        if (buyer == it.seller) revert Marketplace__SellerCannotBuyOwnItem();

        uint256 fee = (it.price * feeBps) / 10_000;
        uint256 totalPrice = it.price + fee;
        uint256 allowance = settlementToken.allowance(buyer, address(this));
        if (allowance < totalPrice) revert Marketplace__InsufficientAllowance(totalPrice, allowance);
        uint256 balance = settlementToken.balanceOf(buyer);
        if (balance < totalPrice) revert Marketplace__InsufficientBalance(totalPrice, balance);

        bytes32 walletId = _walletIdForEvm(buyer);
        if (it.accessList[walletId]) revert Marketplace__AlreadyHasAccess(walletId, itemId);

        it.accessList[walletId] = true;
        it.purchaseCount += 1;

        if (fee > 0) {
            settlementToken.safeTransferFrom(buyer, feeRecipient, fee);
        }

        settlementToken.safeTransferFrom(buyer, it.seller, it.price);

        if (it.purchaseCount == 1) emit ItemFrozenAfterSale(itemId);
        emit ItemPurchased(itemId, buyer, totalPrice, fee, it.price);
    }

    // ========= Views =========

    /**
     * @notice Check if a walletId has access to a specific item.
     *
     * @param itemId The ID of the item
     * @param walletId The wallet identifier (bytes32)
     *
     * @return bool Whether the walletId has access
     */
    function hasAccess(bytes32 itemId, bytes32 walletId) external view onlyExistingItem(itemId) returns (bool) {
        return items[itemId].accessList[walletId];
    }

    /**
     *
     * @notice Get the view data of an item.
     *
     * @param itemId The ID of the item
     *
     * @return DataItemView The view data of the item
     */
    function getItemView(bytes32 itemId) public view onlyExistingItem(itemId) returns (DataItemView memory) {
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
     *
     * @dev WARNING: This function can consume high gas as the marketplace grows.
     *      Intended for off-chain queries (static calls) only. For on-chain or large datasets, use getItems() with pagination.
     *      Only returns items that exist (items[i].exists == true).
     *
     * @return DataItemView[] An array of all item views
     */
    function getAllItems() external view returns (DataItemView[] memory) {
        uint256 count = itemIds.length;
        DataItemView[] memory out = new DataItemView[](count);
        for (uint256 i = 0; i < count; i++) {
            out[i] = getItemView(itemIds[i]);
        }
        return out;
    }

    /**
     * @notice Get a paginated list of items from the marketplace.
     *
     * @dev Returns items by index in the itemIds array.
     *
     * @param start The starting index (inclusive)
     * @param count The maximum number of items to return
     *
     * @return DataItemView[] An array of item views
     */
    function getItems(uint256 start, uint256 count) external view returns (DataItemView[] memory) {
        uint256 total = itemIds.length;
        if (start >= total) {
            return new DataItemView[](0);
        }

        uint256 end = start + count;
        if (end > total) {
            end = total;
        }

        DataItemView[] memory out = new DataItemView[](end - start);
        uint256 index = 0;

        for (uint256 i = start; i < end; i++) {
            out[index] = getItemView(itemIds[i]);
            index++;
        }

        return out;
    }

    function grantAccess(bytes32 itemId, bytes32 walletId) external onlyOwner onlyExistingItem(itemId) {
        DataItem storage it = items[itemId];
        if (it.accessList[walletId]) revert Marketplace__AlreadyHasAccess(walletId, itemId);
        it.accessList[walletId] = true;
    }

    function _walletIdForEvm(address user) internal view returns (bytes32) {
        string memory chainStr = Strings.toString(block.chainid);
        string memory addrStr = Strings.toHexString(uint160(user), 20);
        return keccak256(abi.encodePacked("eip155:", chainStr, ":", addrStr));
    }
}
