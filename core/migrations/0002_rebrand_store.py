from django.db import migrations


def rebrand_store(apps, schema_editor):
    database = schema_editor.connection.alias
    store = apps.get_model("core", "StoreSettings")
    brand = apps.get_model("catalog", "Brand")
    store.objects.using(database).filter(store_name__icontains="Mattic").update(
        store_name="Suitandtiefashionshop"
    )
    for old_name, new_name in (
        ("Mattic", "Suitandtiefashionshop"),
        ("Mattic Demo", "Suitandtiefashionshop Demo"),
    ):
        brand.objects.using(database).filter(name=old_name).update(name=new_name)
    if not brand.objects.using(database).filter(slug="suitandtiefashionshop-demo").exists():
        brand.objects.using(database).filter(slug="mattic-demo").update(slug="suitandtiefashionshop-demo")


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial"), ("catalog", "0002_alter_productvariant_product")]
    operations = [migrations.RunPython(rebrand_store, migrations.RunPython.noop)]
