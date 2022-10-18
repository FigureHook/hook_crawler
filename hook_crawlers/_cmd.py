import pathlib
import sys
from configparser import ConfigParser

import click


@click.group()
def check():
    pass


@check.command()
def get_project():
    service_dir = pathlib.Path(__file__).parent.absolute()
    cfg = ConfigParser()
    cfg.read(f"{service_dir}/scrapy.cfg")

    projects = ""
    for sec in cfg.sections():
        if "deploy" in sec:
            project = cfg.get(sec, "project")
            projects += project + " "

    click.echo(projects)
    sys.exit(0)


if __name__ == "__main__":
    check()
