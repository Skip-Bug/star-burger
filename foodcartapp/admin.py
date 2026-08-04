from django.contrib import admin
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html

from .models import (
    Order,
    OrderItem,
    Product,
    ProductCategory,
    Restaurant,
    RestaurantMenuItem,
)


class RestaurantMenuItemInline(admin.TabularInline):
    model = RestaurantMenuItem
    extra = 0


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
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
    fields = ("restaurant_menu_item", "quantity")
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemsInline]  # noqa: RUF012
    list_filter = ("created_at",)
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
    )
    list_display_links = ("id", "phone_number", "client_first_name")
