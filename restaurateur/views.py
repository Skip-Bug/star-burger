from django import forms
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Case, IntegerField, Value, When
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from geopy.distance import geodesic

from foodcartapp.models import Order, Product, Restaurant
from foodcartapp.utils import get_restaurants_for_order
from location.geocoder import get_or_create_location
from location.models import Location


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
    products = list(Product.objects.prefetch_related("menu_items"))

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

    addresses = set()
    for order in order_items:
        addresses.add(order.client_address)
        for restaurant in get_restaurants_for_order(order):
            addresses.add(restaurant.address)

    location_dict = {
        loc.address: loc for loc in Location.objects.filter(address__in=addresses)
    }

    for address in addresses:
        loc = location_dict.get(address)
        if loc is None or loc.lat is None or loc.lon is None:
            updated_loc = get_or_create_location(address)
            location_dict[address] = updated_loc

    for order in order_items:
        client_loc = location_dict.get(order.client_address)
        client_coords = (
            (client_loc.lat, client_loc.lon)
            if client_loc and client_loc.lat and client_loc.lon
            else None
        )

        if order.restaurant:
            order.available_restaurants = [(order.restaurant, None)]
            continue

        restaurants = get_restaurants_for_order(order)
        restaurants_with_dist = []
        for restaurant in restaurants:
            dist = None
            rest_loc = location_dict.get(restaurant.address)
            if client_coords and rest_loc and rest_loc.lat and rest_loc.lon:
                rest_coords = (rest_loc.lat, rest_loc.lon)
                dist = round(geodesic(client_coords, rest_coords).km, 1)
            restaurants_with_dist.append((restaurant, dist))
        restaurants_with_dist.sort(key=lambda item: (item[1] is None, item[1]))
        order.available_restaurants = restaurants_with_dist

    return render(
        request,
        template_name="order_items.html",
        context={"order_items": order_items},
    )
