from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget
from .models import Category, Product, Order, OrderItem, Commission, CommissionRate, DiagnosisProductMap, PatientProductRecommendation


class CategoryResource(resources.ModelResource):
    class Meta:
        model = Category
        fields = ('id', 'name', 'icon', 'description')
        export_order = ('id', 'name', 'icon', 'description')
        import_id_fields = ('id',)


class ProductResource(resources.ModelResource):
    category = fields.Field(
        column_name='category',
        attribute='category',
        widget=ForeignKeyWidget(Category, 'name')
    )

    class Meta:
        model = Product
        fields = ('id', 'name', 'category', 'description', 'price', 'unit', 'in_stock', 'is_featured')
        export_order = ('id', 'name', 'category', 'description', 'price', 'unit', 'in_stock', 'is_featured')
        import_id_fields = ('id',)


@admin.register(Category)
class CategoryAdmin(ImportExportModelAdmin):
    resource_class = CategoryResource
    list_display = ['name', 'icon']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    list_display = ['name', 'category', 'price', 'unit', 'in_stock', 'is_featured', 'created_at']
    list_filter = ['category', 'in_stock', 'is_featured']
    search_fields = ['name', 'description']
    list_editable = ['in_stock', 'is_featured', 'price']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_name', 'quantity', 'unit_price']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer_name', 'customer_phone', 'status', 'total_amount', 'created_at']
    list_filter = ['status']
    search_fields = ['order_number', 'customer_name', 'customer_email', 'customer_phone']
    readonly_fields = ['order_number', 'created_at']
    inlines = [OrderItemInline]
    list_editable = ['status']


@admin.register(CommissionRate)
class CommissionRateAdmin(admin.ModelAdmin):
    list_display = ['physio', 'rate']
    list_editable = ['rate']


@admin.register(PatientProductRecommendation)
class PatientProductRecommendationAdmin(admin.ModelAdmin):
    list_display = ['patient', 'product', 'recommended_by', 'note', 'created_at']
    list_filter = ['recommended_by']
    search_fields = ['patient__patient_name', 'product__name']
    readonly_fields = ['created_at']


@admin.register(DiagnosisProductMap)
class DiagnosisProductMapAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'label']
    search_fields = ['keyword', 'label']
    filter_horizontal = ['products']


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ['order', 'physio', 'patient_code', 'order_amount', 'commission_rate', 'commission_amount', 'status', 'created_at']
    list_filter = ['status', 'physio']
    list_editable = ['status']
    readonly_fields = ['order', 'physio', 'patient_code', 'order_amount', 'commission_rate', 'commission_amount', 'created_at']
    search_fields = ['patient_code', 'order__order_number']
