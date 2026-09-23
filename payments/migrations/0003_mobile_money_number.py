from django.db import migrations


INSTRUCTIONS = (
    "1. Open Mobile Money on your phone.\n"
    "2. Choose Send money and enter 0784888458.\n"
    "3. Enter the exact order total and check the recipient before confirming.\n"
    "4. Save your payment confirmation screenshot.\n"
    "5. Upload it to your order for verification."
)


def use_mobile_money(apps, schema_editor):
    config_model = apps.get_model("payments", "StorePaymentSettings")
    payment_model = apps.get_model("payments", "Payment")
    database = schema_editor.connection.alias
    config_model.objects.using(database).all().update(
        momo_code="", momo_phone_number="0784888458", payment_instructions=INSTRUCTIONS
    )
    # Completed and submitted payments retain their original instructions for audit.
    for payment in payment_model.objects.using(database).filter(
        status__in=["PENDING", "REJECTED"], order__status="PENDING_PAYMENT"
    ).iterator():
        snapshot = dict(payment.instructions_snapshot)
        snapshot.pop("momo_code", None)
        snapshot.update(momo_phone_number="0784888458", payment_instructions=INSTRUCTIONS)
        payment.instructions_snapshot = snapshot
        payment.save(using=database, update_fields=["instructions_snapshot"])


class Migration(migrations.Migration):
    dependencies = [("payments", "0002_alter_storepaymentsettings_momo_code_and_more")]
    operations = [migrations.RunPython(use_mobile_money, migrations.RunPython.noop)]
