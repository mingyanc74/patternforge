import time

from django.core.management.base import BaseCommand

from core.tasks import dispatch_pending, maintenance


class Command(BaseCommand):
    help = "Dispatch the persistent outbox; survives broker outages without losing accepted jobs."

    def handle(self, *args, **options):
        counter = 0
        while True:
            try:
                dispatch_pending()
                if counter % 6 == 0:
                    maintenance()
            except Exception as exc:
                self.stderr.write("Dispatcher waiting: " + type(exc).__name__)
            counter += 1
            time.sleep(5)
