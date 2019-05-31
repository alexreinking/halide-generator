import glob
import os
import re
from pathlib import Path
from typing import Union, Dict, Optional, List

from src.formatting import expand_template
from src.logging import warn

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

    def get_configurations(self):
        makefile = self.get_makefile()
        return makefile.get_generators()

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
                project._copy_from_skeleton(
                    relative / file_name,
                    {'_HLGEN_BASE': TOOL_DIR,
                     'NAME': project_name})
        return project

    def get_makefile(self):
        if not self._makefile:
            self._makefile = Makefile(self)
        return self._makefile

    def _copy_from_skeleton(self, relative, env):
        skel_file = TOOL_DIR / 'skeleton' / relative
        proj_file = self.root / relative

        with open(skel_file, 'r') as f:
            content = expand_template(f.read(), env)

        proj_file = proj_file.with_name(expand_template(proj_file.name, env))
        with open(proj_file, 'w') as f:
            f.write(content)

    def create_generator(self, generator_name):
        makefile = self.get_makefile()
        self._copy_from_skeleton(
            Path('${NAME}.gen.cpp'),
            {'_HLGEN_BASE': TOOL_DIR, 'NAME': generator_name})
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

    def save(self):
        if self._makefile:
            self._makefile.save()


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
        return self._render().rstrip() + '\n'

    def _render(self):
        if self.source:
            return self.source
        suffix = '' if not self.config_name else f'__{self.config_name}'
        return f'CFG__{self.generator}{suffix} = {self.params}'


class Makefile(object):
    def __init__(self, project: Project):
        self.project = project
        self.path = project.root / 'Makefile'

        with open(str(self.path), 'r') as f:
            self._lines = f.readlines()

        self.after_comment = len(self._lines)
        self.cfg_start = len(self._lines)
        self.cfg_end = len(self._lines)
        self._index: Dict[str, Dict[str, BuildConfig]] = {}

        self.current_configurations = []
        self.invalid_configurations = []
        self._regenerate()

    def get_generators(self):
        return self.current_configurations, self.invalid_configurations

    def _regenerate(self):
        cfgs = self._linearize_index()
        new_cfg_lines = [str(x).rstrip() + '\n'
                         for grp in self.interpose(cfgs, [''])
                         for x in grp]

        if self.cfg_start == self.cfg_end:
            prefix = self._lines[:self.after_comment]
            suffix = self._lines[self.after_comment:]
        else:
            prefix = self._lines[:self.cfg_start]
            suffix = self._lines[self.cfg_end:]

        self._lines = prefix + new_cfg_lines + suffix
        self._parse_makefile()

    def _parse_makefile(self):
        num_lines = len(self._lines)
        after_comment = num_lines
        cfg_start = num_lines
        cfg_end = num_lines

        configurations = []
        invalid_configurations = []
        generator2configs = {}

        # Create table for all the valid generators
        for gen in glob.glob(str(self.project.root / '*.gen.cpp')):
            gen = os.path.basename(gen).rstrip('.gen.cpp')
            generator2configs[gen] = {}

        last_cfg = num_lines

        # Populate table with configurations from makefile
        saw_generator_comment = False
        for line_idx, line in enumerate(self._lines):
            if not line.strip():
                if saw_generator_comment and after_comment == num_lines:
                    after_comment = line_idx
                continue

            if line.startswith('# Configure generators'):
                saw_generator_comment = True
            if saw_generator_comment and after_comment == num_lines and not line.strip().startswith('#'):
                after_comment = line_idx

            config = BuildConfig.from_makefile(line, line_idx)
            if cfg_start == num_lines and config:
                cfg_start = line_idx

            if cfg_end == num_lines and config:
                if config.generator not in generator2configs:
                    warn(f'invalid configuration specified for {config.generator} in Makefile:{line_idx + 1}')
                    invalid_configurations.append(config)
                else:
                    if config.config_name in generator2configs[config.generator]:
                        warn(f'using overriding configuration for {config.generator} from Makefile:{line_idx + 1}')
                        old_config = generator2configs[config.generator][config.config_name]
                        configurations.remove(old_config)
                        invalid_configurations.append(old_config)
                    generator2configs[config.generator][config.config_name] = config
                    configurations.append(config)
                last_cfg = line_idx

            if cfg_start < num_lines and cfg_end == num_lines and not config:
                cfg_end = last_cfg + 1

        # If any generators didn't appear in the makefile, they get default configurations inferred
        for gen in generator2configs:
            if not generator2configs[gen]:
                generator2configs[gen][''] = BuildConfig(gen, '', '')
                configurations.append(BuildConfig(gen, '', ''))

        self._index = generator2configs
        self.after_comment = after_comment
        self.cfg_start = cfg_start
        self.cfg_end = cfg_end
        self.current_configurations = configurations
        self.invalid_configurations = invalid_configurations

    def has_generator(self, name):
        return name in self._index

    def add_generator(self, name):
        if self.has_generator(name):
            raise ValueError(f'generator {name} already exists!')
        self._index[name] = {}
        self._index[name][''] = BuildConfig(name, '', '')

    def save(self):
        with open(str(self.path), 'w') as f:
            f.writelines(self._lines)

    def add_configuration(self, gen, name, params):
        if gen not in self._index:
            raise ValueError(f'no generator named {gen}')
        if name == '(default)':
            name = ''
        if name in self._index[gen]:
            raise ValueError(f'configuration {name or "(default)"} already exists. use update configuration instead')
        config = BuildConfig(gen, name, params)
        self.current_configurations.append(config)
        self._index[gen][name] = config
        self._regenerate()

    @staticmethod
    def interpose(it, x):
        past_start = False
        for i in it:
            if past_start:
                yield x
            yield i
            past_start = True

    def _linearize_index(self) -> List[List[BuildConfig]]:
        cfgs = []
        for gen, gen_cfgs in self._index.items():
            # when the only entry is the default one, don't put it in the makefile
            if len(gen_cfgs) == 1 and '' in gen_cfgs and not gen_cfgs[''].params:
                continue
            cfgs.append(list(sorted(gen_cfgs.values(), key=lambda cfg: cfg.config_name)))
        cfgs.sort(key=lambda grp: grp[0].generator)
        return cfgs

    def delete_configuration(self, generator_name, config_name):
        if generator_name not in self._index:
            raise ValueError(f'no generator named {generator_name}')
        if config_name == '(default)':
            config_name = ''
        if config_name not in self._index[generator_name]:
            raise ValueError(f'no configuration named {config_name or "(default)"} for generator {generator_name}')
        if len(self._index[generator_name]) == 1:
            raise ValueError(f'cannot leave generator unconfigured. use \'delete generator\' to delete a generator.')
        del self._index[generator_name][config_name]
        self._regenerate()
