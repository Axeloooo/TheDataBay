// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.19;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";
import {HelperConfig} from "./HelperConfig.s.sol";
import {Marketplace} from "../src/Marketplace.sol";

contract SeedMarketplace is Script {
    function run() external {
        address marketplaceAddress = vm.envAddress("MARKETPLACE_ADDRESS");
        _seed(marketplaceAddress);
    }

    function run(address marketplaceAddress) external {
        _seed(marketplaceAddress);
    }

    function _seed(address marketplaceAddress) internal {
        HelperConfig config = new HelperConfig();
        (uint256 deployKey,,) = config.activeNetworkConfig();
        address seller = vm.addr(deployKey);

        Marketplace marketplace = Marketplace(marketplaceAddress);

        vm.startBroadcast(deployKey);

        _createItem(
            marketplace,
            bytes16(0x0d5f3ea4f1544f0499d3524c00112233),
            seller,
            "Retail Transactions 2025",
            "Synthetic retail basket-level transactions for demand forecasting.",
            0.02 ether,
            "ipfs://bafybeiaretaildatasetenc",
            bytes32(uint256(keccak256("retail_dataset_hash_v1"))),
            "ipfs://bafybeiaretailsignature",
            bytes32(uint256(keccak256("retail_signature_hash_v1")))
        );

        _createItem(
            marketplace,
            bytes16(0x8be1b771e9ab4cb79e00a42f10445566),
            seller,
            "Cardio Clinical Cohort",
            "De-identified cardiovascular cohort for binary risk classification.",
            0.035 ether,
            "ipfs://bafybeibcardiodatasetenc",
            bytes32(uint256(keccak256("cardio_dataset_hash_v1"))),
            "ipfs://bafybeibcardiosignature",
            bytes32(uint256(keccak256("cardio_signature_hash_v1")))
        );

        _createItem(
            marketplace,
            bytes16(0xf3d9a2217aa14fdcb4cb00ef987799aa),
            seller,
            "SME Invoice Delays",
            "Invoice payment delay records for credit scoring and anomaly modeling.",
            0.015 ether,
            "ipfs://bafybeicsmedatasetenc",
            bytes32(uint256(keccak256("sme_dataset_hash_v1"))),
            "ipfs://bafybeicsmesignature",
            bytes32(uint256(keccak256("sme_signature_hash_v1")))
        );

        vm.stopBroadcast();

        console2.log("Seed completed for marketplace:", marketplaceAddress);
    }

    function _createItem(
        Marketplace marketplace,
        bytes16 uuidPrefix,
        address seller,
        string memory title,
        string memory description,
        uint256 price,
        string memory datasetUrl,
        bytes32 datasetHash,
        string memory signatureUrl,
        bytes32 signatureHash
    ) internal {
        bytes32 itemId = bytes32(uuidPrefix);

        marketplace.createItem(
            itemId,
            title,
            description,
            seller,
            price,
            datasetUrl,
            datasetHash,
            signatureUrl,
            signatureHash
        );

        console2.log("Created item:");
        console2.logBytes32(itemId);
    }
}
