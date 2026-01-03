// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

contract Marketplace is Ownable {
    // ============ Errors ============

    error Marketplace__ItemDoesNotExist(uint256 itemId);
    error Marketplace__InsufficientPayment(uint256 required, uint256 provided);
    error Marketplace__PriceMustBeGreaterThanZero();
    error Marketplace__AccessUrlRequired();
    error Marketplace__SignatureHashRequired();
    error Marketplace__AlreadyHasAccess(address user, uint256 itemId);
    error Marketplace__NothingToWithdraw();
    error Marketplace__WithdrawFailed();

    // ============ Structs ============

    struct DataItem {
        address seller; // Address of the seller NEW
        string accessUrl; // IPFS CID / URL of the dataset
        uint256 price; // Price in wei (1 ETH = 10^18 wei)
        bytes32 signatureHash;
        string signatureVectorUri; // URI of the embedding vector stored off-chain (e.g., IPFS)
        bool exists;
        mapping(address => bool) accessList; // Review access control and check IPFS access control capabilities
    }

    // ============ State Variables ============

    uint256 constant PLATFORM_FEE_BASIS_POINTS = 250; // 2.5% platform fee NEW
    uint256 public nextItemId;
    mapping(uint256 => DataItem) private items;

    // ============ Events ============

    event ItemCreated(
        uint256 indexed itemId, string accessUrl, uint256 price, bytes32 signatureHash, string signatureVectorUri
    );

    event AccessUrlUpdated(uint256 indexed itemId, string oldUrl, string newUrl);

    event PriceUpdated(uint256 indexed itemId, uint256 oldPrice, uint256 newPrice);

    event SignatureUpdated(
        uint256 indexed itemId,
        bytes32 oldSignatureHash,
        bytes32 newSignatureHash,
        string oldSignatureVectorUri,
        string newSignatureVectorUri
    );

    event ItemPurchased(uint256 indexed itemId, address indexed buyer, uint256 pricePaid);

    event Withdrawn(address indexed to, uint256 amount);

    // ============ Modifiers ============

    modifier onlyExistingItem(uint256 itemId) {
        if (!items[itemId].exists) {
            revert Marketplace__ItemDoesNotExist(itemId);
        }
        _;
    }

    // ============ Constructor ============

    constructor(address initialOwner) Ownable(initialOwner) {}

    /**
     *
     * @notice Create a new data item in the marketplace.
     *
     * @param accessUrl The IPFS CID / URL of the dataset.
     * @param price The price in wei.
     * @param signatureHash The keccak256 hash of the embedding vector.
     * @param signatureVectorUri The URI of the embedding vector.
     */
    function createItem(
        string calldata accessUrl,
        uint256 price,
        bytes32 signatureHash,
        string calldata signatureVectorUri
    ) external onlyOwner returns (uint256 itemId) {
        if (price <= 0) {
            revert Marketplace__PriceMustBeGreaterThanZero();
        }

        if (bytes(accessUrl).length == 0) {
            revert Marketplace__AccessUrlRequired();
        }

        if (bytes(signatureVectorUri).length == 0) {
            revert Marketplace__SignatureHashRequired();
        }

        itemId = nextItemId;

        DataItem storage item = items[itemId];
        item.accessUrl = accessUrl;
        item.price = price;
        item.signatureHash = signatureHash;
        item.signatureVectorUri = signatureVectorUri;
        item.exists = true;

        nextItemId = itemId + 1;

        emit ItemCreated(itemId, accessUrl, price, signatureHash, signatureVectorUri);
    }

    /**
     *
     * @notice Update the access URL of an item.
     *
     * @param itemId The ID of the item.
     * @param newAccessUrl The new access URL/CID.
     */
    function updateAccessUrl(uint256 itemId, string calldata newAccessUrl) external onlyOwner onlyExistingItem(itemId) {
        if (bytes(newAccessUrl).length == 0) {
            revert Marketplace__AccessUrlRequired();
        }

        DataItem storage item = items[itemId];
        string memory oldUrl = item.accessUrl;

        item.accessUrl = newAccessUrl;

        emit AccessUrlUpdated(itemId, oldUrl, newAccessUrl);
    }

    /**
     *
     * @notice Update the price of an item.
     *
     * @param itemId The ID of the item.
     * @param newPrice The new price in wei.
     */
    function updatePrice(uint256 itemId, uint256 newPrice) external onlyOwner onlyExistingItem(itemId) {
        if (newPrice <= 0) {
            revert Marketplace__PriceMustBeGreaterThanZero();
        }

        DataItem storage item = items[itemId];
        uint256 oldPrice = item.price;
        item.price = newPrice;

        emit PriceUpdated(itemId, oldPrice, newPrice);
    }

    /**
     *
     * @notice Update the signature hash and vector URI of an item.
     *
     * @param itemId The ID of the item.
     * @param newSignatureHash The new keccak256 hash of the embedding vector.
     * @param newSignatureVectorUri The new URI of the embedding vector.
     */
    function updateSignature(uint256 itemId, bytes32 newSignatureHash, string calldata newSignatureVectorUri)
        external
        onlyOwner
        onlyExistingItem(itemId)
    {
        DataItem storage item = items[itemId];

        bytes32 oldHash = item.signatureHash;
        string memory oldUri = item.signatureVectorUri;

        item.signatureHash = newSignatureHash;
        item.signatureVectorUri = newSignatureVectorUri;

        emit SignatureUpdated(itemId, oldHash, newSignatureHash, oldUri, newSignatureVectorUri);
    }

    /**
     *
     * @notice Purchase access to a specific item.
     *
     * @param itemId The ID of the item to purchase.
     */
    function buyItem(uint256 itemId) external payable nonReentrant onlyExistingItem(itemId) {
        DataItem storage item = items[itemId];

        if (msg.value != item.price) {
            revert Marketplace__IncorrectPaymentAmount();
        }

        if (item.accessList[msg.sender]) {
            revert Marketplace__AlreadyHasAccess(msg.sender, itemId);
        }

        item.accessList[msg.sender] = true;

        emit ItemPurchased(itemId, msg.sender, msg.value);
    }

    /**
     *
     * @notice Check if a user has access to a specific item.
     *
     * @param itemId The ID of the item.
     * @param user The address to check.
     */
    function hasAccess(uint256 itemId, address user) external view onlyExistingItem(itemId) returns (bool) {
        return items[itemId].accessList[user];
    }

    /**
     *
     * @notice Get item details.
     *
     * @param itemId The ID of the item.
     * @return accessUrl The IPFS CID / URL of the dataset.
     * @return price The price in wei.
     * @return signatureHash The keccak256 hash of the embedding vector.
     * @return signatureVectorUri The URI of the embedding vector.
     */
    function getItem(uint256 itemId)
        external
        view
        onlyExistingItem(itemId)
        returns (string memory accessUrl, uint256 price, bytes32 signatureHash, string memory signatureVectorUri)
    {
        DataItem storage item = items[itemId];
        return (item.accessUrl, item.price, item.signatureHash, item.signatureVectorUri);
    }

    /**
     * @notice Withdraw accumulated funds to the owner's address.
     */
    function withdraw() external onlyOwner nonReentrant {
        uint256 amount = address(this).balance;

        if (amount <= 0) {
            revert Marketplace__NothingToWithdraw();
        }

        (bool success,) = owner().call{value: amount}("");

        if (!success) {
            revert Marketplace__WithdrawFailed();
        }

        emit Withdrawn(owner(), amount);
    }
}
