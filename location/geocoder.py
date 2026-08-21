import requests
from django.conf import settings

from .models import Location


def get_coordinates_for_addresses(addresses):
    addresses = set(addresses)
    existing = {
        loc.address: loc for loc in Location.objects.filter(address__in=addresses)
    }
    result = {}
    for address in addresses:
        loc = existing.get(address)
        if loc and loc.lat is not None and loc.lon is not None:
            result[address] = (loc.lat, loc.lon)
        else:
            loc = get_or_create_location(address)
            if loc and loc.lat is not None and loc.lon is not None:
                result[address] = (loc.lat, loc.lon)
            else:
                result[address] = None
    return result


def fetch_coordinates(apikey, address):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(
        base_url,
        params={
            "geocode": address,
            "apikey": apikey,
            "format": "json",
        },
    )
    response.raise_for_status()
    try:
        data = response.json()
    except ValueError:
        raise requests.exceptions.HTTPError("Ответ сервера не является корректным JSON")

    if "error" in data:
        raise requests.exceptions.HTTPError(data["error"])

    found_places = response.json()["response"]["GeoObjectCollection"]["featureMember"]

    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant["GeoObject"]["Point"]["pos"].split(" ")
    return lon, lat


def get_or_create_location(address):
    location, created = Location.objects.get_or_create(address=address)
    if created or location.lat is None or location.lon is None:
        coords = fetch_coordinates(settings.YANDEX_API_KEY, address)
        if coords:
            lon, lat = coords
            location.lat = float(lat)
            location.lon = float(lon)
            location.save(update_fields=["lat", "lon"])
    return location
