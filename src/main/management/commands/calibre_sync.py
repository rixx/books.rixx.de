from django.core.management.base import BaseCommand

import json
import subprocess
from pathlib import Path
import yaml


class Command(BaseCommand):
    help = 'Closes the specified poll for voting'
    def handle(self, *args, **options):

        query = "'tags:\"=on-device\"'"
        result = subprocess.check_output(
            f"calibredb list -s {query} --fields authors,title,*pages,*shelf --for-machine", shell=True, env={}
        ).decode()
        books = json.loads(result)
        output = [
            {"author": b["authors"],
             "title": b["title"],
             "shelf": b["*shelf"],
             "pages": b["*pages"],
             } for b in books
        ]
        path = Path(__file__).parent.parent.parent.parent.parent / "data" / "queue" / "data.yaml"
        print(path)
        with open(path, "w") as fp:
            yaml.dump(output, fp)
