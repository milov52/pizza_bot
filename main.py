import os
import requests
from dotenv import load_dotenv

from cms_api import create_pizzeria_addresses_flow, create_product, add_addresses_to_flow


ADDRESSES_URL = 'https://dvmn.org/media/filer_public/90/90/9090ecbf-249f-42c7-8635-a96985268b88/addresses.json'
MENU_URl = 'https://dvmn.org/media/filer_public/a2/5a/a25a7cbd-541c-4caf-9bf9-70dcdf4a592e/menu.json'

def read_data(url:str):
    response = requests.get(url)
    return response.json()

def init_data(client_id):
    products = read_data(MENU_URl)
    addresses = read_data(ADDRESSES_URL)

    create_product(client_id, products)
    create_pizzeria_addresses_flow(client_id, 'Pizzeria')
    add_addresses_to_flow(client_id, addresses, 'Pizzeria')


if __name__ == '__main__':
    load_dotenv()
    client_id = os.environ.get("CLIENT_ID")

    #init_data(client_id)

