from django.db import migrations


def update_display_name(apps, schema_editor):
    database = schema_editor.connection.alias
    store = apps.get_model("core", "StoreSettings")
    brand = apps.get_model("catalog", "Brand")
    store.objects.using(database).filter(store_name="Suitandtiefashionshop").update(
        store_name="Suit and Tie Fashion Shop"
    )
    for old_name, new_name in (
        ("Suitandtiefashionshop", "Suit and Tie Fashion Shop"),
        ("Suitandtiefashionshop Demo", "Suit and Tie Fashion Shop Demo"),
    ):
        brand.objects.using(database).filter(name=old_name).update(name=new_name)


class Migration(migrations.Migration):
    dependencies = [("core", "0002_rebrand_store")]
    operations = [migrations.RunPython(update_display_name, migrations.RunPython.noop)]
