from django import forms
from django.contrib import admin
from django.shortcuts import redirect
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme

from .models import (
    Order,
    OrderItem,
    Product,
    ProductCategory,
    Restaurant,
    RestaurantMenuItem,
)
from .utils import get_restaurants_for_order


class LocationAdminMixin:
    """Миксин для отображения координат из связанной модели Location."""

    def get_lat(self, obj):
        return (
            obj.location.lat if obj.location and obj.location.lat is not None else None
        )

    get_lat.short_description = "Широта"

    def get_lon(self, obj):
        return (
            obj.location.lon if obj.location and obj.location.lon is not None else None
        )

    get_lon.short_description = "Долгота"


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if self.instance.items.exists():
                self.fields["restaurant"].queryset = get_restaurants_for_order(
                    self.instance
                )


class RestaurantMenuItemInline(admin.TabularInline):
    model = RestaurantMenuItem
    extra = 0


@admin.register(Restaurant)
class RestaurantAdmin(LocationAdminMixin, admin.ModelAdmin):
    readonly_fields = ("get_lat", "get_lon")
    fieldsets = (
        (
            "Общее",
            {
                "fields": [
                    "name",
                    "address",
                    "contact_phone",
                ]
            },
        ),
        (
            "Координаты",
            {
                "fields": [
                    "get_lat",
                    "get_lon",
                ]
            },
        ),
    )
    search_fields = (
        "name",
        "address",
        "contact_phone",
    )
    list_display = (
        "name",
        "address",
        "contact_phone",
    )
    inlines = [RestaurantMenuItemInline]  # noqa: RUF012


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "get_image_list_preview",
        "name",
        "category",
        "price",
    )
    list_display_links = ("name",)
    list_filter = ("category",)
    search_fields = (
        # FIXME SQLite can not convert letter case for cyrillic words properly, so search will be buggy.
        # Migration to PostgreSQL is necessary
        "name",
        "category__name",
    )

    inlines = [RestaurantMenuItemInline]  # noqa: RUF012
    fieldsets = (
        (
            "Общее",
            {
                "fields": [
                    "name",
                    "category",
                    "image",
                    "get_image_preview",
                    "price",
                ]
            },
        ),
        (
            "Подробно",
            {
                "fields": [
                    "special_status",
                    "description",
                ],
                "classes": ["wide"],
            },
        ),
    )

    readonly_fields = ("get_image_preview",)

    class Media:
        css = {"all": (static("admin/foodcartapp.css"))}  # noqa: RUF012

    def get_image_preview(self, obj):
        if not obj.image:
            return "выберите картинку"
        return format_html(
            '<img src="{url}" style="max-height: 200px;"/>', url=obj.image.url
        )

    get_image_preview.short_description = "превью"

    def get_image_list_preview(self, obj):
        if not obj.image or not obj.id:
            return "нет картинки"
        edit_url = reverse("admin:foodcartapp_product_change", args=(obj.id,))
        return format_html(
            '<a href="{edit_url}"><img src="{src}" style="max-height: 50px;"/></a>',
            edit_url=edit_url,
            src=obj.image.url,
        )

    get_image_list_preview.short_description = "превью"


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    pass


class OrderItemsInline(admin.TabularInline):
    fields = (
        "product",
        "quantity",
        "price",
    )
    readonly_fields = ("price",)
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(LocationAdminMixin, admin.ModelAdmin):
    form = OrderForm
    inlines = [OrderItemsInline]  # noqa: RUF012
    readonly_fields = ("get_lat", "get_lon", "created_at")
    fieldsets = (
        (
            "Клиент",
            {
                "fields": (
                    "client_first_name",
                    "client_last_name",
                    "phone_number",
                    "client_address",
                )
            },
        ),
        (
            "Координаты",
            {
                "fields": (
                    "get_lat",
                    "get_lon",
                )
            },
        ),
        (
            "Статус и комментарий",
            {"fields": ("status", "payment_method", "comment")},
        ),
        (
            "Ресторан",
            {"fields": ("restaurant",)},
        ),
        (
            "Информация",
            {"fields": ("created_at", "called_at", "delivered_at")},
        ),
    )
    list_filter = (
        "created_at",
        "status",
        "payment_method",
    )
    search_fields = (
        "phone_number",
        "client_first_name",
        "client_address",
    )
    list_display = (
        "id",
        "phone_number",
        "client_first_name",
        "client_address",
        "created_at",
        "status",
        "payment_method",
    )
    list_display_links = ("id", "phone_number", "client_first_name")
    list_editable = (
        "status",
        "payment_method",
    )

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        for obj in formset.deleted_objects:
            obj.delete()

        for obj in instances:
            if isinstance(obj, OrderItem):
                obj.price = obj.product.price
            obj.save()
        formset.save_m2m()

    def response_change(self, request, obj):
        next_url = request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return super().response_change(request, obj)

    def save_model(self, request, obj, form, change):
        if obj.restaurant and obj.status == "new":
            obj.status = "in_progress"
        super().save_model(request, obj, form, change)
