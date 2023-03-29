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


def get_header_data(client_id: str):
    check_access_token(client_id)
    access_token = os.getenv('ACCESS_TOKEN')
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    return headers


def get_product_by_id(client_id: str, product_id: int):
    headers = get_header_data(client_id)
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
    headers = get_header_data(client_id)

    json_data = {
        'data': {
            'type': 'product',
            'name': products[0]['name'],
            'slug': slugify(products[0]['name']),
            'sku': slugify(products[0]['name']),
            'description': products[0]['description'],
            'manage_stock': False,
            'price': [
                {
                    'amount': products[0]['price'],
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
                          image_url=products[0]['product_image']['url'])

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


def create_pizzeria_addresses_flow(client_id: str, flow_name:str):
    headers = get_header_data(client_id)

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
    headers = get_header_data(client_id)
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
