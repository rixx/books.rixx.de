#!/bin/zsh

set -e

books build --db /home/rixx/data/dbs/books.db
# books build
chmod a+r -R _html/
rsync -avzu --info=progress2 -h _html/* tonks:/usr/share/webapps/books
rsync -avzu --info=progress2 -h /home/rixx/data/dbs/books.db mycroft:/usr/share/webapps/datasette/
# books social
