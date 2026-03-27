import pytest

from app.routers import contract_router
from app.schemas.marketplace_schema import MarketplaceDataItem

LISTING_ID = "123e4567-e89b-12d3-a456-426614174000"


def make_item(item_id: str) -> MarketplaceDataItem:
    return MarketplaceDataItem(
        id=item_id,
        title=f"Dataset {item_id[-4:]}",
        description="Sample dataset",
        seller="0x0000000000000000000000000000000000000001",
        price_atomic="100",
        settlement_currency="USDC",
        settlement_decimals=6,
        dataset_url="ipfs://dataset",
        dataset_hash="0x" + "ab" * 32,
        signature_url="ipfs://signature",
        signature_hash="0x" + "cd" * 32,
        exists=True,
        purchase_count=1,
    )


@pytest.mark.parametrize(
    ("path", "service_attr", "expected"),
    [
        ("/api/v1/contract/max-price", "max_price", 123456),
        ("/api/v1/contract/fee-bps", "fee_bps", 250),
        (
            "/api/v1/contract/fee-recipient",
            "fee_recipient",
            "0x00000000000000000000000000000000000000fE",
        ),
        (
            "/api/v1/contract/owner",
            "owner",
            "0x00000000000000000000000000000000000000AA",
        ),
    ],
)
def test_contract_scalar_read_endpoints(
    client_factory, override_settings, monkeypatch, path, service_attr, expected
):
    settings = override_settings()
    captured = {}

    def fake_service(resolved_settings):
        captured["settings"] = resolved_settings
        return expected

    monkeypatch.setattr(contract_router.contract_service, service_attr, fake_service)

    with client_factory(settings=settings) as client:
        response = client.get(path)

    assert response.status_code == 200
    assert response.json() == expected
    assert captured["settings"] is settings


def test_contract_item_read_endpoints_patch_router_module(
    client_factory, override_settings, monkeypatch
):
    settings = override_settings()
    item = make_item("0x" + "01" * 32)
    all_items = [item]
    paged_items = [item]
    captured = {}

    def fake_get_all_items(resolved_settings):
        captured["all_settings"] = resolved_settings
        return all_items

    def fake_get_items(start, count, resolved_settings):
        captured["paged_args"] = (start, count, resolved_settings)
        return paged_items

    def fake_get_item_view(listing_id, resolved_settings):
        captured["item_args"] = (listing_id, resolved_settings)
        return item

    monkeypatch.setattr(
        contract_router.contract_service, "get_all_items", fake_get_all_items
    )
    monkeypatch.setattr(contract_router.contract_service, "get_items", fake_get_items)
    monkeypatch.setattr(
        contract_router.contract_service, "get_item_view", fake_get_item_view
    )

    with client_factory(settings=settings) as client:
        all_response = client.get("/api/v1/contract/items/all")
        paged_response = client.get(
            "/api/v1/contract/items", params={"start": 2, "count": 5}
        )
        item_response = client.get(f"/api/v1/contract/items/{LISTING_ID}")

    assert all_response.status_code == 200
    assert all_response.json() == [item.model_dump(mode="json")]
    assert paged_response.status_code == 200
    assert paged_response.json() == [item.model_dump(mode="json")]
    assert item_response.status_code == 200
    assert item_response.json() == item.model_dump(mode="json")
    assert captured["all_settings"] is settings
    assert captured["paged_args"] == (2, 5, settings)
    assert captured["item_args"] == (LISTING_ID, settings)


