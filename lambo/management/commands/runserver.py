from django.core.management.commands.runserver import Command as RunserverCommand
from subprocess import Popen
import os


class Command(RunserverCommand):
    help = "Runs the server and also starts Tailwind CSS watcher."

    def inner_run(self, *args, **options):
        # Start tailwind in background
        if os.name == "nt":  # Windows
            Popen(["python", "manage.py", "tailwind", "start"], creationflags=0x08000000)
        else:  # Mac/Linux
            Popen(["python", "manage.py", "tailwind", "start"])

        # Then continue with normal runserver
        super().inner_run(*args, **options)
