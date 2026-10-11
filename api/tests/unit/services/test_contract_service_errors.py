from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from web3 import Web3

from app.contracts import service as contract_service

LEAKY = "upstream https://rpc.example/v3/SECRET-API-KEY failed for key 0xdeadbeef"


def _fake_web3(settings, *, fail_at: str):
    class FakeFunction:
        def build_transaction(self, tx_params):
            return {**tx_params, "to": "0x" + "fe" * 20, "data": "0x"}

    class FakeAccount:
        address = "0x0000000000000000000000000000000000000005"

        def sign_transaction(self, tx):
            return SimpleNamespace(raw_transaction=b"\xaa")

    class FakeEth:
        chain_id = settings.chain_id

        def __init__(self):
            self.account = SimpleNamespace(from_key=lambda key: FakeAccount())

        def get_transaction_count(self, address, state):
            return 1

        def estimate_gas(self, tx):
            return 21_000

        def get_block(self, block_id):
            if fail_at == "get_block":
                raise RuntimeError(LEAKY)
            return {"baseFeePerGas": 1}

        def send_raw_transaction(self, raw_tx):
            if fail_at == "send":
                raise RuntimeError(LEAKY)
            return b"\x01" * 32

        def wait_for_transaction_receipt(self, tx_hash):
            return SimpleNamespace(status=1)

    class FakeWeb3:
        eth = FakeEth()

        def to_wei(self, value, unit):
            return Web3.to_wei(value, unit)

    return FakeFunction(), FakeWeb3()


@pytest.mark.parametrize("fail_at", ["send", "get_block"])
def test_send_tx_upstream_errors_do_not_leak_exception_text(
    monkeypatch, settings, fail_at
):
    function, web3 = _fake_web3(settings, fail_at=fail_at)
    monkeypatch.setattr(contract_service, "_get_web3", lambda _settings: web3)

    with pytest.raises(HTTPException) as exc_info:
        contract_service._send_tx(function, settings)

    assert exc_info.value.status_code == 502
    assert "SECRET-API-KEY" not in exc_info.value.detail
    assert "rpc.example" not in exc_info.value.detail
    assert "0xdeadbeef" not in exc_info.value.detail
