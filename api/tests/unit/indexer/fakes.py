"""An in-memory JSON-RPC provider that serves Marketplace logs and views.

It lets the indexer run through the real web3 request/decoding path
(eth_getLogs formatting, event decoding, eth_call ABI decoding) with no node.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from eth_abi import encode
from web3 import Web3
from web3.providers.base import BaseProvider

import app.contracts as contracts_pkg

ABI = json.loads((Path(contracts_pkg.__file__).parent / "Marketplace.json").read_text())
MARKETPLACE = Web3.to_checksum_address("0x" + "12" * 20)
OTHER_CONTRACT = Web3.to_checksum_address("0x" + "34" * 20)
USDC = Web3.to_checksum_address("0x" + "0a" * 20)
SELLER = Web3.to_checksum_address("0x" + "5e" * 20)
BUYER = Web3.to_checksum_address("0x" + "b0" * 20)
BUYER_2 = Web3.to_checksum_address("0x" + "b2" * 20)
BLOCK_TIME_BASE = 1_760_000_000

_OFFLINE = Web3().eth.contract(address=MARKETPLACE, abi=ABI)


def item_id(n: int) -> bytes:
    return bytes([n]) * 16 + b"\x00" * 16


def _abi_type(entry: dict[str, Any]) -> str:
    if entry["type"].startswith("tuple"):
        inner = ",".join(_abi_type(c) for c in entry["components"])
        return f"({inner}){entry['type'][5:]}"
    return entry["type"]


def _selector(name: str) -> str:
    fn_abi = _OFFLINE.get_function_by_name(name).abi
    sig = f"{name}({','.join(_abi_type(i) for i in fn_abi['inputs'])})"
    return Web3.to_hex(Web3.keccak(text=sig)[:4])


def _encode_outputs(name: str, values: list[Any]) -> str:
    fn_abi = _OFFLINE.get_function_by_name(name).abi
    types = [_abi_type(o) for o in fn_abi["outputs"]]
    return Web3.to_hex(encode(types, values))


class FakeChain(BaseProvider):
    """Minimal node: serves logs, block timestamps and two view functions."""

    def __init__(self, head: int = 0) -> None:
        super().__init__()
        self.head = head
        self.logs: list[dict[str, Any]] = []
        self.items: dict[bytes, dict[str, Any]] = {}
        self.token_decimals: dict[str, int] = {USDC: 6}
        self.get_logs_calls: list[dict[str, Any]] = []
        self.fail_block_times: set[int] = set()
        self.ignore_address_filter = False
        self._tx_counter = 0

    # ---- fixture builders -------------------------------------------------

    def add_event(
        self,
        name: str,
        block: int,
        log_index: int,
        address: str = MARKETPLACE,
        tx_hash: str | None = None,
        **args: Any,
    ) -> str:
        event_abi = _OFFLINE.events[name].abi
        topics = [str(_OFFLINE.events[name].topic).lower()]
        data_types, data_values = [], []
        for inp in event_abi["inputs"]:
            if inp["indexed"]:
                topics.append(Web3.to_hex(encode([inp["type"]], [args[inp["name"]]])))
            else:
                data_types.append(inp["type"])
                data_values.append(args[inp["name"]])
        if tx_hash is None:
            self._tx_counter += 1
            tx_hash = "0x" + f"{self._tx_counter:064x}"
        self.logs.append(
            {
                "address": address.lower(),
                "topics": topics,
                "data": Web3.to_hex(encode(data_types, data_values)),
                "blockNumber": hex(block),
                "blockHash": "0x" + f"{block:064x}",
                "transactionHash": tx_hash,
                "transactionIndex": "0x0",
                "logIndex": hex(log_index),
                "removed": False,
            }
        )
        return tx_hash

    def add_listing(
        self,
        n: int,
        block: int,
        log_index: int = 0,
        price: int = 1_000_000,
        title: str | None = None,
    ) -> bytes:
        iid = item_id(n)
        self.items[iid] = {
            "title": title or f"Dataset {n}",
            "description": f"Description {n}",
            "seller": SELLER,
            "price": price,
            "datasetUrl": f"ipfs://dataset-{n}",
            "datasetHash": b"\x11" * 32,
            "signatureUrl": "",
            "signatureHash": b"\x00" * 32,
            "paymentToken": USDC,
        }
        self.add_event(
            "ItemCreated",
            block,
            log_index,
            itemId=iid,
            seller=SELLER,
            paymentToken=USDC,
            price=price,
            datasetUrl=f"ipfs://dataset-{n}",
            datasetHash=b"\x11" * 32,
            signatureUrl="",
            signatureHash=b"\x00" * 32,
        )
        return iid

    def add_purchase(
        self, iid: bytes, block: int, log_index: int = 0, buyer: str = BUYER
    ) -> str:
        return self.add_event(
            "ItemPurchased",
            block,
            log_index,
            itemId=iid,
            buyer=buyer,
            paymentToken=USDC,
            pricePaid=1_010_000,
            feePaid=10_000,
            sellerPaid=1_000_000,
        )

    # ---- JSON-RPC ---------------------------------------------------------

    def _ok(self, result: Any) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": 1, "result": result}

    def make_request(self, method, params):  # type: ignore[override]
        if method == "eth_chainId":
            return self._ok(hex(31337))
        if method == "eth_blockNumber":
            return self._ok(hex(self.head))
        if method == "eth_getLogs":
            return self._ok(self._get_logs(params[0]))
        if method == "eth_getBlockByNumber":
            number = int(params[0], 16)
            if number in self.fail_block_times:
                raise ConnectionError(f"RPC failed for block {number}")
            return self._ok(
                {
                    "number": hex(number),
                    "hash": "0x" + f"{number:064x}",
                    "parentHash": "0x" + f"{max(number - 1, 0):064x}",
                    "timestamp": hex(BLOCK_TIME_BASE + number),
                    "transactions": [],
                }
            )
        if method == "eth_call":
            return self._ok(self._call(params[0]["data"]))
        raise NotImplementedError(method)

    def _get_logs(self, flt: dict[str, Any]) -> list[dict[str, Any]]:
        self.get_logs_calls.append(flt)
        start, end = int(flt["fromBlock"], 16), int(flt["toBlock"], 16)
        raw_address = flt.get("address") or []
        addresses = {
            a.lower() for a in ([raw_address] if isinstance(raw_address, str) else raw_address)
        }
        topic0 = {t.lower() for t in (flt.get("topics") or [[]])[0]}
        out = []
        for log in self.logs:
            if not start <= int(log["blockNumber"], 16) <= end:
                continue
            if not self.ignore_address_filter and log["address"] not in addresses:
                continue
            if topic0 and log["topics"][0] not in topic0:
                continue
            out.append(log)
        return out

    def _call(self, data: str) -> str:
        selector, args = data[:10], bytes.fromhex(data[10:])
        if selector == _selector("getItemView"):
            iid = args[:32]
            it = self.items[iid]
            view = (
                iid,
                it["title"],
                it["description"],
                it["seller"],
                it["price"],
                it["datasetUrl"],
                it["datasetHash"],
                it["signatureUrl"],
                it["signatureHash"],
                True,
                0,
                it["paymentToken"],
            )
            return _encode_outputs("getItemView", [view])
        if selector == _selector("acceptedTokens"):
            token = Web3.to_checksum_address(args[12:32])
            return _encode_outputs(
                "acceptedTokens", [True, self.token_decimals[token], 10**30]
            )
        raise NotImplementedError(selector)


def contract_for(chain: FakeChain):
    return Web3(chain).eth.contract(address=MARKETPLACE, abi=ABI)
