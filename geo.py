import os

import requests
from geopy import distance

import cms_api


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


def get_min_distance(current_pos):
    pizzerias_addresses = cms_api.get_addresses(flow_slug='Pizzeria')
    distances_to_pizzerias = {pizzerias_address['address']:
        (
            distance.distance(current_pos, pizzerias_address['coordinate']).km,
            pizzerias_address['telegram_id_delieveryman']
        )
        for pizzerias_address in pizzerias_addresses}

    min_distance = min(distances_to_pizzerias.items(), key=lambda x: x[1])
    return min_distance