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


class ProductImage(models.Model):
    """Additional photos for a product's detail-page gallery, beyond the
    single required Product.image -- swipeable/zoomable in the app.
    Mirrors exercise_app.ExerciseStepImage's shape (ordered rows, not
    columns): a product can have zero extra photos or many, with no
    fixed column count to outgrow."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='gallery_images')
    order = models.PositiveSmallIntegerField(default=0, help_text='Display order, after the main product photo')
    image = models.CharField(max_length=200, help_text='Same path convention as Product.image')

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.product.name} — image {self.order}"


class ProductVariant(models.Model):
    """A purchasable option of a Product with its own price/stock/photo -- e.g.
    a resistance band's strength, a brace's size. Optional: most products have
    none and are bought directly. image is optional; blank means "use the
    parent Product's photo" (only override it for genuinely different-looking
    variants, e.g. color)."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    label = models.CharField(max_length=100)  # e.g. "Medium (Green)", "Large"
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.CharField(max_length=200, blank=True, default='')
    in_stock = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"{self.product.name} — {self.label}"


class PharmacyProduct(models.Model):
    """Pharmacy's own catalog -- deliberately a separate table from Product
    (used to just be Product rows tagged category='Pharmacy'). Flat list, no
    category FK yet: the old Pharmacy listing never had real sub-categories
    either, so there's no existing data to back a taxonomy -- add one later
    if/when real categories are assigned."""
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True, help_text='Optional free-text grouping, e.g. "Pain Relief" -- shown on the product page, not filterable yet.')
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50, default='per piece')
    image = models.CharField(max_length=200, blank=True, default='')
    in_stock = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    requires_prescription = models.BooleanField(default=False, help_text='Shows an Rx-required badge on the storefront.')
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
    ORDER_TYPE_CHOICES = [
        ('marketplace', 'Marketplace'),
        ('pharmacy', 'Pharmacy'),
        ('lab_test', 'Lab Test'),
    ]

    order_number = models.CharField(max_length=20, unique=True, editable=False)
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, default='marketplace')
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
    pharmacy_product = models.ForeignKey(PharmacyProduct, on_delete=models.SET_NULL, null=True, blank=True)
    lab_test = models.ForeignKey('lab_app.LabTest', on_delete=models.SET_NULL, null=True, blank=True)
    lab_panel = models.ForeignKey('lab_app.LabTestPanel', on_delete=models.SET_NULL, null=True, blank=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
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
        verbose_name = 'Diagnosis-Product Map'
        verbose_name_plural = 'Diagnosis-Product Maps'

    def __str__(self):
        return self.label or self.keyword
