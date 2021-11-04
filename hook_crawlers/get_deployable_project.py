import pathlib
from configparser import ConfigParser

service_dir = pathlib.Path(__file__).parent.absolute()
cfg = ConfigParser()
cfg.read(f'{service_dir}/scrapy.cfg')

projects = ""
for sec in cfg.sections():
    if "deploy" in sec:
        project = cfg.get(sec, "project")
        projects += project + ' '

print(projects)
