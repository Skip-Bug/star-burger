import json

from django.http import JsonResponse
from django.templatetags.static import static

from .models import Order, OrderItem, Product, RestaurantMenuItem


def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse(
        [
            {
                "title": "Burger",
                "src": static("burger.jpg"),
                "text": "Tasty Burger at your door step",
            },
            {
                "title": "Spices",
                "src": static("food.jpg"),
                "text": "All Cuisines",
            },
            {
                "title": "New York",
                "src": static("tasty.jpg"),
                "text": "Food is incomplete without a tasty dessert",
            },
        ],
        safe=False,
        json_dumps_params={
            "ensure_ascii": False,
            "indent": 4,
        },
    )


def product_list_api(request):
    products = Product.objects.select_related("category").available()

    dumped_products = []
    for product in products:
        dumped_product = {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "special_status": product.special_status,
            "description": product.description,
            "category": {
                "id": product.category.id,
                "name": product.category.name,
            }
            if product.category
            else None,
            "image": product.image.url,
            "restaurant": {
                "id": product.id,
                "name": product.name,
            },
        }
        dumped_products.append(dumped_product)
    return JsonResponse(
        dumped_products,
        safe=False,
        json_dumps_params={
            "ensure_ascii": False,
            "indent": 4,
        },
    )


def register_order(request):
    try:
        order_info = json.loads(request.body.decode())
    except ValueError:
        return JsonResponse(
            {"error": "Неверный JSON"},
            status=400,
        )

    firstname = order_info.get("firstname")
    lastname = order_info.get("lastname", "")
    phonenumber = order_info.get("phonenumber")
    address = order_info.get("address")
    if not firstname or not phonenumber or not address:
        return JsonResponse(
            {"error": "Имя, телефон и адрес обязательны"},
            status=400,
        )

    products = order_info.get("products")
    if not products:
        return JsonResponse(
            {"error": "Нет товаров в заказе"},
            status=400,
        )

    order = Order.objects.create(
        client_first_name=firstname,
        client_last_name=lastname,
        phone_number=phonenumber,
        client_address=address,
    )
    for item in products:
        product_id = item.get("product")
        quantity = item.get("quantity")
        if not product_id or quantity is None or quantity < 1:
            return JsonResponse(
                {"error": "Неверный товар или количество"},
                status=400,
            )
        menu_item = RestaurantMenuItem.objects.filter(
            product_id=product_id, availability=True
        ).first()
        if not menu_item:
            return JsonResponse(
                {"error": f"Товар с id {product_id} недоступен ни в одном ресторане"},
                status=400,
            )

        OrderItem.objects.create(
            order=order,
            restaurant_menu_item=menu_item,
            quantity=quantity,
        )

    return JsonResponse({"status": "ok", "order_id": order.id})
