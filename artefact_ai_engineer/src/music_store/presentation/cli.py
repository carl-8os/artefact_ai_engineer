"""Command-line interface for the customer service agent and offline verification."""
import argparse
import os
from pathlib import Path
from music_store.application.agent import MusicStoreAgent
from music_store.application.catalog import SearchCatalog
from music_store.application.orders import OrderLookup
from music_store.infrastructure.csv_catalog import CsvCatalogRepository
from music_store.infrastructure.csv_orders import CsvOrderRepository
from music_store.infrastructure.openai_model import ModelError
from music_store.infrastructure.model_factory import create_model


def check_data(directory: Path) -> None:
    catalog = CsvCatalogRepository(directory)
    orders = CsvOrderRepository(directory)
    products = catalog.list_products()
    promotions = catalog.list_promotions()
    if not products:
        raise ValueError('Catalog is empty')
    product_ids = {p.id for p in products}
    if len(product_ids) != len(products):
        raise ValueError('Duplicate product IDs')
    if any(p.product_id not in product_ids for p in promotions):
        raise ValueError('Promotion references unknown product')
    for product_id in product_ids:
        if sum(p.active for p in promotions if p.product_id == product_id) > 1:
            raise ValueError(f'Multiple active promotions for product {product_id}')
    # Check order CSV readability, without exposing customer details.
    from music_store.infrastructure.csv_files import resolve_csv
    import csv
    with resolve_csv(directory, 'orders').open(encoding='utf-8-sig', newline='') as handle:
        ids = [int(row['order_id']) for row in csv.DictReader(handle)]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate order IDs')
    for order_id in ids:
        if orders.get_order(order_id) is None or not orders.list_items(order_id):
            raise ValueError(f'Order {order_id} missing or has no items')
    print(f'OK: {len(products)} products, {len(promotions)} promotions, {len(ids)} orders; no customer data printed.')


def main():
    parser = argparse.ArgumentParser(description='Emporio Music Store AI customer service')
    parser.add_argument('--data', type=Path, default=Path('data'), help='Directory with the six original private CSVs (default: data)')
    parser.add_argument('--check-data', action='store_true', help='Validate data without API key or network')
    args = parser.parse_args()
    try:
        if args.check_data:
            check_data(args.data)
            return
        check_data(args.data)
        model = create_model()
        from music_store.presentation.web import _policy_search
        agent = MusicStoreAgent(SearchCatalog(CsvCatalogRepository(args.data)), OrderLookup(CsvOrderRepository(args.data)), model, policy_search=_policy_search())
    except (ValueError, FileNotFoundError) as exc:
        parser.exit(2, f'Configuration error: {exc}\n')
    print("Emporio Music Store | Type 'exit' to quit")
    history: list[dict] = []
    while True:
        try:
            message = input('You: ').strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if message.casefold() in {'sair', 'exit', 'quit'}:
            break
        if not message:
            continue
        try:
            reply = agent.respond(message, history=history)
            print('Assistant:', reply)
            history.extend([{'role': 'user', 'content': message}, {'role': 'assistant', 'content': reply}])
            history = history[-16:]
        except (ModelError, ValueError) as exc:
            print(f'Agent request failed: {exc}')


if __name__ == '__main__':
    main()
