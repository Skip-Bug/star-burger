from django.http import JsonResponse
from django.templatetags.static import static
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

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


@api_view(["POST"])
def register_order(request):
    order_info = request.data

    firstname = order_info.get("firstname")
    lastname = order_info.get("lastname", "")
    phonenumber = order_info.get("phonenumber")
    address = order_info.get("address")
    if not firstname or not phonenumber or not address:
        return Response(
            {"error": "Имя, телефон и адрес обязательны"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    products = order_info.get("products")

    if "products" not in order_info:
        return Response(
            {"error": "products: Обязательное поле."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if products is None:
        return Response(
            {"error": "products: Это поле не может быть пустым."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not isinstance(products, list):
        return Response(
            {"error": "products: Ожидался list со значениями, но был получен 'str'"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if len(products) == 0:
        return Response(
            {"error": "products: Этот список не может быть пустым."},
            status=status.HTTP_400_BAD_REQUEST,
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
            return Response(
                {"error": "Неверный товар или количество"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        menu_item = RestaurantMenuItem.objects.filter(
            product_id=product_id, availability=True
        ).first()
        if not menu_item:
            return Response(
                {"error": f"Товар с id {product_id} недоступен ни в одном ресторане"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        OrderItem.objects.create(
            order=order,
            restaurant_menu_item=menu_item,
            quantity=quantity,
        )

    return Response(
        {"status": "ok", "order_id": order.id}, status=status.HTTP_201_CREATED
    )
