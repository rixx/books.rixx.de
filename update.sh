#!/bin/zsh
books build && chmod a+r -R _html/ && rsync -avzu --info=progress2 -h _html/* tonks:/usr/share/webapps/books # && books social
