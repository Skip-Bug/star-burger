from django.http import JsonResponse
from django.templatetags.static import static
from phonenumbers import NumberParseException, is_valid_number, parse
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer

from .models import Order, OrderItem, Product


def validate_phone(phone):
    try:
        parsed = parse(phone, "RU")
        return is_valid_number(parsed)
    except NumberParseException:
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


class OrderItemSerializer(ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["product", "quantity"]


class OrderSerializer(ModelSerializer):
    firstname = serializers.CharField(
        source="client_first_name",
        required=True,
    )
    lastname = serializers.CharField(
        source="client_last_name",
        required=True,
    )
    address = serializers.CharField(
        source="client_address",
        required=True,
    )
    phonenumber = serializers.CharField(
        source="phone_number",
        required=True,
    )
    products = OrderItemSerializer(
        many=True,
        source="items",
        required=True,
        write_only=True,
    )

    class Meta:
        model = Order
        fields = [
            "firstname",
            "lastname",
            "phonenumber",
            "address",
            "products",
        ]

    def validate_phonenumber(self, value):
        if not validate_phone(value):
            raise serializers.ValidationError("Введен некорректный номер телефона.")
        return value

    def validate_products(self, value):
        if not value:
            raise serializers.ValidationError("Этот список не может быть пустым.")
        return value


@api_view(["POST"])
def register_order(request):

    serializer = OrderSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    validated = serializer.validated_data

    order = Order.objects.create(
        client_first_name=validated["client_first_name"],
        client_last_name=validated["client_last_name"],
        phone_number=validated["phone_number"],
        client_address=validated["client_address"],
    )

    for item in validated["items"]:
        OrderItem.objects.create(
            order=order,
            product=item["product"],
            quantity=item["quantity"],
            price=item["product"].price,
        )

    response_serializer = OrderSerializer(order)

    return Response(response_serializer.data, status=201)
