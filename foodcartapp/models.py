from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Sum
from phonenumber_field.modelfields import PhoneNumberField


class OrderQuerySet(models.QuerySet):
    def active(self):
        active_statuses = [
            "new",
            "confirmed",
            "in_progress",
            "ready",
            "in_delivery",
        ]
        return self.filter(status__in=active_statuses)

    def with_total_cost(self):
        total_cost = Sum(F("items__quantity") * F("items__price"))
        return self.annotate(total_cost=total_cost)


class Restaurant(models.Model):
    name = models.CharField(
        "название",
        max_length=50,
    )
    address = models.CharField(
        "адрес",
        max_length=100,
        blank=True,
    )
    contact_phone = models.CharField(
        "контактный телефон",
        max_length=50,
        blank=True,
    )

    class Meta:
        verbose_name = "ресторан"
        verbose_name_plural = "рестораны"

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = RestaurantMenuItem.objects.filter(
            availability=True,
        ).values_list("product")
        return self.filter(pk__in=products)


class ProductCategory(models.Model):
    name = models.CharField("название", max_length=50)

    class Meta:
        verbose_name = "категория"
        verbose_name_plural = "категории"

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField("название", max_length=50)
    category = models.ForeignKey(
        ProductCategory,
        verbose_name="категория",
        related_name="products",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        "цена",
        max_digits=8,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
        ],
    )
    image = models.ImageField("картинка")
    special_status = models.BooleanField(
        "спец.предложение",
        default=False,
        db_index=True,
    )
    description = models.TextField(
        "описание",
        max_length=200,
        blank=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = "товар"
        verbose_name_plural = "товары"

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name="menu_items",
        verbose_name="ресторан",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="menu_items",
        verbose_name="продукт",
    )
    availability = models.BooleanField(
        "в продаже",
        default=True,
        db_index=True,
    )

    class Meta:
        verbose_name = "пункт меню ресторана"
        verbose_name_plural = "пункты меню ресторана"
        unique_together = ("restaurant", "product")

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"


class Order(models.Model):
    ORDER_STATUS = [
        ("new", "Новый"),
        ("confirmed", "Подтверждён"),
        ("in_progress", "На сборке"),
        ("ready", "Готов к доставки"),
        ("in_delivery", "В доставке"),
        ("completed", "Выполнен"),
        ("canceled", "Отменён"),
        ("returned", "Возврат"),
        ("erorr", "Ошибка"),
    ]
    PAYMENT_METHOD = [
        ("", "не выбрано"),
        ("cash", "наличными"),
        ("card", "картой"),
        ("QR", "QR-кодом"),
        ("online", "онлайн"),
    ]
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD,
        null=True,
        default="не выбрано",
        db_index=True,
        verbose_name="Способ оплаты",
    )
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS,
        default="new",
        db_index=True,
        verbose_name="Статус заказа",
    )
    comment = models.TextField(
        "Комментарий к заказу",
        blank=True,
    )
    client_first_name = models.CharField("Имя клиента", max_length=50)
    client_last_name = models.CharField(
        "Фамилия клиента",
        max_length=50,
        blank=True,
    )
    phone_number = PhoneNumberField("Номер телефона", db_index=True)
    client_address = models.CharField(
        "Адрес клиента",
        max_length=200,
        db_index=True,
    )
    created_at = models.DateTimeField(
        "Время создания заказа",
        auto_now_add=True,
        db_index=True,
    )
    called_at = models.DateTimeField(
        "Время звонка",
        null=True,
        blank=True,
        db_index=True,
    )
    delivered_at = models.DateTimeField(
        "Дата доставки",
        null=True,
        blank=True,
        db_index=True,
    )
    restaurant = models.ForeignKey(
        "Restaurant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="Ресторан",
    )

    objects = OrderQuerySet.as_manager()

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Список заказов"

    def __str__(self):
        return f"Заказ {self.pk} от {self.client_first_name} {self.phone_number}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name="Продукт",
    )

    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    price = models.DecimalField(
        "цена в заказе",
        max_digits=8,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
        ],
    )

    class Meta:
        unique_together = ("order", "product")
        verbose_name = "Продукт"
        verbose_name_plural = "Состав заказа"

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
