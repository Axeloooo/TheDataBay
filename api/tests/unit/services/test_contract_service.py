import json
from types import SimpleNamespace

import pytest
from hexbytes import HexBytes
from web3 import Web3
from web3.datastructures import AttributeDict

from app.contracts import service as contract_service

LISTING_ID = "123e4567-e89b-12d3-a456-426614174000"


def test_listing_id_to_bytes32():
    listing_id = "123e4567-e89b-12d3-a456-426614174000"
    b = contract_service.uuid_to_bytes32(listing_id)
    assert isinstance(b, bytes)
    assert len(b) == 32


def test_listing_id_to_bytes32_rejects_invalid_uuid():
    with pytest.raises(contract_service.HTTPException) as exc_info:
        contract_service.uuid_to_bytes32("not-a-uuid")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid id UUID"


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


def test_wallet_id_invalid_evm_address_raises_bad_request(settings):
    with pytest.raises(contract_service.HTTPException) as exc_info:
        contract_service.wallet_id("evm", "not-an-address", settings)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid EVM address provided"


def test_load_abi_reads_json_file(tmp_path):
    abi_path = tmp_path / "Marketplace.json"
    expected_abi = [{"type": "function", "name": "owner"}]
    abi_path.write_text(json.dumps(expected_abi))
    contract_service._load_abi.cache_clear()

    try:
        assert contract_service._load_abi(str(abi_path)) == expected_abi
    finally:
        contract_service._load_abi.cache_clear()


def test_load_abi_missing_file_raises_internal_config_error(tmp_path):
    abi_path = tmp_path / "missing.json"
    contract_service._load_abi.cache_clear()

    try:
        with pytest.raises(contract_service.HTTPException) as exc_info:
            contract_service._load_abi(str(abi_path))
    finally:
        contract_service._load_abi.cache_clear()

    assert exc_info.value.status_code == 500
    assert f"Contract ABI file not found at path: {abi_path}" in exc_info.value.detail


def test_load_abi_invalid_json_raises_internal_config_error(tmp_path):
    abi_path = tmp_path / "Marketplace.json"
    abi_path.write_text("{not-json")
    contract_service._load_abi.cache_clear()

    try:
        with pytest.raises(contract_service.HTTPException) as exc_info:
            contract_service._load_abi(str(abi_path))
    finally:
        contract_service._load_abi.cache_clear()

    assert exc_info.value.status_code == 500
    assert f"Contract ABI file is not valid JSON: {abi_path}" in exc_info.value.detail


@pytest.mark.parametrize(
    ("rpc_url", "expected"),
    [
        ("http://host.docker.internal:8545", "http://host.docker.internal:8545"),
        (
            "https://user:secret@example-rpc.invalid/v3/token?api_key=secret",
            "https://example-rpc.invalid",
        ),
        ("not-a-url", "<invalid RPC_URL>"),
    ],
)
def test_redact_rpc_url_strips_credentials_paths_and_queries(rpc_url, expected):
    assert contract_service._redact_rpc_url(rpc_url) == expected


def test_get_web3_unreachable_rpc_uses_redacted_detail(monkeypatch, settings):
    class FakeProvider:
        def __init__(self, rpc_url):
            self.rpc_url = rpc_url

    class FakeWeb3:
        HTTPProvider = FakeProvider

        def __init__(self, provider):
            self.provider = provider

        def is_connected(self):
            return False

    monkeypatch.setattr(contract_service, "Web3", FakeWeb3)
    secret_rpc_settings = settings.model_copy(
        update={
            "rpc_url": "https://user:secret@example-rpc.invalid/v3/token?api_key=secret"
        }
    )

    with pytest.raises(contract_service.HTTPException) as exc_info:
        contract_service._get_web3(secret_rpc_settings)

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "RPC node unreachable at https://example-rpc.invalid"
    assert "secret" not in exc_info.value.detail


def test_call_contract_read_translates_known_custom_error():
    class FailingCall:
        def call(self):
            raise RuntimeError("execution reverted: custom error 0xb3be6278")

    with pytest.raises(contract_service.HTTPException) as exc_info:
        contract_service._call_contract_read(FailingCall(), "getItemView")

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Item does not exist. operation=getItemView"


def test_call_contract_read_translates_unknown_custom_error_selector():
    class FailingCall:
        def call(self):
            raise RuntimeError("execution reverted: custom error 0xdeadbeef")

    with pytest.raises(contract_service.HTTPException) as exc_info:
        contract_service._call_contract_read(FailingCall(), "feeBps")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Contract reverted (0xdeadbeef). operation=feeBps"


