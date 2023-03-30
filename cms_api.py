import os
from datetime import datetime

import requests
from slugify import slugify


def get_access_token(client_id: str):
    data = {
        'client_id': client_id,
        'client_secret': os.environ.get('CLIENT_SECRET'),
        'grant_type': os.environ.get('GRANT_TYPE')
    }

    response_access_token = requests.post(
        'https://api.moltin.com/oauth/access_token', data=data
    )
    response_access_token.raise_for_status()

    assess_token = response_access_token.json()
    os.environ.setdefault('MOLTIN_TOKEN_EXPIRES_TIME', str(assess_token['expires']))
    os.environ.setdefault('ACCESS_TOKEN', assess_token['access_token'])


def check_access_token(client_id: str):
    token_expires_time = os.environ.get('MOLTIN_TOKEN_EXPIRES_TIME')
    timestamp = int(datetime.now().timestamp())
    if not token_expires_time or int(token_expires_time) < timestamp:
        get_access_token(client_id)


def get_access_header_data(client_id: str):
    check_access_token(client_id)
    access_token = os.getenv('ACCESS_TOKEN')
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    return headers


def get_product_by_id(client_id: str, product_id: int):
    headers = get_access_header_data(client_id)
    product_data = requests.get(f'https://api.moltin.com/pcm/products/{product_id}',
                                headers=headers)
    product_data.raise_for_status()
    return product_data['data']


def create_file(headers: str, image_url: str) -> str:
    response_create_file = requests.post(
        'https://api.moltin.com/v2/files/',
        headers=headers,
        files={
            'file_location': (None, image_url),
            'file_name': 'Some_file_name.jpg'
        }
    )
    file_id = response_create_file.json()['data']['id']
    return file_id


def add_image_to_product(headers, product_id, file_id):
    json_data = {
        'data': {
            "type": "main_image",
            "id": file_id
        },
    }

    requests.post(
        f'https://api.moltin.com/v2/products/{product_id}/relationships/main-image',
        headers=headers,
        json=json_data
    )


def create_product(client_id: str, products):
    headers = get_access_header_data(client_id)

    for product in products:
        json_data = {
            'data': {
                'type': 'product',
                'name': product['name'],
                'slug': slugify(product['name']),
                'sku': slugify(product['name']),
                'description': product['description'],
                'manage_stock': False,
                'price': [
                    {
                        'amount': product['price'],
                        'currency': 'RUB',
                        'includes_tax': True,
                    },
                ],
                'status': 'live',
                'commodity_type': 'physical',
            },
        }

        response_create_product = requests.post(
            'https://api.moltin.com/v2/products',
            headers=headers,
            json=json_data
        )

        response_create_product = response_create_product.json()
        product_id = response_create_product['data']['id']

        file_id = create_file(headers=headers,
                              image_url=product['product_image']['url'])

        add_image_to_product(headers=headers,
                             product_id=product_id,
                             file_id=file_id)


def create_flow(headers, json_data):
    response_create_flow = requests.post(
        'https://api.moltin.com/v2/flows',
        headers=headers,
        json=json_data
    )
    response_create_flow.raise_for_status()
    return response_create_flow.json()['data']['id']


def create_flow_fields(headers, json_data):
    response_create_flow_field = requests.post(
        'https://api.moltin.com/v2/fields',
        headers=headers,
        json=json_data
    )

    response_create_flow_field.raise_for_status()


def create_pizzeria_addresses_flow(client_id: str, flow_name: str):
    headers = get_access_header_data(client_id)

    flow_data = {
        'data': {
            'type': 'flow',
            'name': flow_name,
            'slug': flow_name,
            'description': 'Addresses of our pizzerias',
            'enabled': True,
        },
    }

    flow_id = create_flow(headers, flow_data)
    flow_fields = ['Address', 'Alias', 'Longitude', 'Latitude']

    for flow_field in flow_fields:
        field_data = {
            'data': {
                'type': 'field',
                'name': flow_field,
                'slug': slugify(flow_field),
                'field_type': 'string',
                'description': f'{flow_field} field description',
                'required': False,
                'unique': False,
                'enabled': True,
                'relationships': {
                    'flow': {
                        'data': {
                            'type': 'flow',
                            'id': flow_id,
                        },
                    },
                },
            },
        }
        create_flow_fields(headers, field_data)


