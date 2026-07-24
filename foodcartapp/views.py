from django.http import JsonResponse
from django.templatetags.static import static
from phonenumbers import is_valid_number, parse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Order, OrderItem, Product, RestaurantMenuItem


def validate_phone(phone):
    try:
        parsed = parse(phone, "RU")
        return is_valid_number(parsed)
    except:
        return False


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

    required_keys = ["firstname", "lastname", "phonenumber", "address"]
    missing = []
    for key in required_keys:
        if key not in order_info:
            missing.append(key)
    if missing:
        return Response(
            {"error": f"{', '.join(missing)}: Обязательное поле."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    empty_fields = []
    for field in ["firstname", "lastname", "phonenumber", "address"]:
        value = order_info[field]
        if value is None or value == "":
            empty_fields.append(field)
    if empty_fields:
        return Response(
            {"error": f"{', '.join(empty_fields)}: Это поле не может быть пустым."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    for field in required_keys:
        if not isinstance(order_info[field], str):
            return Response(
                {"error": f"{field}: Not a valid string."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    firstname = order_info["firstname"]
    lastname = order_info["lastname"]
    phonenumber = order_info["phonenumber"]
    address = order_info["address"]

    if not validate_phone(phonenumber):
        return Response(
            {"error": "phonenumber: Введен некорректный номер телефона."},
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
        if product_id is None:
            return Response(
                {"error": "Неверный товар"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if quantity is None or quantity < 1:
            return Response(
                {"error": "Не верное количество количество"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not Product.objects.filter(id=product_id).exists():
            return Response(
                {"error": f"products: Недопустимый первичный ключ '{product_id}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        menu_item = RestaurantMenuItem.objects.filter(
            product_id=product_id, availability=True
        ).first()
        if not menu_item:
            return Response(
                {"error": f"Товар с id {product_id} недоступен ни в одном ресторане."},
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
