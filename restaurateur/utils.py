from collections import defaultdict

from geopy.distance import geodesic

from foodcartapp.models import RestaurantMenuItem


def get_order_products_map(order_items):
    """
    Возвращает словарь {order_id: set(product_ids)} для всех заказов,
    а также множество всех уникальных product_id.
    """
    order_products_map = {}
    all_product_ids = set()
    for order in order_items:
        product_ids = {item.product_id for item in order.items.all()}
        order_products_map[order.id] = product_ids
        all_product_ids.update(product_ids)
    return order_products_map, all_product_ids


def get_restaurant_products_map(product_ids):
    """
    Возвращает кортеж (restaurant_products, restaurants_map)
    restaurant_products: dict {restaurant_id: set(product_ids)}
    restaurants_map: dict {restaurant_id: Restaurant object}
    """
    menu_items = RestaurantMenuItem.objects.filter(
        product_id__in=product_ids, availability=True
    ).select_related("restaurant")
    restaurant_products = defaultdict(set)
    restaurants_map = {}
    for item in menu_items:
        rest = item.restaurant
        restaurant_products[rest.id].add(item.product_id)
        restaurants_map[rest.id] = rest
    return restaurant_products, restaurants_map


def find_suitable_restaurants(
    order_items,
    order_products_map,
    restaurant_products,
    restaurants_map,
):
    """
    Для каждого заказа возвращает словарь {order_id: list(Restaurant)},
    где рестораны могут приготовить все продукты заказа.
    """
    suitable_by_order = {}
    for order in order_items:
        if order.restaurant:
            suitable_by_order[order.id] = [order.restaurant]
            continue

        order_product_ids = order_products_map.get(order.id, set())
        if not order_product_ids:
            suitable_by_order[order.id] = []
            continue

        suitable = []
        for rest_id, rest_products in restaurant_products.items():
            if rest_products.issuperset(order_product_ids):
                suitable.append(restaurants_map[rest_id])
        suitable_by_order[order.id] = suitable

    return suitable_by_order


def collect_addresses(order_items, suitable_by_order):
    """
    Собирает все адреса клиентов и ресторанов из заказов и подходящих ресторанов.
    """
    addresses = set()
    for order in order_items:
        addresses.add(order.client_address)
        suitable = suitable_by_order.get(order.id, [])
        for restaurant in suitable:
            addresses.add(restaurant.address)
    return addresses


def compute_distances_for_orders(order_items, coordinates, suitable_by_order):
    """
    Для каждого заказа вычисляет расстояния до подходящих ресторанов.
    Устанавливает:
      - order.client_coords_not_found (bool) – если координаты клиента не найдены
      - order.available_restaurants (list of (restaurant, dist)) – отсортировано по расстоянию
    """
    for order in order_items:
        if order.restaurant:
            continue

        client_coords = coordinates.get(order.client_address)
        order.client_coords_not_found = client_coords is None

        suitable_restaurants = suitable_by_order.get(order.id, [])

        restaurants_with_dist = []
        for restaurant in suitable_restaurants:
            rest_coords = coordinates.get(restaurant.address)
            dist = None
            if client_coords and rest_coords:
                dist = round(geodesic(client_coords, rest_coords).km, 1)
            restaurants_with_dist.append((restaurant, dist))

        restaurants_with_dist.sort(key=lambda item: (item[1] is None, item[1]))
        order.available_restaurants = restaurants_with_dist
