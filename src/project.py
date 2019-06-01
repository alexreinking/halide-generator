import os
from pathlib import Path
from typing import Union, Optional

from src.formatting import expand_template
from src.logging import warn
from src.makefile import Makefile

TOOL_DIR = Path(os.path.dirname(os.path.realpath(os.path.join(__file__, '..'))))


class Project(object):
    def __init__(self, root: Optional[Union[Path, str]] = None):
        if isinstance(root, str):
            root = Path(root)
        if not root:
            root = Path(os.path.realpath(os.getcwd()))
        if not root.is_dir():
            raise ValueError(f'project directory {root} does not exist')
        self.root = root
        self._makefile = None

    @staticmethod
    def create_new(project_name):
        if os.path.isdir(project_name):
            raise ValueError(f'project directory {project_name} already exists!')

        os.mkdir(project_name)
        project = Project(os.path.realpath(project_name))
        skeleton_path = TOOL_DIR / 'skeleton'
        for root, _, files in os.walk(skeleton_path):
            relative = Path(root).relative_to(skeleton_path)

            os.makedirs(project.root / relative, exist_ok=True)
            for file_name in files:
                project._copy_from_skeleton(relative / file_name, {'NAME': project_name})
        return project

    def get_makefile(self):
        if not self._makefile:
            self._makefile = Makefile(self.root)
        return self._makefile

    def get_configurations(self):
        makefile = self.get_makefile()
        return makefile.get_generators()

    def save(self):
        if self._makefile:
            self._makefile.save()

    def create_generator(self, generator_name):
        makefile = self.get_makefile()
        self._copy_from_skeleton(Path('${NAME}.gen.cpp'), {'NAME': generator_name})
        makefile.add_generator(generator_name)

    def create_configuration(self, generator_name, config_name, params):
        makefile = self.get_makefile()
        makefile.add_configuration(
            generator_name,
            config_name,
            ' '.join(params)
        )

    def delete_configuration(self, generator_name, config_name):
        makefile = self.get_makefile()
        makefile.delete_configuration(
            generator_name,
            config_name)

    def delete_generator(self, name):
        makefile = self.get_makefile()
        if not makefile.has_generator(name):
            raise ValueError(f'no generator named {name}')
        source_path = self.root / (name + '.gen.cpp')
        if not source_path.is_file():
            warn(f'expected file {source_path} not removing')
        else:
            source_path.unlink()
        makefile.delete_generator(name)

    def _copy_from_skeleton(self, relative, env):
        skel_file = TOOL_DIR / 'skeleton' / relative
        proj_file = self.root / relative

        with open(skel_file, 'r') as f:
            content = expand_template(f.read(), env)

        proj_file = proj_file.with_name(expand_template(proj_file.name, env))
        with open(proj_file, 'w') as f:
            f.write(content)