def test_item_view_to_schema_includes_payment_token():
    item_id = bytes.fromhex("01" * 32)
    payment_token = "0x0000000000000000000000000000000000000002"

    item = contract_service._item_view_to_schema(
        (
            item_id,
            "Dataset",
            "desc",
            "0x0000000000000000000000000000000000000001",
            100,
            "ipfs://dataset",
            bytes.fromhex("11" * 32),
            "ipfs://signature",
            bytes.fromhex("22" * 32),
            True,
            0,
            payment_token,
        )
    )

    assert item.payment_token == payment_token
    assert item.price_atomic == "100"


def test_item_view_to_schema_decodes_web3_attribute_dict():
    item_id = bytes.fromhex("02" * 32)
    payment_token = "0x0000000000000000000000000000000000000002"

    item = contract_service._item_view_to_schema(
        AttributeDict(
            {
                "itemId": item_id,
                "title": "Dataset",
                "description": "desc",
                "seller": "0x0000000000000000000000000000000000000001",
                "price": 100,
                "datasetUrl": "ipfs://dataset",
                "datasetHash": bytes.fromhex("11" * 32),
                "signatureUrl": "ipfs://signature",
                "signatureHash": bytes.fromhex("22" * 32),
                "exists": True,
                "purchaseCount": 0,
                "paymentToken": payment_token,
            }
        )
    )

    assert item.id == Web3.to_hex(item_id)
    assert item.payment_token == payment_token
    assert item.price_atomic == "100"


def test_item_view_to_schema_preserves_empty_signature_url_mapping():
    item_id = bytes.fromhex("02" * 32)

    item = contract_service._item_view_to_schema(
        AttributeDict(
            {
                "itemId": item_id,
                "title": "Dataset",
                "description": "desc",
                "seller": "0x0000000000000000000000000000000000000001",
                "price": 100,
                "datasetUrl": "ipfs://dataset",
                "datasetHash": bytes.fromhex("11" * 32),
                "signatureUrl": "",
                "signatureHash": bytes(32),
                "exists": True,
                "purchaseCount": 0,
                "paymentToken": "0x0000000000000000000000000000000000000002",
            }
        )
    )

    assert item.signature_url == ""
    assert item.signature_hash == "0x" + "0" * 64


def test_item_view_to_schema_derives_cadc_from_unmapped_18_decimal_token(settings):
    item_id = bytes.fromhex("03" * 32)
    payment_token = Web3.to_checksum_address(
        "0x0000000000000000000000000000000000000003"
    )
    configured_settings = settings.model_copy(
        update={
            "usdc_token_address": "0x0000000000000000000000000000000000000002",
            "cadc_token_address": "",
        }
    )

    class FakeCall:
        def call(self):
            return (True, 18, 10**24)

    class FakeFunctions:
        def acceptedTokens(self, token):
            assert token == payment_token
            return FakeCall()

    item = contract_service._item_view_to_schema(
        AttributeDict(
            {
                "itemId": item_id,
                "title": "Dataset",
                "description": "desc",
                "seller": "0x0000000000000000000000000000000000000001",
                "price": 100,
                "datasetUrl": "ipfs://dataset",
                "datasetHash": bytes.fromhex("11" * 32),
                "signatureUrl": "ipfs://signature",
                "signatureHash": bytes.fromhex("22" * 32),
                "exists": True,
                "purchaseCount": 0,
                "paymentToken": payment_token,
            }
        ),
        settings=configured_settings,
        contract=SimpleNamespace(functions=FakeFunctions()),
        token_config_cache={},
    )

    assert item.settlement_currency == "CADC"
    assert item.settlement_decimals == 18


def test_item_view_to_schema_without_configured_payment_token_returns_usdc_fallback(settings):
    item_id = bytes.fromhex("04" * 32)
    payment_token = Web3.to_checksum_address(
        "0x0000000000000000000000000000000000000004"
    )
    unconfigured_settings = settings.model_copy(update={"usdc_token_address": ""})

    item = contract_service._item_view_to_schema(
        AttributeDict(
            {
                "itemId": item_id,
                "title": "Dataset",
                "description": "desc",
                "seller": "0x0000000000000000000000000000000000000001",
                "price": 100,
                "datasetUrl": "ipfs://dataset",
                "datasetHash": bytes.fromhex("11" * 32),
                "signatureUrl": "ipfs://signature",
                "signatureHash": bytes.fromhex("22" * 32),
                "exists": True,
                "purchaseCount": 0,
                "paymentToken": payment_token,
            }
        ),
        settings=unconfigured_settings,
    )

    assert item.settlement_currency == "USDC"
    assert item.settlement_decimals == 6


