"""
Router exposing Marketplace smart contract operations.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..config.settings import Settings, get_settings
from .schemas import (
    AccessCheckResponse,
    BuyItemRequest,
    CreateItemRequest,
    GrantAccessRequest,
    SetFeeConfigRequest,
    TransferOwnershipRequest,
    TxHashResponse,
    UpdateDatasetUrlRequest,
    PurchasedItemsRequest,
    PurchasedItemsResponse,
    UpdatePriceRequest,
    UpdateSignatureRequest,
    WalletAccessRequest,
)
from .marketplace_schemas import MarketplaceDataItem
from . import service as contract_service

router = APIRouter(prefix="/api/v1/contract", tags=["contract"])
logger = logging.getLogger(__name__)


@router.get("/max-price", response_model=int)
def get_max_price(settings: Settings = Depends(get_settings)) -> int:
    """Get the maximum allowed item price from the marketplace contract.

    Args:
        settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).

    Returns:
        int: Maximum item price in settlement token atomic units
    """
    return contract_service.max_price(settings)


@router.get("/fee-bps", response_model=int)
def get_fee_bps(settings: Settings = Depends(get_settings)) -> int:
    """Get the current marketplace fee in basis points.

    Args:
        settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).

    Returns:
        int: Current fee in basis points
    """
    return contract_service.fee_bps(settings)


@router.get("/fee-recipient", response_model=str)
def get_fee_recipient(settings: Settings = Depends(get_settings)) -> str:
    """Get the configured fee recipient address.

    Args:
        settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).

    Returns:
        str: Fee recipient EVM address
    """
    return contract_service.fee_recipient(settings)


@router.get("/owner", response_model=str)
def get_owner(settings: Settings = Depends(get_settings)) -> str:
    """Get the current marketplace contract owner.

    Args:
        settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).

    Returns:
        str: Contract owner EVM address
    """
    return contract_service.owner(settings)


@router.get("/items/all", response_model=List[MarketplaceDataItem])
def get_all_items(
    settings: Settings = Depends(get_settings),
) -> List[MarketplaceDataItem]:
    """Get all marketplace items from the contract.

    Args:
        settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).

    Returns:
        List[MarketplaceDataItem]: Full list of marketplace items
    """
    logger.info("contract.get_all_items called")
    return contract_service.get_all_items(settings)


@router.get("/items", response_model=List[MarketplaceDataItem])
def get_items(
    start: int = 0,
    count: int = 20,
    settings: Settings = Depends(get_settings),
) -> List[MarketplaceDataItem]:
    """Get a paginated slice of marketplace items from the contract.

    Args:
        start (int, optional): Start index for pagination. Defaults to 0.
        count (int, optional): Number of items to return. Defaults to 20.
        settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).

    Returns:
        List[MarketplaceDataItem]: Paginated list of marketplace items
    """
    logger.info("contract.get_items called start=%s count=%s", start, count)
    return contract_service.get_items(start, count, settings)


@router.get("/items/{listing_id}", response_model=MarketplaceDataItem)
def get_item_view(
    listing_id: str, settings: Settings = Depends(get_settings)
) -> MarketplaceDataItem:
    """Get one marketplace item by listing UUID.

    Args:
        listing_id (str): Listing UUID string
        settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).

    Returns:
        MarketplaceDataItem: Item view returned by the contract
    """
    logger.info("contract.get_item_view called listing_id=%s", listing_id)
    return contract_service.get_item_view(listing_id, settings)


@router.post("/purchases/by-wallet", response_model=PurchasedItemsResponse)
def get_purchases_by_wallet(
    request: PurchasedItemsRequest,
    settings: Settings = Depends(get_settings),
) -> PurchasedItemsResponse:
    """Get purchased marketplace items for a wallet via ItemPurchased event indexing.

    Args:
        request (PurchasedItemsRequest): Purchased items query payload.
        settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).

    Returns:
        PurchasedItemsResponse: Purchased items and derived wallet id.
    """
    logger.info(
        "contract.get_purchases_by_wallet called wallet_type=%s address=%s",
        request.wallet_type,
        request.address,
    )
    wallet_id_hex, items = contract_service.get_purchased_items_by_wallet(
        wallet_type=request.wallet_type,
        address=request.address,
        settings=settings,
        start_block=request.start_block,
        end_block=request.end_block,
        limit=request.limit,
        offset=request.offset,
    )
    return PurchasedItemsResponse(
        wallet_id=wallet_id_hex, items=items, count=len(items)
    )


@router.post("/items", response_model=TxHashResponse)
def create_item(
    request: CreateItemRequest, settings: Settings = Depends(get_settings)
) -> TxHashResponse:
    """Create a new marketplace item on-chain.

    Args:
        request (CreateItemRequest): Create item request model
        settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).

    Raises:
        HTTPException: Direct wallet transaction required for createItem.

    Returns:
        TxHashResponse: Transaction hash response
    """
    raise HTTPException(
        status_code=400,
        detail="Direct wallet transaction required for createItem.",
    )


@router.post("/items/{listing_id}/buy", response_model=TxHashResponse)
def buy_item(
    listing_id: str,
    request: BuyItemRequest,
    settings: Settings = Depends(get_settings),
) -> TxHashResponse:
    """Purchase an item on-chain.

    Args:
        listing_id (str): Listing UUID string
        request (BuyItemRequest): Buy item request model
        settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).

    Returns:
        TxHashResponse: Transaction hash response
    """
    raise HTTPException(
        status_code=400,
        detail="Direct wallet transaction required for buyItem.",
    )
    """Purchase an item on-chain.

    Args:
        listing_id (str): Listing UUID string
        request (BuyItemRequest): Buy item request model
        settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).

    Returns:
        TxHashResponse: Transaction hash response
    """
    tx_hash = contract_service.buy_item(listing_id, request.value_wei, settings)
    return TxHashResponse(tx_hash=tx_hash)


@router.patch("/items/{listing_id}/dataset-url", response_model=TxHashResponse)
def update_dataset_url(
    listing_id: str,
    request: UpdateDatasetUrlRequest,
    settings: Settings = Depends(get_settings),
) -> TxHashResponse:
    """Update the dataset URL for an existing item.

    Args:
        listing_id (str): Listing UUID string
        request (UpdateDatasetUrlRequest): Update dataset URL request model
        settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).

    Returns:
        TxHashResponse: Transaction hash response
    """
    tx_hash = contract_service.update_dataset_url(listing_id, request.new_url, settings)
    return TxHashResponse(tx_hash=tx_hash)


@router.patch("/items/{listing_id}/signature", response_model=TxHashResponse)
def update_signature(
    listing_id: str,
    request: UpdateSignatureRequest,
    settings: Settings = Depends(get_settings),
) -> TxHashResponse:
    """Update signature URL and hash for an existing item.

    Args:
        listing_id (str): Listing UUID string
        request (UpdateSignatureRequest): Update signature request model
        settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).

    Returns:
        TxHashResponse: Transaction hash response
    """
    tx_hash = contract_service.update_signature(
        listing_id, request.new_url, request.new_hash, settings
    )
    return TxHashResponse(tx_hash=tx_hash)


@router.patch("/items/{listing_id}/price", response_model=TxHashResponse)
def update_price(
    listing_id: str,
    request: UpdatePriceRequest,
    settings: Settings = Depends(get_settings),
) -> TxHashResponse:
    """Update item price on-chain.

    Args:
        listing_id (str): Listing UUID string
        request (UpdatePriceRequest): Update price request model
        settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).

    Returns:
        TxHashResponse: Transaction hash response
    """
    tx_hash = contract_service.update_price(listing_id, request.new_price, settings)
    return TxHashResponse(tx_hash=tx_hash)


@router.post("/access/{listing_id}/check", response_model=AccessCheckResponse)
def check_access(
    listing_id: str,
    request: WalletAccessRequest,
    settings: Settings = Depends(get_settings),
) -> AccessCheckResponse:
    """Check whether a wallet has access to a listing.

    Args:
        listing_id (str): Listing UUID string
        request (WalletAccessRequest): Wallet access request model
        settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).

    Returns:
        AccessCheckResponse: Access check result
    """
    logger.info(
        "contract.check_access called listing_id=%s wallet_type=%s",
        listing_id,
        request.wallet_type,
    )
    wallet_id_bytes = contract_service.wallet_id(
        request.wallet_type, request.address, settings
    )
    return AccessCheckResponse(
        has_access=contract_service.has_access(listing_id, wallet_id_bytes, settings)
    )


@router.post("/items/{listing_id}/grant-access", response_model=TxHashResponse)
def grant_access(
    listing_id: str,
    request: GrantAccessRequest,
    settings: Settings = Depends(get_settings),
) -> TxHashResponse:
    """Grant listing access for a wallet on-chain.

    Args:
        listing_id (str): Listing UUID string
        request (GrantAccessRequest): Grant access request model
        settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).

    Returns:
        TxHashResponse: Transaction hash response
    """
    wallet_id_bytes = contract_service.wallet_id(
        request.wallet_type, request.address, settings
    )
    tx_hash = contract_service.grant_access(listing_id, wallet_id_bytes, settings)
    return TxHashResponse(tx_hash=tx_hash)


@router.patch("/fee-config", response_model=TxHashResponse)
def set_fee_config(
    request: SetFeeConfigRequest, settings: Settings = Depends(get_settings)
) -> TxHashResponse:
    """Update fee recipient and fee bps in the contract.

    Args:
        request (SetFeeConfigRequest): Set fee config request model
        settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).

    Returns:
        TxHashResponse: Transaction hash response
    """
    tx_hash = contract_service.set_fee_config(
        request.fee_recipient, request.fee_bps, settings
    )
    return TxHashResponse(tx_hash=tx_hash)


@router.post("/ownership/transfer", response_model=TxHashResponse)
def transfer_ownership(
    request: TransferOwnershipRequest,
    settings: Settings = Depends(get_settings),
) -> TxHashResponse:
    """Transfer contract ownership.

    Args:
        request (TransferOwnershipRequest): Transfer ownership request model
        settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).

    Returns:
        TxHashResponse: Transaction hash response
    """
    tx_hash = contract_service.transfer_ownership(request.new_owner, settings)
    return TxHashResponse(tx_hash=tx_hash)


@router.post("/ownership/renounce", response_model=TxHashResponse)
def renounce_ownership(settings: Settings = Depends(get_settings)) -> TxHashResponse:
    """Renounce contract ownership.

    Args:
        settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).

    Returns:
        TxHashResponse: Transaction hash response
    """
    tx_hash = contract_service.renounce_ownership(settings)
    return TxHashResponse(tx_hash=tx_hash)
