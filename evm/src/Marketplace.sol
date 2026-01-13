// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

contract Marketplace is Ownable, ReentrancyGuard {
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
        string title;
        string description;
        address seller;
        uint256 price;

        string datasetUrl;
        bytes32 datasetHash;

        string signatureUrl;
        bytes32 signatureHash;

        bool exists;

        mapping(address => bool) accessList;
    }

    // ============ State Variables ============

    uint256 constant PLATFORM_FEE_BASIS_POINTS = 250;
    uint256 public nextItemId;
    mapping(uint256 => DataItem) private items;

    // ============ Events ============

    event ItemCreated(
        uint256 indexed itemId, string datasetUrl, uint256 price, bytes32 datasetHash, string signatureUrl
    );

    event AccessUrlUpdated(uint256 indexed itemId, string oldUrl, string newUrl);

    event PriceUpdated(uint256 indexed itemId, uint256 oldPrice, uint256 newPrice);

    event SignatureUpdated(
        uint256 indexed itemId,
        string oldSignatureUrl,
        string newSignatureUrl,
        bytes32 oldSignatureHash,
        bytes32 newSignatureHash
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
     * @param title The title of the dataset.
     * @param description The description of the dataset.
     * @param seller The seller's address.
     * @param price The price in wei.
     * @param datasetUrl The IPFS CID / URL of the dataset.
     * @param datasetHash The keccak256 hash of the dataset.
     * @param signatureUrl The URL of the signature vector.
     * @param signatureHash The keccak256 hash of the signature.
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
        if (price == 0) {
            revert Marketplace__PriceMustBeGreaterThanZero();
        }

        if (bytes(datasetUrl).length == 0) {
            revert Marketplace__AccessUrlRequired();
        }

        if (bytes(signatureUrl).length == 0) {
            revert Marketplace__SignatureHashRequired();
        }

        itemId = nextItemId;

        DataItem storage item = items[itemId];
        item.title = title;
        item.description = description;
        item.seller = seller;
        item.price = price;
        item.datasetUrl = datasetUrl;
        item.datasetHash = datasetHash;
        item.signatureUrl = signatureUrl;
        item.signatureHash = signatureHash;
        item.exists = true;

        nextItemId = itemId + 1;

        emit ItemCreated(itemId, datasetUrl, price, datasetHash, signatureUrl);
    }

    /**
     *
     * @notice Update the dataset URL of an item.
     *
     * @param itemId The ID of the item.
     * @param newDatasetUrl The new dataset URL/CID.
     */
    function updateDatasetUrl(uint256 itemId, string calldata newDatasetUrl)
        external
        onlyOwner
        onlyExistingItem(itemId)
    {
        if (bytes(newDatasetUrl).length == 0) {
            revert Marketplace__AccessUrlRequired();
        }

        DataItem storage item = items[itemId];
        string memory oldUrl = item.datasetUrl;

        item.datasetUrl = newDatasetUrl;

        emit AccessUrlUpdated(itemId, oldUrl, newDatasetUrl);
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
     * @notice Update the signature URL and hash of an item.
     *
     * @param itemId The ID of the item.
     * @param newSignatureUrl The new URL of the signature vector.
     * @param newSignatureHash The new hash of the signature.
     */
    function updateSignature(uint256 itemId, string calldata newSignatureUrl, bytes32 newSignatureHash)
        external
        onlyOwner
        onlyExistingItem(itemId)
    {
        DataItem storage item = items[itemId];

        string memory oldUrl = item.signatureUrl;
        bytes32 oldHash = item.signatureHash;

        item.signatureUrl = newSignatureUrl;
        item.signatureHash = newSignatureHash;

        emit SignatureUpdated(itemId, oldUrl, newSignatureUrl, oldHash, newSignatureHash);
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
            revert Marketplace__InsufficientPayment(item.price, msg.value);
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
     * @return title The title of the dataset.
     * @return description The description of the dataset.
     * @return seller The seller's address.
     * @return price The price in wei.
     * @return datasetUrl The IPFS CID / URL of the dataset.
     * @return datasetHash The keccak256 hash of the dataset.
     * @return signatureUrl The URL of the signature vector.
     * @return signatureHash The keccak256 hash of the signature.
     */
    function getItem(uint256 itemId)
        external
        view
        onlyExistingItem(itemId)
        returns (
            string memory title,
            string memory description,
            address seller,
            uint256 price,
            string memory datasetUrl,
            bytes32 datasetHash,
            string memory signatureUrl,
            bytes32 signatureHash
        )
    {
        DataItem storage item = items[itemId];
        return (
            item.title,
            item.description,
            item.seller,
            item.price,
            item.datasetUrl,
            item.datasetHash,
            item.signatureUrl,
            item.signatureHash
        );
    }

    /**
     * @notice Withdraw accumulated funds to the owner's address.
     */
    function withdraw() external onlyOwner nonReentrant {
        uint256 amount = address(this).balance;

        if (amount == 0) {
            revert Marketplace__NothingToWithdraw();
        }

        (bool success,) = owner().call{value: amount}("");

        if (!success) {
            revert Marketplace__WithdrawFailed();
        }

        emit Withdrawn(owner(), amount);
    }
}
