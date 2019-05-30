#!/usr/bin/env python3
import argparse
import ast
import glob
import itertools
import os
import re
import sys
from pathlib import Path
from typing import Union, List

TOOL_DIR = Path(os.path.dirname(os.path.realpath(__file__)))
PROJ_DIR = Path(os.path.realpath(os.getcwd()))


class BuildConfig(object):
    def __init__(self, generator, config_name, value, *, source=None, lineno=-1):
        self.generator = generator or ''
        self.config_name = config_name or ''
        self.params = value or ''
        self.source = source
        self.lineno = lineno

    @staticmethod
    def from_makefile(source, lineno):
        # Is there a way to do this without lazy groups?
        m = re.match(r'^CFG__(\w+?)(?:\s|__(\w+)?).*?=\s*(.*?)\s*$', source)
        if not m:
            return None
        return BuildConfig(*m.group(1, 2, 3), source=source, lineno=lineno)

    def __repr__(self):
        return str(self)

    def __str__(self):
        if self.source:
            return self.source
        suffix = '' if not self.config_name else f'__{self.config_name}'
        return f'CFG__{self.generator}{suffix} = {self.params}'


class ProjectMakefile(object):
    def __init__(self, path: Union[Path, str]):
        if isinstance(path, str):
            path = Path(path)
        self.path = path

        with open(path, 'r') as f:
            self._lines = f.readlines()

        self._gens, self._invalid = self._parse_makefile()

    def lines(self):
        return self._lines

    def get_generators(self):
        return self._gens, self._invalid

    def _parse_makefile(self):
        saw_generator_comment = False
        num_lines = len(self._lines)
        after_comment = num_lines
        cfg_start = num_lines
        cfg_end = num_lines

        configurations = []
        invalid_configurations = []
        generator2configs = {}

        # Create table for all the valid generators
        for gen in glob.glob(str(PROJ_DIR / '*.gen.cpp')):
            gen = os.path.basename(gen).rstrip('.gen.cpp')
            generator2configs[gen] = {}

        last_cfg = num_lines

        # Populate table with configurations from makefile
        for i, line in enumerate(self._lines):
            if not line.strip():
                if saw_generator_comment and after_comment == num_lines:
                    after_comment = i
                continue

            if line.startswith('# Configure generators'):
                saw_generator_comment = True
            if saw_generator_comment and after_comment == num_lines and not line.strip().startswith('#'):
                after_comment = i

            config = BuildConfig.from_makefile(line, i)
            if cfg_start == num_lines and config:
                cfg_start = i

            if cfg_end == num_lines and config:
                if config.generator not in generator2configs:
                    warn(f'invalid configuration specified for {config.generator} in Makefile:{i + 1}')
                    invalid_configurations.append(config)
                else:
                    if config.config_name in generator2configs[config.generator]:
                        warn(f'using overriding configuration for {config.generator} from Makefile:{i + 1}')
                        old_config = generator2configs[config.generator][config.config_name]
                        configurations.remove(old_config)
                        invalid_configurations.append(old_config)
                    generator2configs[config.generator][config.config_name] = config
                    configurations.append(config)
                last_cfg = i

            if cfg_start < num_lines and cfg_end == num_lines and not config:
                cfg_end = last_cfg + 1

        # If any generators didn't appear in the makefile, they get default configurations inferred
        for gen in generator2configs:
            if not generator2configs[gen]:
                generator2configs[gen][''] = BuildConfig(gen, '', '')
                configurations.append(BuildConfig(gen, '', ''))

        self._index = {}
        for config in configurations:
            self._index[(config.generator, config.config_name)] = config

        self.after_comment = after_comment
        self.cfg_start = cfg_start
        self.cfg_end = cfg_end

        return configurations, invalid_configurations


def warn(msg):
    print(f'WARNING: {msg}', file=sys.stderr)


def expand_template(template, env=None, **kwargs):
    if not env:
        env = dict()
    env = {k.lower(): v for k, v in env.items()}
    env.update({k.lower(): v for k, v in kwargs.items()})

    funs = {}

    def get_names(expr):
        names = set()
        for node in ast.walk(expr):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                node.id = node.id.lower()
                names.add(node.id)
        return list(names)

    def mkfun(expression):
        key = ast.dump(expression)
        if key in funs:
            return funs[key]

        names = get_names(expression)
        body = expression.body

        args = [ast.arg(arg=name, annotation=None) for name in names]
        body = ast.Lambda(
            ast.arguments(args=args, defaults=[], kwonlyargs=[], kw_defaults=[]),
            body)

        expression.body = body
        ast.fix_missing_locations(expression)

        f = compile(expression, filename="<ast>", mode='eval')
        value = (eval(f), names)
        funs[key] = value
        return value

    def expand(src):
        ex = ast.parse(src, mode='eval')
        if not isinstance(ex, ast.Expression):
            return ''
        f, names = mkfun(ex)
        args = [str(env.get(name)) or '' for name in names]
        return f(*args)

    # TODO: do something smarter here for matching { }
    return re.sub(r'\${([^}]+)}', lambda m: expand(m.group(1)), template)


