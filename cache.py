import cms_api
from db import get_database_connection

def create_menu(category):
    products = cms_api.get_products_by_category(category)
    products_with_details = [cms_api.get_product(product_id=product["id"])
                             for product in products]
    return {"menu": products_with_details}


def cache_menu():
    client = get_database_connection()
    categories = cms_api.get_categories()
    for category in categories:
        menu = create_menu(category["slug"])
        client.set(category["slug"], str(menu))


if __name__ == '__main__':
    cache_menu()