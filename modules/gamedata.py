# https://github.com/dixon2004/python-tf2-utilities/
import requests, vdf
def get_items_game() -> dict:
    response = requests.get('https://raw.githubusercontent.com/SteamDatabase/GameTracking-TF2/master/tf/scripts/items/items_game.txt', timeout=10)
    if response.status_code == 200:
        return vdf.loads(response.text.replace('\x00', ''))["items_game"]
    else:
        raise Exception("Failed to get items_game.txt.")
items_game=get_items_game()