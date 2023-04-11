import cms_api
import json

def create_menu(category):
    products = cms_api.get_products_by_category(category)
    products_with_details = [cms_api.get_product(product_id=product["id"])
                             for product in products]
    return {"menu": products_with_details}


def cache_menu(db):
    categories = cms_api.get_categories()
    for category in categories:
        menu = create_menu(category["slug"])
        db.set(category["slug"], str(menu))

def get_menu(db):
    cached_menu = db.get("front_page")
    json_acceptable_string = cached_menu.replace("'", "\"")
    return json.loads(json_acceptable_string)
