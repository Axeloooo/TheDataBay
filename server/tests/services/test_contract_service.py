from types import SimpleNamespace

import pytest
from web3 import Web3

from app.services import contract_service


def test_listing_id_to_bytes32():
    listing_id = "123e4567-e89b-12d3-a456-426614174000"
    b = contract_service.uuid_to_bytes32(listing_id)
    assert isinstance(b, bytes)
    assert len(b) == 32


def test_wallet_id_evm(settings):
    wid = contract_service.wallet_id(
        "evm", "0x0000000000000000000000000000000000000001", settings
    )
    assert isinstance(wid, bytes)
    assert len(wid) == 32


def test_wallet_id_evm_matches_solidity_payload_format(settings):
    address = "0xAbCDEFabcdefABCDEFabcdefABCDEFabcdefABCD"
    wid = contract_service.wallet_id("evm", address, settings)

    normalized_addr = Web3.to_hex(
        Web3.to_bytes(hexstr=Web3.to_checksum_address(address))
    )
    expected = Web3.keccak(text=f"eip155:{settings.chain_id}:{normalized_addr}")

    assert wid == expected


def test_get_purchased_items_by_wallet_non_evm_rejected(settings):
    with pytest.raises(contract_service.HTTPException) as exc_info:
        contract_service.get_purchased_items_by_wallet(
            wallet_type="solana",
            address="So11111111111111111111111111111111111111112",
            settings=settings,
        )

    assert exc_info.value.status_code == 400
    assert "only EVM wallets" in str(exc_info.value.detail)


def test_get_purchased_items_by_wallet_invalid_block_range(monkeypatch, settings):
    monkeypatch.setattr(contract_service, "_get_contract", lambda _settings: object())
    monkeypatch.setattr(
        contract_service,
        "_get_web3",
        lambda _settings: SimpleNamespace(eth=SimpleNamespace(block_number=123)),
    )

    with pytest.raises(contract_service.HTTPException) as exc_info:
        contract_service.get_purchased_items_by_wallet(
            wallet_type="evm",
            address="0x0000000000000000000000000000000000000001",
            settings=settings,
            start_block=10,
            end_block=9,
        )

    assert exc_info.value.status_code == 400
    assert "start_block cannot be greater than end_block" in str(exc_info.value.detail)


def test_get_purchased_items_by_wallet_pagination_and_deduping(monkeypatch, settings):
    item_a = bytes.fromhex("01" * 32)
    item_b = bytes.fromhex("02" * 32)
    item_c = bytes.fromhex("03" * 32)

    class FakeCall:
        def __init__(self, result):
            self._result = result

        def call(self):
            return self._result

    class FakeFunctions:
        def __init__(self, views):
            self._views = views

        def getItemView(self, item_id):
            return FakeCall(self._views[item_id])

    class FakeItemPurchasedEvent:
        def __init__(self, logs):
            self._logs = logs
            self.last_filters = None

        def get_logs(self, from_block, to_block, argument_filters):
            self.last_filters = {
                "from_block": from_block,
                "to_block": to_block,
                "argument_filters": argument_filters,
            }
            return self._logs

    class FakeEvents:
        def __init__(self, logs):
            self.item_purchased = FakeItemPurchasedEvent(logs)

        def ItemPurchased(self):
            return self.item_purchased

    logs = [
        SimpleNamespace(args={"itemId": item_a}),
        SimpleNamespace(args={"itemId": item_b}),
        SimpleNamespace(args={"itemId": item_a}),
        SimpleNamespace(args={"itemId": item_c}),
    ]

    item_views = {
        item_a: (
            item_a,
            "A",
            "desc",
            "0x0000000000000000000000000000000000000001",
            10,
            "ipfs://dataset-a",
            bytes.fromhex("aa" * 32),
            "ipfs://sig-a",
            bytes.fromhex("ab" * 32),
            True,
            1,
        ),
        item_b: (
            item_b,
            "B",
            "desc",
            "0x0000000000000000000000000000000000000001",
            20,
            "ipfs://dataset-b",
            bytes.fromhex("ba" * 32),
            "ipfs://sig-b",
            bytes.fromhex("bb" * 32),
            True,
            2,
        ),
        item_c: (
            item_c,
            "C",
            "desc",
            "0x0000000000000000000000000000000000000001",
            30,
            "ipfs://dataset-c",
            bytes.fromhex("ca" * 32),
            "ipfs://sig-c",
            bytes.fromhex("cb" * 32),
            True,
            3,
        ),
    }

    fake_contract = SimpleNamespace(
        events=FakeEvents(logs),
        functions=FakeFunctions(item_views),
    )

    monkeypatch.setattr(contract_service, "_get_contract", lambda _settings: fake_contract)
    monkeypatch.setattr(
        contract_service,
        "_get_web3",
        lambda _settings: SimpleNamespace(eth=SimpleNamespace(block_number=200)),
    )
    monkeypatch.setattr(
        contract_service,
        "_call_contract_read",
        lambda callable_obj, _operation: callable_obj.call(),
    )

    wallet_id_hex, items = contract_service.get_purchased_items_by_wallet(
        wallet_type="evm",
        address="0x0000000000000000000000000000000000000001",
        settings=settings,
        start_block=100,
        end_block=200,
        limit=1,
        offset=1,
    )

    # Logs reversed in service -> [C, A, B, A], deduped -> [C, A, B], offset=1 limit=1 -> [A]
    assert len(items) == 1
    assert items[0].id == "0x" + "01" * 32
    assert items[0].title == "A"
    assert wallet_id_hex.startswith("0x")
    assert len(wallet_id_hex) == 66

    filters = fake_contract.events.item_purchased.last_filters
    assert filters is not None
    assert filters["from_block"] == 100
    assert filters["to_block"] == 200
    assert filters["argument_filters"]["buyer"] == Web3.to_checksum_address(
        "0x0000000000000000000000000000000000000001"
    )
