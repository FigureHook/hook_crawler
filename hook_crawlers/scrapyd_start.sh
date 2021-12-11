#!/bin/bash
COMMAND=$1
EGGS_DIR=eggs

# set proxy-list path
export PROXY_LIST=$(readlink -f $(find . -name proxy-list.txt))

# clean old stuffs

if [ -z "$COMMAND" ]; then
    echo "Please specified command 'run' or 'test'."
    exit 1
fi

clean_old () {
    echo "Clean old egg in $EGGS_DIR"
    if [ -d "$EGGS_DIR" ]; then
        rm -r $EGGS_DIR/$p
    fi
}

get_project () {
    python _cmd.py get-project
}

check_db () {
    python _cmd.py checkdb
}

make_egg () {
    SPIDER_PROJECTS=$(get_project)

    for p in $SPIDER_PROJECTS;
        do
            mkdir -p $EGGS_DIR/$p
            scrapyd-deploy --build-egg $EGGS_DIR/$p/$(date +%s).egg
        done
}


# pre-process
clean_old
make_egg


if [ "$COMMAND" == "test" ]; then
    nohup scrapyd &
    sleep 5s
    pkill scrapyd
elif [ "$COMMAND" == "run" ]; then
    if check_db; then
        scrapyd
    else
        echo "Can't get connection with db."
        exit 1
    fi
else
    echo "Please specified command 'run' or 'test'."
    exit 1
fi