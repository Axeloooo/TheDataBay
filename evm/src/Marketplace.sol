// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";

/**
 * @title Ulenor Marketplace (single-chain now, CCIP-ready later)
 * @author Axel Sanchez (@Axeloooo)
 * @notice ERC-20 purchases on one chain. Later: CCIP can call _purchase() after cross-chain funds arrive.
 * @custom:security-contact security@ulenor.com
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
    error Marketplace__TokenNotAccepted(address token);
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
        uint256 price; // payment token atomic units
        address paymentToken;

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
        address paymentToken;
    }

    struct TokenConfig {
        bool enabled;
        uint8 decimals;
        uint256 maxPrice;
    }

    bytes32[] private itemIds;
    mapping(bytes32 => DataItem) private items;
    address[] private acceptedTokenList;
    mapping(address => TokenConfig) public acceptedTokens;

    // fee in basis points (bps): 100 = 1%, 250 = 2.5%, 10000 = 100%
    uint256 public feeBps;
    address public feeRecipient;

    // ========= Events =========
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
     * @param initialPaymentToken The initial accepted token address used for settlement
     * @param initialTokenDecimals The initial accepted token decimals
     * @param initialTokenMaxPrice The initial accepted token maximum listing price
     * @param _feeRecipient The address that will receive marketplace fees
     * @param _feeBps The fee in basis points (bps)
     */
    constructor(
        address initialOwner,
        address initialPaymentToken,
        uint8 initialTokenDecimals,
        uint256 initialTokenMaxPrice,
        address _feeRecipient,
        uint256 _feeBps
    ) Ownable(initialOwner) {
        if (initialOwner == address(0)) revert Marketplace__InitialOwnerRequired();
        if (initialPaymentToken == address(0)) revert Marketplace__SettlementTokenRequired();
        if (initialTokenMaxPrice == 0) revert Marketplace__PriceExceedsMaximum(0, 0);
        if (_feeRecipient == address(0)) revert Marketplace__FeeRecipientRequired();
        if (_feeBps > 10_000) revert Marketplace__InvalidFeeBps(_feeBps);
        feeRecipient = _feeRecipient;
        feeBps = _feeBps;

        _setTokenConfig(initialPaymentToken, true, initialTokenDecimals, initialTokenMaxPrice);
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
     * @notice Add or update an accepted payment token.
     * @dev Only standard, no-fee ERC-20 tokens are supported. Fee-on-transfer and rebasing tokens can underpay recipients
     *      relative to the listed atomic price.
     */
    function addAcceptedToken(address token, uint8 decimals, uint256 maxPrice) external onlyOwner {
        if (token == address(0)) revert Marketplace__SettlementTokenRequired();
        if (maxPrice == 0) revert Marketplace__PriceExceedsMaximum(0, 0);

        _setTokenConfig(token, true, decimals, maxPrice);
    }

    function setTokenEnabled(address token, bool enabled) external onlyOwner {
        TokenConfig storage config = acceptedTokens[token];
        if (config.maxPrice == 0) revert Marketplace__TokenNotAccepted(token);

        config.enabled = enabled;
        emit TokenConfigUpdated(token, enabled, config.decimals, config.maxPrice);
    }

    /**
     *
     * @notice Create a new dataset listing.
     *
     * @param title The title of the dataset
     * @param description The description of the dataset
     * @param seller The address of the dataset seller
     * @param paymentToken The accepted ERC-20 token used for payment
     * @param price The price in payment token atomic units
     * @param datasetUrl The URL of the dataset
     * @param datasetHash The hash of the dataset
     * @param signatureUrl The URL of the signature
     * @param signatureHash The hash of the signature
     *
     * @return createdItemId The ID of the created item
     */
    function createItem(
        bytes32 itemId,
        string memory title,
        string memory description,
        address seller,
        address paymentToken,
        uint256 price,
        string memory datasetUrl,
        bytes32 datasetHash,
        string memory signatureUrl,
        bytes32 signatureHash
    ) external returns (bytes32 createdItemId) {
        _validateItemText(title, description);
        _validateItemPrice(paymentToken, price);
        _validateItemArtifacts(datasetUrl);
        _validateNewItemSellerAndId(itemId, seller);
        _storeItemSaleTerms(itemId, title, description, seller, paymentToken, price);
        _storeItemArtifacts(itemId, datasetUrl, datasetHash, signatureUrl, signatureHash);
        _markItemCreated(itemId);
        _emitItemCreated(itemId, seller, paymentToken, price, datasetUrl, datasetHash, signatureUrl, signatureHash);
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
        DataItem storage it = items[itemId];
        uint256 maxPrice = _enabledTokenMaxPrice(it.paymentToken);
        if (newPrice > maxPrice) revert Marketplace__PriceExceedsMaximum(newPrice, maxPrice);
        uint256 old = it.price;
        it.price = newPrice;
        emit PriceUpdated(itemId, old, newPrice);
    }

    // ========= Purchase (single chain now) =========
    /**
     * @notice Purchase an item by transferring the listing token (price + fee) from the buyer.
     *
     * @param itemId The ID of the item to purchase
     */
    function buyItem(bytes32 itemId) external nonReentrant onlyExistingItem(itemId) {
        _purchase(itemId, msg.sender);
    }

    function grantAccess(bytes32 itemId, bytes32 walletId) external onlyOwner onlyExistingItem(itemId) {
        DataItem storage it = items[itemId];
        if (it.accessList[walletId]) revert Marketplace__AlreadyHasAccess(walletId, itemId);
        it.accessList[walletId] = true;
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
            purchaseCount: it.purchaseCount,
            paymentToken: it.paymentToken
        });
    }

    function acceptedTokenCount() external view returns (uint256 count) {
        count = acceptedTokenList.length;
    }

    function acceptedTokenAt(uint256 index) external view returns (address token) {
        token = acceptedTokenList[index];
    }

    function getAcceptedTokens() external view returns (address[] memory tokens) {
        tokens = acceptedTokenList;
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

    /**
     *
     * @notice Internal purchase logic, can be called by CCIP handler later for cross-chain purchases.
     *
     * @dev Internal purchase path. Later CCIP receiver can call this after receiving bridged funds.
     *      Fee and totalPrice calculations are overflow-safe due to per-token max price enforcement.
     *      Follows checks-effects-interactions pattern: all state changes occur before external calls.
     *
     * @param itemId The ID of the item to purchase
     * @param buyer The address of the buyer
     */
    function _purchase(bytes32 itemId, address buyer) internal {
        DataItem storage it = items[itemId];
        if (buyer == it.seller) revert Marketplace__SellerCannotBuyOwnItem();
        _requireEnabledToken(it.paymentToken);
        IERC20 paymentToken = IERC20(it.paymentToken);

        uint256 fee = (it.price * feeBps) / 10_000;
        uint256 totalPrice = it.price + fee;
        uint256 allowance = paymentToken.allowance(buyer, address(this));
        if (allowance < totalPrice) revert Marketplace__InsufficientAllowance(totalPrice, allowance);
        uint256 balance = paymentToken.balanceOf(buyer);
        if (balance < totalPrice) revert Marketplace__InsufficientBalance(totalPrice, balance);

        bytes32 walletId = _walletIdForEvm(buyer);
        if (it.accessList[walletId]) revert Marketplace__AlreadyHasAccess(walletId, itemId);

        it.accessList[walletId] = true;
        it.purchaseCount += 1;

        if (fee > 0) {
            paymentToken.safeTransferFrom(buyer, feeRecipient, fee);
        }

        paymentToken.safeTransferFrom(buyer, it.seller, it.price);

        if (it.purchaseCount == 1) emit ItemFrozenAfterSale(itemId);
        emit ItemPurchased(itemId, buyer, it.paymentToken, totalPrice, fee, it.price);
    }

    function _setTokenConfig(address token, bool enabled, uint8 decimals, uint256 maxPrice) internal {
        if (acceptedTokens[token].maxPrice == 0) {
            acceptedTokenList.push(token);
        }

        acceptedTokens[token] = TokenConfig({enabled: enabled, decimals: decimals, maxPrice: maxPrice});
        emit TokenConfigUpdated(token, enabled, decimals, maxPrice);
    }

    function _validateItemText(string memory title, string memory description) internal pure {
        if (bytes(title).length == 0) revert Marketplace__TitleRequired();
        if (bytes(description).length == 0) revert Marketplace__DescriptionRequired();
    }

    function _validateItemPrice(address paymentToken, uint256 price) internal view {
        if (price == 0) revert Marketplace__PriceMustBeGreaterThanZero();
        uint256 maxPrice = _enabledTokenMaxPrice(paymentToken);
        if (price > maxPrice) revert Marketplace__PriceExceedsMaximum(price, maxPrice);
    }

    function _validateItemArtifacts(string memory datasetUrl) internal pure {
        if (bytes(datasetUrl).length == 0) revert Marketplace__DatasetUrlRequired();
    }

    function _validateNewItemSellerAndId(bytes32 itemId, address seller) internal view {
        if (seller == address(0) || seller != msg.sender) revert Marketplace__SellerRequired();
        if (items[itemId].exists) revert Marketplace__ItemAlreadyExists(itemId);
    }

    function _storeItemSaleTerms(
        bytes32 itemId,
        string memory title,
        string memory description,
        address seller,
        address paymentToken,
        uint256 price
    ) internal {
        DataItem storage it = items[itemId];
        it.title = title;
        it.description = description;
        it.seller = seller;
        it.price = price;
        it.paymentToken = paymentToken;
    }

    function _storeItemArtifacts(
        bytes32 itemId,
        string memory datasetUrl,
        bytes32 datasetHash,
        string memory signatureUrl,
        bytes32 signatureHash
    ) internal {
        DataItem storage it = items[itemId];
        it.datasetUrl = datasetUrl;
        it.datasetHash = datasetHash;
        it.signatureUrl = signatureUrl;
        it.signatureHash = signatureHash;
    }

    function _markItemCreated(bytes32 itemId) internal {
        DataItem storage it = items[itemId];
        it.exists = true;

        itemIds.push(itemId);
    }

    function _emitItemCreated(
        bytes32 itemId,
        address seller,
        address paymentToken,
        uint256 price,
        string memory datasetUrl,
        bytes32 datasetHash,
        string memory signatureUrl,
        bytes32 signatureHash
    ) internal {
        emit ItemCreated(itemId, seller, paymentToken, price, datasetUrl, datasetHash, signatureUrl, signatureHash);
    }

    function _enabledTokenMaxPrice(address token) internal view returns (uint256 maxPrice) {
        TokenConfig storage config = acceptedTokens[token];
        if (!config.enabled) revert Marketplace__TokenNotAccepted(token);
        maxPrice = config.maxPrice;
    }

    function _requireEnabledToken(address token) internal view {
        if (!acceptedTokens[token].enabled) revert Marketplace__TokenNotAccepted(token);
    }

    function _walletIdForEvm(address user) internal view returns (bytes32) {
        string memory chainStr = Strings.toString(block.chainid);
        string memory addrStr = Strings.toHexString(uint160(user), 20);
        return keccak256(abi.encodePacked("eip155:", chainStr, ":", addrStr));
    }
}
