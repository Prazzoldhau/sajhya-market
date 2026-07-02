from django.db import models
from django.conf import settings
from decimal import Decimal
import uuid


class Category(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, default='')
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products'
    )
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50, default='per piece')
    image = models.CharField(max_length=200, blank=True, default='')
    in_stock = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_featured', 'name']

    def __str__(self):
        return self.name



class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    order_number = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    delivery_address = models.TextField()
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order_number} — {self.customer_name}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class CommissionRate(models.Model):
    physio = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True, related_name='commission_rate'
    )  # null = global default rate
    rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('10.00'))

    def __str__(self):
        return f"{'Global default' if not self.physio else self.physio.username} — {self.rate}%"

    @classmethod
    def get_rate_for_physio(cls, physio):
        try:
            return cls.objects.get(physio=physio).rate
        except cls.DoesNotExist:
            pass
        try:
            return cls.objects.get(physio__isnull=True).rate
        except cls.DoesNotExist:
            return Decimal('10.00')


class Commission(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
    ]
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='commission')
    physio = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='commissions'
    )
    patient_code = models.CharField(max_length=20, blank=True)
    order_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Commission {self.order.order_number} — {self.physio}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.product_name}"

    @property
    def total_price(self):
        return self.quantity * self.unit_price


class PatientProductRecommendation(models.Model):
    patient      = models.ForeignKey(
        'personal_account.AddPatient', on_delete=models.CASCADE,
        related_name='product_recommendations'
    )
    product      = models.ForeignKey(Product, on_delete=models.CASCADE)
    recommended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    note         = models.CharField(max_length=200, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['patient', 'product']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name} → {self.patient}"


class DiagnosisProductMap(models.Model):
    keyword  = models.CharField(max_length=100, unique=True)
    label    = models.CharField(max_length=150, blank=True)
    products = models.ManyToManyField(Product, blank=True, related_name='diagnosis_maps')

    class Meta:
        ordering = ['keyword']
        verbose_name = 'Diagnosis → Product Map'
        verbose_name_plural = 'Diagnosis → Product Maps'

    def __str__(self):
        return self.label or self.keyword
