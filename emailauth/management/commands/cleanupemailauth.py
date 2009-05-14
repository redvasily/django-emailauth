from django.core.management.base import NoArgsCommand

from emailauth.models import UserEmail


class Command(NoArgsCommand):
    help = "Delete expired UserEmail objects from the database"

    def handle_noargs(self, **options):
        UserEmail.objects.delete_expired()
