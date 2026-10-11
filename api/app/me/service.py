"""Wallet-scoped reads. Indexer tables serve when synced; otherwise the
existing contract read paths do, so the endpoints work with the indexer off."""

import logging
from collections import defaultdict
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select
from web3 import Web3

from ..auth.dependencies import AuthedWallet
from ..config.settings import Settings
from ..contracts import service as contract_service
from ..indexer.models import IndexedListing, IndexedPurchase
from ..indexer.service import synced_state
from .schemas import PurchasedListing, SellerListing

logger = logging.getLogger(__name__)

_CONTRACT_PAGE = 500


def _checksum(address: str) -> str:
    return Web3.to_checksum_address(address)


def _symbol(token: str, settings: Settings, decimals: int) -> str:
    return contract_service._settlement_currency_for_token(token, settings, decimals)


def _indexed_purchases(
    session: Session, wallet: AuthedWallet, settings: Settings
) -> list[PurchasedListing] | None:
    try:
        if synced_state(session, settings) is None:
            return None
        purchases = session.exec(
            select(IndexedPurchase)
            .where(IndexedPurchase.buyer == _checksum(wallet.address))
            .order_by(
                IndexedPurchase.block_number.desc(),  # type: ignore[attr-defined]
                IndexedPurchase.log_index.desc(),  # type: ignore[attr-defined]
            )
        ).all()
        latest: dict[str, IndexedPurchase] = {}
        for purchase in purchases:
            latest.setdefault(purchase.listing_id, purchase)
        listings = {
            row.listing_id: row
            for row in session.exec(
                select(IndexedListing).where(
                    IndexedListing.listing_id.in_(list(latest))  # type: ignore[attr-defined]
                )
            ).all()
        }
    except SQLAlchemyError:
        logger.exception("Indexed /me/purchases read failed; falling back to contract")
        return None

    result = []
    for listing_id, purchase in latest.items():
        listing = listings.get(listing_id)
        if listing is None:
            logger.warning("Indexed purchase references unknown listing %s", listing_id)
            continue
        result.append(
            PurchasedListing(
                listing_id=listing_id,
                title=listing.title,
                description=listing.description,
                price_paid=str(int(purchase.price_paid)),
                payment_token=purchase.payment_token,
                token_symbol=_symbol(
                    purchase.payment_token, settings, listing.payment_token_decimals
                ),
                token_decimals=listing.payment_token_decimals,
                purchased_at=purchase.block_time,
                source="indexer",
            )
        )
    return result


def get_purchases(
    session: Session, wallet: AuthedWallet, settings: Settings
) -> list[PurchasedListing]:
    indexed = _indexed_purchases(session, wallet, settings)
    if indexed is not None:
        return indexed
    _, items = contract_service.get_purchased_items_by_wallet(
        wallet.wallet_type, wallet.address, settings, limit=_CONTRACT_PAGE
    )
    return [
        PurchasedListing(
            listing_id=item.id,
            title=item.title,
            description=item.description,
            # The contract path has no per-purchase amount; the current price
            # is the best available figure.
            price_paid=item.price_atomic,
            payment_token=item.payment_token,
            token_symbol=item.settlement_currency,
            token_decimals=item.settlement_decimals,
            purchased_at=None,
            source="contract",
        )
        for item in items
    ]


def _indexed_listings(
    session: Session, wallet: AuthedWallet, settings: Settings
) -> list[SellerListing] | None:
    try:
        if synced_state(session, settings) is None:
            return None
        rows = session.exec(
            select(IndexedListing)
            .where(IndexedListing.seller == _checksum(wallet.address))
            .order_by(
                IndexedListing.created_block,  # type: ignore[arg-type]
                IndexedListing.created_log_index,  # type: ignore[arg-type]
            )
        ).all()
        ids = [row.listing_id for row in rows]
        purchases = (
            session.exec(
                select(IndexedPurchase).where(
                    IndexedPurchase.listing_id.in_(ids)  # type: ignore[attr-defined]
                )
            ).all()
            if ids
            else []
        )
    except SQLAlchemyError:
        logger.exception("Indexed /me/listings read failed; falling back to contract")
        return None

    sales: dict[str, int] = defaultdict(int)
    earned: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for purchase in purchases:
        sales[purchase.listing_id] += 1
        earned[purchase.listing_id][purchase.payment_token] += purchase.seller_paid

    return [
        SellerListing(
            listing_id=row.listing_id,
            title=row.title,
            price=str(int(row.price)),
            payment_token=row.payment_token,
            token_symbol=_symbol(row.payment_token, settings, row.payment_token_decimals),
            token_decimals=row.payment_token_decimals,
            sales_count=sales[row.listing_id],
            earnings_by_token={
                token: str(int(total)) for token, total in earned[row.listing_id].items()
            },
            price_editable=sales[row.listing_id] == 0 and not row.frozen,
            source="indexer",
        )
        for row in rows
    ]


def get_seller_listings(
    session: Session, wallet: AuthedWallet, settings: Settings
) -> list[SellerListing]:
    indexed = _indexed_listings(session, wallet, settings)
    if indexed is not None:
        return indexed
    seller = _checksum(wallet.address)
    return [
        SellerListing(
            listing_id=item.id,
            title=item.title,
            price=item.price_atomic,
            payment_token=item.payment_token,
            token_symbol=item.settlement_currency,
            token_decimals=item.settlement_decimals,
            sales_count=item.purchase_count,
            earnings_by_token={},
            price_editable=item.purchase_count == 0,
            source="contract",
        )
        for item in contract_service.get_all_items(settings)
        if str(item.seller).lower() == seller.lower()
    ]