def test_contract_purchases_by_wallet_returns_count_and_items(
    client_factory, override_settings, monkeypatch
):
    settings = override_settings()
    item = make_item("0x" + "02" * 32)
    captured = {}

    def fake_get_purchased_items_by_wallet(
        *, wallet_type, address, settings, start_block, end_block, limit, offset
    ):
        captured["args"] = {
            "wallet_type": wallet_type,
            "address": address,
            "settings": settings,
            "start_block": start_block,
            "end_block": end_block,
            "limit": limit,
            "offset": offset,
        }
        return ("0x" + "11" * 32, [item])

    monkeypatch.setattr(
        contract_router.contract_service,
        "get_purchased_items_by_wallet",
        fake_get_purchased_items_by_wallet,
    )

    with client_factory(settings=settings) as client:
        response = client.post(
            "/api/v1/contract/purchases/by-wallet",
            json={
                "wallet_type": "evm",
                "address": "0x0000000000000000000000000000000000000001",
                "start_block": 10,
                "end_block": 20,
                "limit": 3,
                "offset": 1,
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "wallet_id": "0x" + "11" * 32,
        "items": [item.model_dump(mode="json")],
        "count": 1,
    }
    assert captured["args"] == {
        "wallet_type": "evm",
        "address": "0x0000000000000000000000000000000000000001",
        "settings": settings,
        "start_block": 10,
        "end_block": 20,
        "limit": 3,
        "offset": 1,
    }


def test_contract_check_access_uses_wallet_id_then_has_access(
    client_factory, override_settings, monkeypatch
):
    settings = override_settings()
    captured = {}

    def fake_wallet_id(wallet_type, address, resolved_settings):
        captured["wallet_args"] = (wallet_type, address, resolved_settings)
        return b"wallet-id"

    def fake_has_access(listing_id, wallet_id_bytes, resolved_settings):
        captured["access_args"] = (listing_id, wallet_id_bytes, resolved_settings)
        return True

    monkeypatch.setattr(contract_router.contract_service, "wallet_id", fake_wallet_id)
    monkeypatch.setattr(contract_router.contract_service, "has_access", fake_has_access)

    with client_factory(settings=settings) as client:
        response = client.post(
            f"/api/v1/contract/access/{LISTING_ID}/check",
            json={
                "wallet_type": "evm",
                "address": "0x0000000000000000000000000000000000000001",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"has_access": True}
    assert captured["wallet_args"] == (
        "evm",
        "0x0000000000000000000000000000000000000001",
        settings,
    )
    assert captured["access_args"] == (LISTING_ID, b"wallet-id", settings)


@pytest.mark.parametrize(
    ("method", "path", "body", "service_attr", "service_result", "expected_args"),
    [
        (
            "patch",
            f"/api/v1/contract/items/{LISTING_ID}/dataset-url",
            {"new_url": "ipfs://new-dataset"},
            "update_dataset_url",
            "0x" + "01" * 32,
            (LISTING_ID, "ipfs://new-dataset"),
        ),
        (
            "patch",
            f"/api/v1/contract/items/{LISTING_ID}/signature",
            {"new_url": "ipfs://new-signature", "new_hash": "0x" + "ef" * 32},
            "update_signature",
            "0x" + "02" * 32,
            (LISTING_ID, "ipfs://new-signature", "0x" + "ef" * 32),
        ),
        (
            "patch",
            f"/api/v1/contract/items/{LISTING_ID}/price",
            {"new_price": 555},
            "update_price",
            "0x" + "03" * 32,
            (LISTING_ID, 555),
        ),
        (
            "patch",
            "/api/v1/contract/fee-config",
            {
                "fee_recipient": "0x0000000000000000000000000000000000000002",
                "fee_bps": 125,
            },
            "set_fee_config",
            "0x" + "04" * 32,
            ("0x0000000000000000000000000000000000000002", 125),
        ),
        (
            "post",
            "/api/v1/contract/ownership/transfer",
            {"new_owner": "0x0000000000000000000000000000000000000003"},
            "transfer_ownership",
            "0x" + "05" * 32,
            ("0x0000000000000000000000000000000000000003",),
        ),
    ],
)
def test_contract_write_endpoints_forward_to_service(
    client_factory,
    override_settings,
    monkeypatch,
    method,
    path,
    body,
    service_attr,
    service_result,
    expected_args,
):
    settings = override_settings()
    captured = {}

    def fake_service(*args):
        captured["args"] = args
        return service_result

    monkeypatch.setattr(contract_router.contract_service, service_attr, fake_service)

    with client_factory(settings=settings) as client:
        response = getattr(client, method)(path, json=body)

    assert response.status_code == 200
    assert response.json() == {"tx_hash": service_result}
    assert captured["args"] == (*expected_args, settings)


def test_contract_grant_access_derives_wallet_id_before_service_call(
    client_factory, override_settings, monkeypatch
):
    settings = override_settings()
    captured = {}

    def fake_wallet_id(wallet_type, address, resolved_settings):
        captured["wallet_args"] = (wallet_type, address, resolved_settings)
        return b"derived-wallet"

    def fake_grant_access(listing_id, wallet_id_bytes, resolved_settings):
        captured["grant_args"] = (listing_id, wallet_id_bytes, resolved_settings)
        return "0x" + "06" * 32

    monkeypatch.setattr(contract_router.contract_service, "wallet_id", fake_wallet_id)
    monkeypatch.setattr(
        contract_router.contract_service, "grant_access", fake_grant_access
    )

    with client_factory(settings=settings) as client:
        response = client.post(
            f"/api/v1/contract/items/{LISTING_ID}/grant-access",
            json={
                "wallet_type": "evm",
                "address": "0x0000000000000000000000000000000000000004",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"tx_hash": "0x" + "06" * 32}
    assert captured["wallet_args"] == (
        "evm",
        "0x0000000000000000000000000000000000000004",
        settings,
    )
    assert captured["grant_args"] == (LISTING_ID, b"derived-wallet", settings)


def test_contract_renounce_ownership_forwards_to_service(
    client_factory, override_settings, monkeypatch
):
    settings = override_settings()
    captured = {}

    def fake_renounce_ownership(resolved_settings):
        captured["settings"] = resolved_settings
        return "0x" + "07" * 32

    monkeypatch.setattr(
        contract_router.contract_service,
        "renounce_ownership",
        fake_renounce_ownership,
    )

    with client_factory(settings=settings) as client:
        response = client.post("/api/v1/contract/ownership/renounce")

    assert response.status_code == 200
    assert response.json() == {"tx_hash": "0x" + "07" * 32}
    assert captured["settings"] is settings


def test_contract_create_item_requires_direct_wallet_transaction(
    client_factory, monkeypatch
):
    monkeypatch.setattr(
        contract_router.contract_service,
        "create_item",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("create_item service should not be called")
        ),
    )

    with client_factory() as client:
        response = client.post(
            "/api/v1/contract/items",
            json={
                "listing_id": LISTING_ID,
                "title": "Dataset title",
                "description": "Dataset description",
                "seller": "0x0000000000000000000000000000000000000001",
                "price": 100,
                "dataset_url": "ipfs://dataset",
                "dataset_hash": "0x" + "11" * 32,
                "signature_url": "ipfs://signature",
                "signature_hash": "0x" + "22" * 32,
            },
        )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Direct wallet transaction required for createItem."
    }


def test_contract_buy_item_requires_direct_wallet_transaction(
    client_factory, monkeypatch
):
    monkeypatch.setattr(
        contract_router.contract_service,
        "buy_item",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("buy_item service should not be called")
        ),
    )

    with client_factory() as client:
        response = client.post(
            f"/api/v1/contract/items/{LISTING_ID}/buy",
            json={"value_wei": 200},
        )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Direct wallet transaction required for buyItem."
    }
