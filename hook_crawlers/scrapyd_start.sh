#!/bin/bash
EGGS_DIR=eggs

# set proxy-list path
export PROXY_LIST=$(readlink -f $(find . -name proxy-list.txt))

# clean old stuffs

if [ -d "$EGGS_DIR" ]; then
    rm -r $EGGS_DIR/$p
fi

SPIDER_PROJECTS=$(python cmd.py get-project)
for p in $SPIDER_PROJECTS;
    do
        mkdir -p $EGGS_DIR/$p
        scrapyd-deploy --build-egg $EGGS_DIR/$p/$(date +%s).egg
    done

if python cmd.py checkdb; then
    scrapyd
else
    echo "Can't get connection with db."
    exit 1
fi
