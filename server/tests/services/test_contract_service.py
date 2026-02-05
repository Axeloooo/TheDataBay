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
