import os

import redis
import requests
from geopy import distance

import cms_api

ADDRESSES_URL = 'https://dvmn.org/media/filer_public/90/90/9090ecbf-249f-42c7-8635-a96985268b88/addresses.json'
MENU_URl = 'https://dvmn.org/media/filer_public/a2/5a/a25a7cbd-541c-4caf-9bf9-70dcdf4a592e/menu.json'

_database = None


def read_data(url: str):
    response = requests.get(url)
    return response.json()


def init_data(client_id):
    products = read_data(MENU_URl)
    addresses = read_data(ADDRESSES_URL)
    cms_api.get_addresses(client_id, 'Pizzeria')
    cms_api.create_product(client_id, products)

    cms_api.create_pizzeria_addresses_flow(client_id, 'Pizzeria')
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
        cms_api.add_addresses_to_flow(client_id, address_data, 'Pizzeria')


def fetch_coordinates(address):
    apikey = os.environ.get("API_YANDEX_GEO_KEY")
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(base_url, params={
        "geocode": address,
        "apikey": apikey,
        "format": "json",
    })
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection']['featureMember']

    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return float(lon), float(lat)


def get_min_distance(client_id, current_pos):
    pizzerias_addresses = cms_api.get_addresses(client_id=client_id, flow_slug='Pizzeria')
    distances_to_pizzerias = {pizzerias_address['address']:
        (
            distance.distance(current_pos, pizzerias_address['coordinate']).km,
            pizzerias_address['telegram_id_delieveryman']
        )
        for pizzerias_address in pizzerias_addresses}

    min_distance = min(distances_to_pizzerias.items(), key=lambda x: x[1])
    return min_distance


def get_database_connection():
    global _database
    if _database is None:
        database_password = os.environ.get("DATABASE_PASSWORD")
        database_host = os.environ.get("DATABASE_HOST")
        database_port = os.environ.get("DATABASE_PORT")

        _database = redis.Redis(host=database_host, port=database_port, password=database_password)
    return _database
