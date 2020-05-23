#!/bin/zsh
books build && rsync -avzu --info=progress2 -h _html/* tonks:/usr/share/webapps/books