def test_settlement_currency_for_token_resolves_cadc_address(settings):
    cadc_address = "0x0000000000000000000000000000000000000099"
    configured_settings = settings.model_copy(
        update={"cadc_token_address": cadc_address}
    )

    result = contract_service._settlement_currency_for_token(cadc_address, configured_settings)

    assert result == "CADC"


def test_settlement_currency_for_token_resolves_usdc_address(settings):
    usdc_address = settings.usdc_token_address

    result = contract_service._settlement_currency_for_token(usdc_address, settings)

    assert result == "USDC"


def test_settlement_currency_for_token_returns_usdc_for_unknown_token(settings):
    unknown_address = Web3.to_checksum_address("0x0000000000000000000000000000000000000077")

    result = contract_service._settlement_currency_for_token(unknown_address, settings)

    assert result == "USDC"


def test_max_price_reads_first_accepted_token_config(monkeypatch, settings):
    captured = {}

    class FakeCall:
        def __init__(self, result):
            self._result = result

        def call(self):
            return self._result

    class FakeFunctions:
        def acceptedTokenAt(self, index):
            captured["accepted_token_at"] = index
            return FakeCall("0x0000000000000000000000000000000000000002")

        def acceptedTokens(self, token):
            captured["accepted_tokens"] = token
            return FakeCall((True, 6, 123456))

    monkeypatch.setattr(
        contract_service,
        "_get_contract",
        lambda _settings: SimpleNamespace(functions=FakeFunctions()),
    )

    unconfigured_settings = settings.model_copy(update={"usdc_token_address": ""})

    assert contract_service.max_price(unconfigured_settings) == 123456
    assert captured == {
        "accepted_token_at": 0,
        "accepted_tokens": "0x0000000000000000000000000000000000000002",
    }


def test_max_price_prefers_configured_payment_token(monkeypatch, settings):
    configured_settings = settings.model_copy(
        update={
            "usdc_token_address": "0x0000000000000000000000000000000000000002"
        }
    )
    captured = {}

    class FakeCall:
        def __init__(self, result):
            self._result = result

        def call(self):
            return self._result

    class FakeFunctions:
        def acceptedTokenAt(self, index):
            raise AssertionError("configured payment token should be used")

        def acceptedTokens(self, token):
            captured["accepted_tokens"] = token
            return FakeCall((True, 6, 987654))

    monkeypatch.setattr(
        contract_service,
        "_get_contract",
        lambda _settings: SimpleNamespace(functions=FakeFunctions()),
    )

    assert contract_service.max_price(configured_settings) == 987654
    assert captured == {
        "accepted_tokens": Web3.to_checksum_address(
            "0x0000000000000000000000000000000000000002"
        )
    }


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


def test_get_all_items_returns_empty_when_contract_not_deployed(monkeypatch, settings):
    fake_web3 = SimpleNamespace(
        eth=SimpleNamespace(
            get_code=lambda _address: b"",
        )
    )

    monkeypatch.setattr(contract_service, "_get_web3", lambda _settings: fake_web3)
    monkeypatch.setattr(
        contract_service,
        "_get_contract",
        lambda _settings: (_ for _ in ()).throw(
            AssertionError("should not build contract")
        ),
    )

    assert contract_service.get_all_items(settings) == []


