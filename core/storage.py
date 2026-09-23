from django.conf import settings
from django.core.files.storage import FileSystemStorage, storages
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.PRIVATE_MEDIA_ROOT)

    def url(self, name):
        raise ValueError("Payment screenshots require an authenticated API download.")


def private_storage():
    return storages["private"]
