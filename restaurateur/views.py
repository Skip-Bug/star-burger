from django import forms
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Case, IntegerField, Value, When
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View

from foodcartapp.models import Order, Product, Restaurant
from location.geocoder import get_coordinates_for_addresses
from restaurateur.utils import (
    collect_addresses,
    compute_distances_for_orders,
    find_suitable_restaurants,
    get_order_products_map,
    get_restaurant_products_map,
)


class Login(forms.Form):
    username = forms.CharField(
        label="Логин",
        max_length=75,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Укажите имя пользователя"}
        ),
    )
    password = forms.CharField(
        label="Пароль",
        max_length=75,
        required=True,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Введите пароль"}
        ),
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, "login.html", context={"form": form})

    def post(self, request):
        form = Login(request.POST)

        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff:  # FIXME replace with specific permission
                    return redirect("restaurateur:RestaurantView")
                return redirect("start_page")

        return render(
            request,
            "login.html",
            context={
                "form": form,
                "ivalid": True,
            },
        )


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy("restaurateur:login")


def is_manager(user):
    return user.is_staff  # FIXME replace with specific permission


@user_passes_test(is_manager, login_url="restaurateur:login")
def view_products(request):
    restaurants = list(Restaurant.objects.order_by("name"))
    products = list(
        Product.objects.prefetch_related("menu_items").select_related("category")
    )

    products_with_restaurant_availability = []
    for product in products:
        availability = {
            item.restaurant_id: item.availability for item in product.menu_items.all()
        }
        ordered_availability = [
            availability.get(restaurant.id, False) for restaurant in restaurants
        ]

        products_with_restaurant_availability.append((product, ordered_availability))

    return render(
        request,
        template_name="products_list.html",
        context={
            "products_with_restaurant_availability": products_with_restaurant_availability,
            "restaurants": restaurants,
        },
    )


@user_passes_test(is_manager, login_url="restaurateur:login")
def view_restaurants(request):
    return render(
        request,
        template_name="restaurants_list.html",
        context={
            "restaurants": Restaurant.objects.all(),
        },
    )


@user_passes_test(is_manager, login_url="restaurateur:login")
def view_orders(request):
    order_items = (
        Order.objects.active()
        .select_related("restaurant")
        .with_total_cost()
        .annotate(
            is_new=Case(
                When(status="new", then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
        .order_by("-is_new", "created_at")
        .prefetch_related("items__product")
    )

    if not order_items:
        return render(request, "order_items.html", {"order_items": []})

    order_products_map, all_product_ids = get_order_products_map(order_items)

    restaurant_products, restaurants_map = get_restaurant_products_map(all_product_ids)

    suitable_by_order = find_suitable_restaurants(
        order_items,
        order_products_map,
        restaurant_products,
        restaurants_map,
    )

    addresses = collect_addresses(order_items, suitable_by_order)

    coordinates = get_coordinates_for_addresses(addresses)

    compute_distances_for_orders(order_items, coordinates, suitable_by_order)

    return render(
        request,
        template_name="order_items.html",
        context={"order_items": order_items},
    )