def add_addresses_to_flow(client_id, addresses, flow_name):
    headers = get_access_header_data(client_id)
    for address in addresses:
        address_data = {
            'data': {
                'type': 'entry',
                'address': address['address']['full'],
                'alias': address['alias'],
                'longitude': address['coordinates']['lon'],
                'latitude': address['coordinates']['lat']
            },
        }

        requests.post(
            f'https://api.moltin.com/v2/flows/{flow_name}/entries',
            headers=headers,
            json=address_data
        )
    print('Add entries is complete')


def get_products(client_id):
    headers = get_access_header_data(client_id)

    products_data = requests.get(f'https://api.moltin.com/v2/products/',
                                 headers=headers)
    products_data.raise_for_status()

    products_data = products_data.json()
    products = [{"id": product["id"], "name": product["name"]} for product in products_data["data"]]
    return products


def get_product(product_id, client_id):
    headers = get_access_header_data(client_id)

    product_data = requests.get(f'https://api.moltin.com/v2/products/{product_id}',
                                headers=headers)
    product_data.raise_for_status()
    product_data = product_data.json()["data"]

    file_id = product_data["relationships"]["main_image"]["data"]["id"]
    image_data = get_file_by_id(headers, file_id, client_id)

    product = {
        "file_id": file_id,
        "image_path": image_data["data"]["link"]["href"],
        "name": product_data["name"],
        "description": product_data["description"],
        "price": product_data["meta"]["display_price"]["with_tax"]["formatted"],
        "stock": product_data["meta"]["stock"]["level"]
    }

    return product


def get_file_by_id(headers, file_id: str, client_id: str):
    file_data = requests.get(f'https://api.moltin.com/v2/files/{file_id}',
                             headers=headers)
    file_data.raise_for_status()
    return file_data.json()


def create_user_account(name: str, email: str, client_id: str):
    headers = get_access_header_data(client_id)

    json_data = {
        'data': {
            'type': 'customer',
            'name': name,
            'email': email,
        },
    }

    response_create_customer = requests.post(
        'https://api.moltin.com/v2/customers',
        headers=headers,
        json=json_data
    )
    response_create_customer.raise_for_status()


def add_to_cart(cart_id: str, product_id: str, quantity: int, client_id: str):
    headers = get_access_header_data(client_id)

    cart_data = {
        "data": {
            "id": product_id,
            "type": "cart_item",
            "quantity": quantity
        }
    }
    cart = requests.post(f'https://api.moltin.com/v2/carts/{cart_id}/items',
                         json=cart_data,
                         headers=headers)
    cart.raise_for_status()


def get_cart(cart_id: str, client_id: str):
    headers = get_access_header_data(client_id)

    cart_response = requests.get(f'https://api.moltin.com/v2/carts/{cart_id}',
                                 headers=headers)
    cart_response.raise_for_status()
    cart_items_response = requests.get(f'https://api.moltin.com/v2/carts/{cart_id}/items',
                                       headers=headers)
    cart_items_response.raise_for_status()

    cart = []
    for cart_items in cart_items_response.json()["data"]:
        cart_item = {
            "id": cart_items["id"],
            "name": cart_items["name"],
            "description": cart_items["description"],
            "price": cart_items["unit_price"]["amount"],
            "quantity": cart_items["quantity"],
            "amount": cart_items["value"]["amount"]
        }
        cart.append(cart_item)

    full_amount = cart_response.json()["data"]["meta"]["display_price"]["with_tax"]["amount"]
    return {"cart_items": cart, "full_amount": full_amount}


def delete_from_cart(cart_id: str, product_id: str, client_id: str):
    headers = get_access_header_data(client_id)

    cart_delete_response = requests.delete(f'https://api.moltin.com/v2/carts/{cart_id}/items/{product_id}',
                                           headers=headers)
    cart_delete_response.raise_for_status()


def get_addresses(client_id: str, flow_slug: str):
    headers = get_access_header_data(client_id)
    addresses_response = requests.get(
        f'https://api.moltin.com/v2/flows/{flow_slug}/entries',
        headers=headers
    )
    addresses_data = addresses_response.json()
    addresses = [{"address": address["address"],
                  "coordinate": (float(address['longitude']), float(address['latitude']))}
                 for address in addresses_data["data"]]
    return addresses
