from django.db.models import Count

from foodcartapp.models import Restaurant, RestaurantMenuItem


def get_restaurants_for_order(order):

    product_ids = order.items.values_list("product_id", flat=True)
    if not product_ids:
        return Restaurant.objects.none()

    restaurant_ids = (
        RestaurantMenuItem.objects.filter(
            product_id__in=product_ids,
            availability=True,
        )
        .values("restaurant_id")
        .annotate(matched_count=Count("product_id"))
        .filter(matched_count=len(product_ids))
        .values_list("restaurant_id", flat=True)
    )

    return Restaurant.objects.filter(id__in=restaurant_ids)
