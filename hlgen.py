#!/usr/bin/env python3
import argparse
import itertools
import os
import sys
from pathlib import Path
from typing import List

from logging import warn
from src.formatting import expand_template, Table
from src.project import Project, BuildConfig

TOOL_DIR = Path(os.path.dirname(os.path.realpath(__file__)))


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

        getattr(self, args.command)(sys.argv[2:])

    def list(self, argv):
        makefile = Project().get_makefile()
        configurations, invalid = makefile.get_generators()
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

        makefile = Project().get_makefile()

        if not makefile.has_generator(args.gen):
            warn(f'no generator named {args.gen} exists!')
            sys.exit(1)

        makefile.add_configuration(args.gen, args.name, ' '.join(generator_params))
        makefile.save()

    def create_generator(self, argv):
        parser = argparse.ArgumentParser(
            description='Create a new Halide generator',
            usage='hlgen create generator <name>')
        parser.add_argument('name', type=str,
                            help='The name of the generator. This will also be the name of the source file created.')

        args = parser.parse_args(argv)
        project = Project()
        makefile = project.get_makefile()

        if makefile.has_generator(args.name):
            warn(f'generator {args.name} already exists!')
            sys.exit(1)

        makefile.add_generator(args.name)
        self.copy_from_skeleton(
            project,
            Path('${NAME}.gen.cpp'),
            {'_HLGEN_BASE': TOOL_DIR, 'NAME': args.name})
        makefile.save()

    def create_project(self, argv):
        parser = argparse.ArgumentParser(
            description='Create a new Halide project',
            usage='hlgen create project <name>')
        parser.add_argument('name', type=str,
                            help='The name of the project. This will also be the name of the directory created.')

        args = parser.parse_args(argv)

        if os.path.isdir(args.name):
            warn('project directory already exists!')
            sys.exit(1)

        os.mkdir(args.name)

        project = Project(os.path.realpath(args.name))

        env = {'_HLGEN_BASE': TOOL_DIR,
               'NAME': args.name}

        self.init_from_skeleton(project, env)

    def copy_from_skeleton(self, project, relative, env):
        skel_file = TOOL_DIR / 'skeleton' / relative
        proj_file = project.root / relative

        with open(skel_file, 'r') as f:
            content = expand_template(f.read(), env)

        proj_file = proj_file.with_name(expand_template(proj_file.name, env))
        with open(proj_file, 'w') as f:
            f.write(content)

    def init_from_skeleton(self, project, env):
        skeleton_path = TOOL_DIR / 'skeleton'
        for root, _, files in os.walk(skeleton_path):
            relative = Path(root).relative_to(skeleton_path)

            os.makedirs(project.root / relative, exist_ok=True)
            for file_name in files:
                self.copy_from_skeleton(project, relative / file_name, env)


if __name__ == '__main__':
    HLGen()