def test_send_tx_submits_eip1559_transaction(monkeypatch, settings):
    captured = {}

    class FakeFunction:
        def build_transaction(self, tx_params):
            captured["build_params"] = dict(tx_params)
            return {
                **tx_params,
                "to": "0x00000000000000000000000000000000000000fE",
                "data": "0x1234",
                "gasPrice": 1,
            }

    class FakeAccount:
        address = "0x0000000000000000000000000000000000000005"

        def sign_transaction(self, tx):
            captured["signed_tx"] = dict(tx)
            return SimpleNamespace(raw_transaction=b"\xaa\xbb")

    fake_account = FakeAccount()

    class FakeEth:
        chain_id = settings.chain_id

        def __init__(self):
            self.account = SimpleNamespace(from_key=self.from_key)

        def from_key(self, private_key):
            captured["private_key"] = private_key
            return fake_account

        def get_transaction_count(self, address, state):
            captured["nonce_args"] = (address, state)
            return 7

        def estimate_gas(self, tx):
            captured["estimate_tx"] = dict(tx)
            return 21_000

        def get_block(self, block_id):
            captured["block_id"] = block_id
            return {"baseFeePerGas": 100}

        def send_raw_transaction(self, raw_tx):
            captured["raw_tx"] = raw_tx
            return HexBytes("0x" + "ab" * 32)

        def wait_for_transaction_receipt(self, tx_hash):
            captured["receipt_hash"] = tx_hash
            return SimpleNamespace(status=1)

    class FakeWeb3:
        def __init__(self):
            self.eth = FakeEth()

        def to_wei(self, value, unit):
            return Web3.to_wei(value, unit)

    monkeypatch.setattr(contract_service, "_get_web3", lambda _settings: FakeWeb3())

    tx_hash = contract_service._send_tx(FakeFunction(), settings, value=99)

    assert tx_hash == "ab" * 32
    assert captured["build_params"] == {
        "from": fake_account.address,
        "nonce": 7,
        "chainId": settings.chain_id,
        "value": 99,
    }
    assert captured["nonce_args"] == (fake_account.address, "pending")
    assert captured["estimate_tx"]["value"] == 99
    assert captured["signed_tx"]["gas"] == 21_000
    assert captured["signed_tx"]["type"] == "0x2"
    assert captured["signed_tx"]["maxPriorityFeePerGas"] == Web3.to_wei(1, "gwei")
    assert captured["signed_tx"]["maxFeePerGas"] == 200 + Web3.to_wei(1, "gwei")
    assert "gasPrice" not in captured["signed_tx"]
    assert captured["raw_tx"] == b"\xaa\xbb"
    assert captured["receipt_hash"] == HexBytes("0x" + "ab" * 32)


def test_send_tx_translates_custom_error_during_build(monkeypatch, settings):
    class FakeFunction:
        def build_transaction(self, tx_params):
            raise RuntimeError("execution reverted: custom error 0xac30c3e9")

    class FakeEth:
        chain_id = settings.chain_id

        def __init__(self):
            self.account = SimpleNamespace(
                from_key=lambda _key: SimpleNamespace(
                    address="0x0000000000000000000000000000000000000006"
                )
            )

        def get_transaction_count(self, address, state):
            return 1

    monkeypatch.setattr(
        contract_service,
        "_get_web3",
        lambda _settings: SimpleNamespace(eth=FakeEth(), to_wei=Web3.to_wei),
    )

    with pytest.raises(contract_service.HTTPException) as exc_info:
        contract_service._send_tx(FakeFunction(), settings)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Price exceeds maximum. operation=build_transaction"


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

    monkeypatch.setattr(
        contract_service, "_get_contract", lambda _settings: fake_contract
    )
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


def test_buy_item_rejects_insufficient_payment(monkeypatch, settings):
    listing_id_bytes = contract_service.uuid_to_bytes32(LISTING_ID)

    class FakeCall:
        def __init__(self, result):
            self._result = result

        def call(self):
            return self._result

    class FakeFunctions:
        def getItemView(self, requested_item_id):
            assert requested_item_id == listing_id_bytes
            return FakeCall(
                (
                    requested_item_id,
                    "Dataset",
                    "desc",
                    "0x0000000000000000000000000000000000000001",
                    100,
                    "ipfs://dataset",
                    bytes.fromhex("11" * 32),
                    "ipfs://signature",
                    bytes.fromhex("22" * 32),
                    True,
                    0,
                )
            )

        def feeBps(self):
            return FakeCall(250)

        def buyItem(self, requested_item_id):
            raise AssertionError("buyItem should not be called when payment is too low")

    fake_contract = SimpleNamespace(functions=FakeFunctions())
    monkeypatch.setattr(
        contract_service, "_get_contract", lambda _settings: fake_contract
    )
    monkeypatch.setattr(
        contract_service,
        "_call_contract_read",
        lambda callable_obj, _operation: callable_obj.call(),
    )

    with pytest.raises(contract_service.HTTPException) as exc_info:
        contract_service.buy_item(LISTING_ID, value_wei=101, settings=settings)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == (
        "Insufficient payment. required=102 provided=101 (price=100, fee_bps=250)"
    )


