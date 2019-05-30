#!/usr/bin/env python3
from pathlib import Path
import argparse
import ast
import os
import re
import sys
import warnings 

TOOL_DIR = os.path.dirname(os.path.realpath(__file__))
PROJ_DIR = os.path.realpath(os.getcwd())

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
        args = [env.get(name) or '' for name in names]
        return f(*args)

    # TODO: do something smarter here for matching { }
    return re.sub(r'\${([^}]+)}', lambda m: expand(m.group(1)), template)

def get_halide_directory():
    hldir = os.environ.get('HALIDE_DISTRIB_PATH')
    if not hldir:
        hldir = '/opt/halide'
    return os.path.realpath(hldir) if os.path.isdir(hldir) else None

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

    def create(self, argv):
        parser = argparse.ArgumentParser(
            description='Create a new Halide project, generator, or configuration',
            usage='hlgen create <item_type> [<args>]')
        parser.add_argument('item_type', type=str, choices=['project', 'generator', 'configuration'], help='what kind of item to create')

        args = parser.parse_args(argv[:1])
        method = f'create_{args.item_type}'

        getattr(self, method)(argv[1:])

    def create_project(self, argv):
        parser = argparse.ArgumentParser(
                description='Create a new Halide project',
                usage='hlgen create project <name>')
        parser.add_argument('project_name', type=str, help='The name of the project. This will also be the name of the directory created.')

        args = parser.parse_args(argv)
        
        if os.path.isdir(args.project_name):
            warnings.warn('project directory already exists!', Warning)
            sys.exit(1)

        os.mkdir(args.project_name)
        PROJ_DIR = os.path.realpath(args.project_name)
        
        env = { '_HLGEN_BASE': TOOL_DIR,
                'NAME': args.project_name }

        self.init_from_skeleton(PROJ_DIR, env)

    def init_from_skeleton(self, dst, env):
        skeleton_path = Path(TOOL_DIR) / 'skeleton'
        project_path = Path(dst)
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
