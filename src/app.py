import argparse
import itertools
import os
import sys
from pathlib import Path

from src.formatting import Table
from src.logging import warn
from src.project import Project

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
        except (ValueError, OSError) as e:
            warn(str(e))
            sys.exit(1)

    def delete(self, argv):
        parser = argparse.ArgumentParser(
            description='Delete an existing Halide generator or configuration',
            usage='hlgen delete <item_type> [<args>]')
        parser.add_argument('item_type', type=str, choices=['generator', 'configuration'],
                            help='what kind of item to delete')

        args = parser.parse_args(argv[:1])
        method = f'delete_{args.item_type}'

        getattr(self, method)(argv[1:])

    def delete_configuration(self, argv):
        parser = argparse.ArgumentParser(
            description='Delete an existing Halide generator configuration',
            usage='''hlgen delete configuration <gen> [<name>]

        Recommended to run `make clean` before running this command. To remove
        the default configuration, either omit <name> or write '(default)'.
        ''')
        parser.add_argument('gen', type=str, help='The name of the generator.')
        parser.add_argument('name', type=str, help='The name of the configuration.', default='', nargs='?')

        args = parser.parse_args(argv)

        project = Project()
        project.delete_configuration(args.gen, args.name)
        project.save()

    def delete_generator(self, argv):
        parser = argparse.ArgumentParser(
            description='Delete an existing Halide generator',
            usage='hlgen delete generator [-f/--force] <name>')
        parser.add_argument('-f', '--force', action='store_true',
                            help='do not prompt for confirmation before deleting files')
        parser.add_argument('name', type=str, help='The name of the generator.')

        args = parser.parse_args(argv)

        can_delete = True
        if not args.force:
            response = None
            while response not in ['', 'y', 'yes', 'n', 'no']:
                print('Alert! this action will delete any associated .gen.cpp files.')
                response = input('Are you sure you wish to continue? [y/n] ').lower()
            can_delete = response in ['', 'y', 'yes']

        if can_delete:
            project = Project()
            project.delete_generator(args.name)
            project.save()

    def list(self, argv):
        project = Project()
        configurations, invalid = project.get_configurations()
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
            usage='''hlgen create configuration <gen> <name> [<params>]

The new configuration will be compiled as <gen>__<name>.{a,h,so,etc.}. To restore
a default configuration after deleting it either omit <name> or write '(default)'
''')
        parser.add_argument('gen', type=str, help='The name of the generator.')
        parser.add_argument('name', type=str, help='The name of the configuration.', default='', nargs='?')
        parser.add_argument('params', type=str,
                            help='The build parameters passed to the generator.', nargs=argparse.REMAINDER)

        args = parser.parse_args(argv)

        project = Project()
        project.create_configuration(args.gen, args.name, args.params)
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
