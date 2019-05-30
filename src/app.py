import argparse
import itertools
import os
import sys
from pathlib import Path
from typing import List

from src.formatting import Table
from src.logging import warn
from src.project import Project, BuildConfig

TOOL_DIR = Path(os.path.dirname(os.path.realpath(os.path.join(__file__, '..'))))


class HLGen(object):
    def __init__(self):
        parser = argparse.ArgumentParser(
            description='Creates and manages Halide projects',
            usage='''hlgen <command> [<args>]

The available hlgen commands are:
   create     Create a new Halide project, generator, or configuration
   delete     Remove an existing generator or configuration
   list       List generators and their configurations
''')
        parser.add_argument('command', help='Subcommand to run')

        args = parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.command):
            parser.print_help()
            sys.exit(1)

        try:
            getattr(self, args.command)(sys.argv[2:])
        except ValueError as e:
            warn(str(e))
            sys.exit(1)

    def list(self, argv):
        project = Project()
        configurations, invalid = project.get_configurations()
        configurations: List[BuildConfig] = configurations
        configurations.sort(key=lambda cfg: (cfg.generator, cfg.config_name))

        table = Table()
        table.set_headers('Generator', 'Configuration', 'Parameters')

        pad = False
        for generator, confs in itertools.groupby(configurations, key=lambda x: x.generator):
            if pad:
                table.add_row()
            for config in confs:
                table.add_row(config.generator,
                              config.config_name or '(default)',
                              config.params or '(default)')
            pad = True
        print(table)

    def create(self, argv):
        parser = argparse.ArgumentParser(
            description='Create a new Halide project, generator, or configuration',
            usage='hlgen create <item_type> [<args>]')
        parser.add_argument('item_type', type=str, choices=['project', 'generator', 'configuration'],
                            help='what kind of item to create')

        args = parser.parse_args(argv[:1])
        method = f'create_{args.item_type}'

        getattr(self, method)(argv[1:])

    def create_configuration(self, argv):
        parser = argparse.ArgumentParser(
            description='Create a new Halide generator configuration',
            usage='''hlgen create configuration <gen> <name> [<generator-params>]

The new configuration will be compiled as <gen>__<name>.{a,h,so,etc.}
''')
        parser.add_argument('gen', type=str, help='The name of the generator.')
        parser.add_argument('name', type=str, help='The name of the configuration.')

        args, generator_params = parser.parse_known_args(argv)

        project = Project()
        project.create_configuration(args.gen, args.name, generator_params)
        project.save()

    def create_generator(self, argv):
        parser = argparse.ArgumentParser(
            description='Create a new Halide generator',
            usage='hlgen create generator <name>')
        parser.add_argument('name', type=str,
                            help='The name of the generator. This will also be the name of the source file created.')

        args = parser.parse_args(argv)
        project = Project()
        project.create_generator(args.name)
        project.save()

    def create_project(self, argv):
        parser = argparse.ArgumentParser(
            description='Create a new Halide project',
            usage='hlgen create project <name>')
        parser.add_argument('name', type=str,
                            help='The name of the project. This will also be the name of the directory created.')

        args = parser.parse_args(argv)
        project = Project.create_new(args.name)
        project.save()