def get_halide_directory():
    hldir = os.environ.get('HALIDE_DISTRIB_PATH')
    if not hldir:
        hldir = '/opt/halide'
    return os.path.realpath(hldir) if os.path.isdir(hldir) else None


class Table(object):
    def __init__(self, *, width=0, colpadding=1, show_row_numbers=False):
        self.width = width
        self.sizes = [0] * width
        self.rows = []
        self.colpadding = colpadding
        self.headers = []
        self.show_row_numbers = show_row_numbers

    def add_row(self, *args):
        try:
            self._ensure_width(args)
            self._update_sizes(args)
            self.rows.append(tuple(args))
        except ValueError:
            if args:
                raise
            self.rows.append(tuple([''] * self.width))

    def _update_sizes(self, args):
        self.sizes = list(map(max, zip(self.sizes, map(len, args))))

    def _ensure_width(self, args):
        if not self.width:
            self.width = len(args)
            self.sizes = [0] * self.width
        if len(args) != self.width:
            raise ValueError('arguments list not the same width')

    def _format_row(self, args, sizes):
        gutter = ' ' * self.colpadding
        template = ['{:<{}}'] * len(args)
        template = (gutter + '|' + gutter).join(template)
        fmtargs = zip(args, sizes)
        return template.format(*[x for y in fmtargs for x in y])

    def _format_rule(self, sizes):
        line_width = len(self._format_row([''] * len(sizes), sizes))
        rule = ['-'] * line_width
        i = 0
        for j in sizes[:-1]:
            i += j + self.colpadding
            rule[i] = '+'
            i += 1 + self.colpadding
        return ''.join(rule)

    def __str__(self):
        output = ''
        sizes = self.sizes
        if self.show_row_numbers:
            sizes = [len(str(len(self.rows)))] + sizes

        if self.headers:
            headers = self.headers
            if self.show_row_numbers:
                headers = [''] + headers
            output += self._format_row(headers, sizes) + '\n'
            output += self._format_rule(sizes) + '\n'

        for i, row in enumerate(self.rows):
            if self.show_row_numbers:
                row = [i] + list(row)
            output += self._format_row(row, sizes) + '\n'

        return output.rstrip()

    def set_headers(self, *args):
        args = list(args)
        self._ensure_width(args)
        self._update_sizes(args)
        self.headers = args


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

    @staticmethod
    def _open_project():
        if not (PROJ_DIR / 'Makefile').exists():
            warn('There is no makefile in this directory. Are you sure you are in a project folder?')
            sys.exit(1)
        return ProjectMakefile(PROJ_DIR / 'Makefile')

    def list(self, argv):
        project = self._open_project()
        configurations, invalid = project.get_generators()
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

    def create_project(self, argv):
        parser = argparse.ArgumentParser(
            description='Create a new Halide project',
            usage='hlgen create project <name>')
        parser.add_argument('project_name', type=str,
                            help='The name of the project. This will also be the name of the directory created.')

        args = parser.parse_args(argv)

        if os.path.isdir(args.project_name):
            warn('project directory already exists!')
            sys.exit(1)

        os.mkdir(args.project_name)
        PROJ_DIR = Path(os.path.realpath(args.project_name))

        env = {'_HLGEN_BASE': TOOL_DIR,
               'NAME': args.project_name}

        self.init_from_skeleton(PROJ_DIR, env)

    def init_from_skeleton(self, project_path, env):
        skeleton_path = TOOL_DIR / 'skeleton'
        for root, _, files in os.walk(skeleton_path):
            skel_dir = Path(root)
            relative = skel_dir.relative_to(skeleton_path)
            proj_dir = project_path / relative

            os.makedirs(proj_dir, exist_ok=True)

            for file_name in files:
                with open(skel_dir / file_name, 'r') as f:
                    content = f.read()

                file_name = expand_template(file_name, env)
                with open(proj_dir / file_name, 'w') as f:
                    f.write(expand_template(content, env))


if __name__ == '__main__':
    HLGen()
