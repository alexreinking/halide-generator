#!/usr/bin/env python3
import argparse
import ast
import glob
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

TOOL_DIR = Path(os.path.dirname(os.path.realpath(__file__)))
PROJ_DIR = Path(os.path.realpath(os.getcwd()))


class CfgLine(object):
    def __init__(self, cfg):
        # Is there a way to do this without lazy groups?
        m = re.match(r'^CFG__(\w+?)(?:\s|__(\w+)?).*?=\s*(.*?)\s*$', cfg)
        self.gen, self.subcfg, self.val = m.group(1, 2, 3)
        self.gen = self.gen or ''
        self.subcfg = self.subcfg or ''
        self.val = self.val or ''
        self.orig = cfg

    def __repr__(self):
        return f'({self.gen}, {self.subcfg}) = {self.val} [{self.orig}]'


class ProjectMakefile(object):
    def __init__(self, path):
        if isinstance(path, str):
            path = Path(path)
        self.path = path

        with open(path, 'r') as f:
            self._lines = f.readlines()

        self._compute_landmarks()

    def _compute_landmarks(self):
        n_lines = len(self._lines)

        enum_lines = list(enumerate(self._lines))

        # Try to find the skeleton's landmark comment
        comment_line = next((i for i, line in enum_lines
                             if line.startswith('# Configure generators')), n_lines)

        # Find the first non-comment line after the landmark
        after_comment = next((i for i, line in enum_lines[comment_line + 1:]
                              if not line.startswith('#')), n_lines)

        # cfg_start is the very first line to create a configuration
        cfg_start = next((i for i, line in enum_lines
                          if line.startswith('CFG__')), n_lines)

        # cfg_end is the very last configuration that is contiguous with the first one, allowing
        # for intervening blank lines
        cfg_end = next((i for i, line in enum_lines[cfg_start + 1:]
                        if line.strip() and not line.strip().startswith('CFG__')), n_lines)

        # chop trailing blank lines
        cfg_end -= next((i for i, line in enumerate(self._lines[cfg_start:cfg_end][::-1])
                         if line.strip()), 0)

        self.after_comment = after_comment
        self.cfg_start = cfg_start
        self.cfg_end = cfg_end

    def lines(self):
        return self._lines

    def _parse_generators(self):
        gen_to_cfgs = {}
        invalid = []

        for gen in glob.glob(str(PROJ_DIR / '*.gen.cpp')):
            gen = os.path.basename(gen).rstrip('.gen.cpp')
            gen_to_cfgs[gen] = defaultdict(dict)

        for cfg in self._lines[self.cfg_start:self.cfg_end]:
            cfg = cfg.strip()
            if not cfg:
                continue

            line = CfgLine(cfg)
            if line.gen in gen_to_cfgs:
                if line.subcfg in gen_to_cfgs[line.gen]:
                    warn(f'Generator {line.gen} has duplicate configuration {line.subcfg}')
                    invalid.append(gen_to_cfgs[line.gen][line.subcfg])
                gen_to_cfgs[line.gen][line.subcfg] = line
            else:
                warn(f'Generator {line.gen} appears in Makefile but has no corresponding .gen.cpp')
                invalid.append(line)

        for gen_table in gen_to_cfgs.values():
            if not gen_table:
                gen_table[''] = None

        return gen_to_cfgs, invalid

    def get_generators(self):
        return self._parse_generators()

    def _insertion_point(self):
        n_lines = len(self._lines)
        if self.cfg_start < self.cfg_end and self.cfg_start < n_lines:
            return self.cfg_start
        return min(self.after_comment, n_lines)


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
    def __init__(self, width=0, colpadding=1):
        self.width = width
        self.sizes = [0] * width
        self.rows = []
        self.colpadding = colpadding

    def add_row(self, *args):
        if not self.width:
            self.width = len(args)
            self.sizes = [0] * self.width
        if len(args) == 0:
            self.rows.append(tuple([''] * self.width))
            return
        if len(args) != self.width:
            raise ValueError('arguments list not the same width')
        self.sizes = list(map(max, zip(self.sizes, map(len, args))))
        self.rows.append(tuple(args))

    def __str__(self):
        gutter = ' ' * self.colpadding

        template = ['{:<{}}'] * self.width
        template = (gutter + '|' + gutter).join(template)

        output = ''
        for row in self.rows:
            fmtargs = zip(row, self.sizes)
            output += template.format(*[x for y in fmtargs for x in y]) + '\n'
        return output


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

    def _require_project(self):
        if not (PROJ_DIR / 'Makefile').exists():
            warn('There is no makefile in this directory. Are you sure you are in a project folder?')
            sys.exit(1)

    def list(self, argv):
        self._require_project()
        project = ProjectMakefile(PROJ_DIR / 'Makefile')
        gens, invalid = project.get_generators()

        for cfg in invalid:
            warn(f'[BAD CFG] {cfg.orig}')

        if invalid:
            print()

        for gen in gens:
            table = Table()
            print(gens[gen])
            for cfg in gens[gen].values():
                table.add_row(gen, cfg.subcfg or '(default)', cfg.val)
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
