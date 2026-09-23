from rest_framework import serializers

from .models import StoreSettings


class ValidatedModelSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = self.Meta.model()
        if self.instance:
            for field in self.Meta.model._meta.concrete_fields:
                setattr(instance, field.attname, getattr(self.instance, field.attname))
        for key, value in attrs.items():
            setattr(instance, key, value)
        instance.clean()
        return attrs


class StoreSettingsSerializer(ValidatedModelSerializer):
    class Meta:
        model = StoreSettings
        fields = "__all__"


class NoteSerializer(serializers.Serializer):
    admin_note = serializers.CharField(required=False, allow_blank=True, max_length=2000, default="")
