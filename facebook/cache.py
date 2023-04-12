import cms_api
import json
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
    client.quit()

def get_menu(category):
    client = get_database_connection()
    cached_menu = client.get(category)
    # client.quit()
    json_acceptable_string = cached_menu.replace("'", "\"")
    return json.loads(json_acceptable_string)
