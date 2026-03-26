// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Script, stdJson} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";
import {HelperConfig} from "./HelperConfig.s.sol";
import {Marketplace} from "../src/Marketplace.sol";

contract SeedMarketplace is Script {
    using stdJson for string;

    struct SeedItem {
        string listing_id;
        string title;
        string description;
        string price_atomic;
        string dataset_url;
        string dataset_hash;
        string signature_url;
        string signature_hash;
    }

    function run() external {
        address marketplaceAddress = vm.envAddress("MARKETPLACE_ADDRESS");
        _seed(marketplaceAddress);
    }

    function run(address marketplaceAddress) external {
        _seed(marketplaceAddress);
    }

    function _seed(address marketplaceAddress) internal {
        HelperConfig config = new HelperConfig();
        (uint256 deployKey,,,) = config.activeNetworkConfig();
        address seller = vm.addr(deployKey);

        Marketplace marketplace = Marketplace(marketplaceAddress);
        SeedItem[] memory items = _loadItems();

        vm.startBroadcast(deployKey);

        for (uint256 i; i < items.length; ++i) {
            SeedItem memory item = items[i];
            _createItem(
                marketplace,
                _uuidToBytes32(item.listing_id),
                seller,
                item.title,
                item.description,
                vm.parseUint(item.price_atomic),
                item.dataset_url,
                vm.parseBytes32(item.dataset_hash),
                item.signature_url,
                vm.parseBytes32(item.signature_hash)
            );
        }

        vm.stopBroadcast();

        console2.log("Seed completed for marketplace:", marketplaceAddress);
    }

    function _loadItems() internal returns (SeedItem[] memory items) {
        string memory manifestPath = string.concat(vm.projectRoot(), "/../shared/mock-marketplace-items.json");
        string[] memory cmd = new string[](3);
        cmd[0] = "bash";
        cmd[1] = "-lc";
        cmd[2] = string.concat(
            "jq -c '{listing_id:[.items[].listing_id],title:[.items[].title],description:[.items[].description],price_atomic:[.items[].price_atomic],dataset_url:[.items[].dataset_url],dataset_hash:[.items[].dataset_hash],signature_url:[.items[].signature_url],signature_hash:[.items[].signature_hash]}' ",
            manifestPath
        );

        string memory normalizedJson = string(vm.ffi(cmd));

        string[] memory listingIds = vm.parseJsonStringArray(normalizedJson, ".listing_id");
        string[] memory titles = vm.parseJsonStringArray(normalizedJson, ".title");
        string[] memory descriptions = vm.parseJsonStringArray(normalizedJson, ".description");
        string[] memory pricesAtomic = vm.parseJsonStringArray(normalizedJson, ".price_atomic");
        string[] memory datasetUrls = vm.parseJsonStringArray(normalizedJson, ".dataset_url");
        string[] memory datasetHashes = vm.parseJsonStringArray(normalizedJson, ".dataset_hash");
        string[] memory signatureUrls = vm.parseJsonStringArray(normalizedJson, ".signature_url");
        string[] memory signatureHashes = vm.parseJsonStringArray(normalizedJson, ".signature_hash");

        items = new SeedItem[](listingIds.length);
        for (uint256 i; i < listingIds.length; ++i) {
            items[i] = SeedItem({
                listing_id: listingIds[i],
                title: titles[i],
                description: descriptions[i],
                price_atomic: pricesAtomic[i],
                dataset_url: datasetUrls[i],
                dataset_hash: datasetHashes[i],
                signature_url: signatureUrls[i],
                signature_hash: signatureHashes[i]
            });
        }
    }

    function _uuidToBytes32(string memory listingId) internal pure returns (bytes32) {
        bytes memory source = bytes(listingId);
        bytes memory compact = new bytes(32);
        uint256 compactIndex;

        for (uint256 i; i < source.length; ++i) {
            if (source[i] == bytes1("-")) {
                continue;
            }
            compact[compactIndex] = source[i];
            compactIndex++;
        }

        bytes memory padded = bytes(string.concat("0x", string(compact), "00000000000000000000000000000000"));
        return vm.parseBytes32(string(padded));
    }

    function _createItem(
        Marketplace marketplace,
        bytes32 itemId,
        address seller,
        string memory title,
        string memory description,
        uint256 price,
        string memory datasetUrl,
        bytes32 datasetHash,
        string memory signatureUrl,
        bytes32 signatureHash
    ) internal {
        marketplace.createItem(
            itemId, title, description, seller, price, datasetUrl, datasetHash, signatureUrl, signatureHash
        );

        console2.log("Created item:");
        console2.logBytes32(itemId);
    }
}
