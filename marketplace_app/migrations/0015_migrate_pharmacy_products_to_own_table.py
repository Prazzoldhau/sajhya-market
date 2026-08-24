# Copies existing Product rows tagged category='Pharmacy' into the new,
# separate PharmacyProduct table, then removes them from Product -- the
# Pharmacy catalog used to just be Product rows filtered by category name;
# now it's its own table entirely (see PharmacyProduct in models.py).
#
# Safe to delete the old rows: OrderItem.product is ON DELETE SET NULL and
# already carries denormalized product_name/unit_price, so past order
# history is unaffected. ProductVariant/ProductImage cascade-delete (no
# Pharmacy item has ever used variants/gallery images). PatientProductRecommendation
# cascade-deletes too, but Pharmacy is already excluded from every patient
# recommendation query in views.py, so none should exist for these rows.

from django.db import migrations


def migrate_forward(apps, schema_editor):
    Product = apps.get_model('marketplace_app', 'Product')
    PharmacyProduct = apps.get_model('marketplace_app', 'PharmacyProduct')

    pharmacy_products = Product.objects.filter(category__name='Pharmacy')
    for p in pharmacy_products:
        PharmacyProduct.objects.create(
            name=p.name,
            description=p.description,
            price=p.price,
            unit=p.unit,
            image=p.image,
            in_stock=p.in_stock,
            is_featured=p.is_featured,
            created_at=p.created_at,
        )
    pharmacy_products.delete()


def migrate_backward(apps, schema_editor):
    Product = apps.get_model('marketplace_app', 'Product')
    Category = apps.get_model('marketplace_app', 'Category')
    PharmacyProduct = apps.get_model('marketplace_app', 'PharmacyProduct')

    category, _ = Category.objects.get_or_create(name='Pharmacy', defaults={'icon': '', 'description': ''})
    for pp in PharmacyProduct.objects.all():
        Product.objects.create(
            name=pp.name,
            category=category,
            description=pp.description,
            price=pp.price,
            unit=pp.unit,
            image=pp.image,
            in_stock=pp.in_stock,
            is_featured=pp.is_featured,
            created_at=pp.created_at,
        )
    PharmacyProduct.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace_app', '0014_pharmacyproduct_order_order_type_and_more'),
    ]

    operations = [
        migrations.RunPython(migrate_forward, migrate_backward),
    ]
