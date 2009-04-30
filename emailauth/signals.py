from django.dispatch import Signal

email_created = Signal(providing_args=["user"])