def test_create_item_rejects_invalid_hash_format(monkeypatch, settings):
    monkeypatch.setattr(
        contract_service,
        "_get_contract",
        lambda _settings: SimpleNamespace(functions=SimpleNamespace()),
    )

    with pytest.raises(contract_service.HTTPException) as exc_info:
        contract_service.create_item(
            listing_id="123e4567-e89b-12d3-a456-426614174000",
            title="Dataset",
            description="desc",
            seller="0x0000000000000000000000000000000000000001",
            payment_token="0x0000000000000000000000000000000000000002",
            price=100,
            dataset_url="ipfs://dataset",
            dataset_hash="not-a-hash",
            signature_url="ipfs://signature",
            signature_hash="0x" + "22" * 32,
            settings=settings,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid dataset/signature hash format"


def test_create_item_normalizes_payment_token_and_sends_tx(monkeypatch, settings):
    captured = {}
    tx_object = object()

    class FakeFunctions:
        def createItem(
            self,
            item_id,
            title,
            description,
            seller,
            payment_token,
            price,
            dataset_url,
            dataset_hash,
            signature_url,
            signature_hash,
        ):
            captured["create_item_args"] = (
                item_id,
                title,
                description,
                seller,
                payment_token,
                price,
                dataset_url,
                dataset_hash,
                signature_url,
                signature_hash,
            )
            return tx_object

    monkeypatch.setattr(
        contract_service,
        "_get_contract",
        lambda _settings: SimpleNamespace(functions=FakeFunctions()),
    )

    def fake_send_tx(function, resolved_settings):
        captured["send_tx_args"] = (function, resolved_settings)
        return "0x" + "ee" * 32

    monkeypatch.setattr(contract_service, "_send_tx", fake_send_tx)

    tx_hash = contract_service.create_item(
        listing_id=LISTING_ID,
        title="Dataset",
        description="desc",
        seller="0x0000000000000000000000000000000000000001",
        payment_token="0x0000000000000000000000000000000000000002",
        price=100,
        dataset_url="ipfs://dataset",
        dataset_hash="0x" + "11" * 32,
        signature_url="ipfs://signature",
        signature_hash="0x" + "22" * 32,
        settings=settings,
    )

    assert tx_hash == "0x" + "ee" * 32
    args = captured["create_item_args"]
    assert args[0] == contract_service.uuid_to_bytes32(LISTING_ID)
    assert args[3] == Web3.to_checksum_address(
        "0x0000000000000000000000000000000000000001"
    )
    assert args[4] == Web3.to_checksum_address(
        "0x0000000000000000000000000000000000000002"
    )
    assert args[5] == 100
    assert captured["send_tx_args"] == (tx_object, settings)


def test_create_item_rejects_invalid_payment_token(monkeypatch, settings):
    monkeypatch.setattr(
        contract_service,
        "_get_contract",
        lambda _settings: SimpleNamespace(functions=SimpleNamespace()),
    )

    with pytest.raises(contract_service.HTTPException) as exc_info:
        contract_service.create_item(
            listing_id=LISTING_ID,
            title="Dataset",
            description="desc",
            seller="0x0000000000000000000000000000000000000001",
            payment_token="not-an-address",
            price=100,
            dataset_url="ipfs://dataset",
            dataset_hash="0x" + "11" * 32,
            signature_url="ipfs://signature",
            signature_hash="0x" + "22" * 32,
            settings=settings,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid payment token EVM address"


def test_update_signature_rejects_invalid_hash_format(monkeypatch, settings):
    monkeypatch.setattr(
        contract_service,
        "_get_contract",
        lambda _settings: SimpleNamespace(functions=SimpleNamespace()),
    )

    with pytest.raises(contract_service.HTTPException) as exc_info:
        contract_service.update_signature(
            LISTING_ID,
            new_url="ipfs://signature",
            new_hash="bad-hash",
            settings=settings,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid signature hash format"


def test_set_fee_config_normalizes_address_and_sends_tx(monkeypatch, settings):
    captured = {}
    tx_object = object()

    class FakeFunctions:
        def setFeeConfig(self, recipient, fee_bps):
            captured["set_fee_config_args"] = (recipient, fee_bps)
            return tx_object

    monkeypatch.setattr(
        contract_service,
        "_get_contract",
        lambda _settings: SimpleNamespace(functions=FakeFunctions()),
    )

    def fake_send_tx(function, resolved_settings):
        captured["send_tx_args"] = (function, resolved_settings)
        return "0x" + "aa" * 32

    monkeypatch.setattr(
        contract_service,
        "_send_tx",
        fake_send_tx,
    )

    tx_hash = contract_service.set_fee_config(
        "0x0000000000000000000000000000000000000002",
        150,
        settings,
    )

    assert tx_hash == "0x" + "aa" * 32
    assert captured["set_fee_config_args"] == (
        Web3.to_checksum_address("0x0000000000000000000000000000000000000002"),
        150,
    )
    assert captured["send_tx_args"] == (tx_object, settings)


def test_set_fee_config_rejects_invalid_fee_recipient(monkeypatch, settings):
    monkeypatch.setattr(
        contract_service,
        "_get_contract",
        lambda _settings: SimpleNamespace(functions=SimpleNamespace()),
    )

    with pytest.raises(contract_service.HTTPException) as exc_info:
        contract_service.set_fee_config("bad-address", 100, settings)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid fee recipient EVM address"


def test_transfer_ownership_normalizes_address_and_sends_tx(monkeypatch, settings):
    captured = {}
    tx_object = object()

    class FakeFunctions:
        def transferOwnership(self, owner):
            captured["transfer_args"] = owner
            return tx_object

    monkeypatch.setattr(
        contract_service,
        "_get_contract",
        lambda _settings: SimpleNamespace(functions=FakeFunctions()),
    )

    def fake_send_tx(function, resolved_settings):
        captured["send_tx_args"] = (function, resolved_settings)
        return "0x" + "bb" * 32

    monkeypatch.setattr(
        contract_service,
        "_send_tx",
        fake_send_tx,
    )

    tx_hash = contract_service.transfer_ownership(
        "0x0000000000000000000000000000000000000003", settings
    )

    assert tx_hash == "0x" + "bb" * 32
    assert captured["transfer_args"] == Web3.to_checksum_address(
        "0x0000000000000000000000000000000000000003"
    )
    assert captured["send_tx_args"] == (tx_object, settings)


def test_transfer_ownership_rejects_invalid_owner(monkeypatch, settings):
    monkeypatch.setattr(
        contract_service,
        "_get_contract",
        lambda _settings: SimpleNamespace(functions=SimpleNamespace()),
    )

    with pytest.raises(contract_service.HTTPException) as exc_info:
        contract_service.transfer_ownership("not-an-address", settings)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid new owner EVM address"


def test_renounce_ownership_forwards_tx(monkeypatch, settings):
    captured = {}
    tx_object = object()

    class FakeFunctions:
        def renounceOwnership(self):
            captured["renounce_called"] = True
            return tx_object

    monkeypatch.setattr(
        contract_service,
        "_get_contract",
        lambda _settings: SimpleNamespace(functions=FakeFunctions()),
    )

    def fake_send_tx(function, resolved_settings):
        captured["send_tx_args"] = (function, resolved_settings)
        return "0x" + "cc" * 32

    monkeypatch.setattr(
        contract_service,
        "_send_tx",
        fake_send_tx,
    )

    tx_hash = contract_service.renounce_ownership(settings)

    assert tx_hash == "0x" + "cc" * 32
    assert captured["renounce_called"] is True
    assert captured["send_tx_args"] == (tx_object, settings)


def test_grant_access_uses_uuid_bytes_and_wallet_bytes(monkeypatch, settings):
    captured = {}
    tx_object = object()
    wallet_id_bytes = b"wallet-id-32-bytes".ljust(32, b"\x00")

    class FakeFunctions:
        def grantAccess(self, item_id, wallet_id):
            captured["grant_args"] = (item_id, wallet_id)
            return tx_object

    monkeypatch.setattr(
        contract_service,
        "_get_contract",
        lambda _settings: SimpleNamespace(functions=FakeFunctions()),
    )

    def fake_send_tx(function, resolved_settings):
        captured["send_tx_args"] = (function, resolved_settings)
        return "0x" + "dd" * 32

    monkeypatch.setattr(
        contract_service,
        "_send_tx",
        fake_send_tx,
    )

    tx_hash = contract_service.grant_access(LISTING_ID, wallet_id_bytes, settings)

    assert tx_hash == "0x" + "dd" * 32
    assert captured["grant_args"] == (
        contract_service.uuid_to_bytes32(LISTING_ID),
        wallet_id_bytes,
    )
    assert captured["send_tx_args"] == (tx_object, settings)
