from django.db.models import Count

from foodcartapp.models import Restaurant, RestaurantMenuItem

import requests
from django.db.models import Count

from foodcartapp.models import Location, Restaurant, RestaurantMenuItem
from star_burger import settings


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
    found_places = response.json(
    )["response"]["GeoObjectCollection"]["featureMember"]

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
        else:
            pass

    return location


def get_restaurants_for_order(order):

    product_ids = order.items.values_list("product_id", flat=True)
    if not product_ids:
        return Restaurant.objects.none()

    restaurant_ids = (
        RestaurantMenuItem.objects.filter(
            product_id__in=product_ids, availability=True)
        .values("restaurant_id")
        .annotate(matched_count=Count("product_id"))
        .filter(matched_count=len(product_ids))
        .values_list("restaurant_id", flat=True)
    )

    return Restaurant.objects.filter(id__in=restaurant_ids)
