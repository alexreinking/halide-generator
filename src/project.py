import glob
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Union, DefaultDict, Dict, Optional

from logging import warn


class Project(object):
    def __init__(self, root: Optional[Union[Path, str]] = None):
        if isinstance(root, str):
            root = Path(root)
        if not root:
            root = Path(os.path.realpath(os.getcwd()))
        self.root = root

    def get_makefile(self):
        return ProjectMakefile(self)


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


class ProjectMakefile(object):
    def __init__(self, project: Project):
        self.project = project
        self.path = project.root / 'Makefile'

        with open(str(self.path), 'r') as f:
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
        for gen in glob.glob(str(self.project.root / '*.gen.cpp')):
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

        self._index: DefaultDict[str, Dict[str, BuildConfig]] = defaultdict(dict)
        for config in configurations:
            self._index[config.generator][config.config_name] = config

        self.after_comment = after_comment
        self.cfg_start = cfg_start
        self.cfg_end = cfg_end

        return configurations, invalid_configurations

    def has_generator(self, name):
        return name in self._index

    def add_generator(self, name):
        if self.has_generator(name):
            raise ValueError('cannot add a new generator when one already exists')
        self._index[name][''] = BuildConfig(name, '', '')

    def save(self):
        with open(str(self.path), 'w') as f:
            f.writelines(self._lines)

    def add_configuration(self, gen, name, params):
        if name in self._index[gen]:
            raise ValueError('use update_configuration to update in place (without rearranging makefile)')
        config = BuildConfig(gen, name, params)
        self._gens.append(config)
        self._index[gen][name] = config
        self._regenerate()

    def _regenerate(self):
        if self.cfg_start < len(self._lines):
            cfg_start = self.cfg_start
            cfg_end = self.cfg_end
        elif self.after_comment < len(self._lines):
            cfg_start = self.after_comment
            cfg_end = self.after_comment
        else:
            cfg_start = cfg_end = len(self._lines)

        prefix = self._lines[:cfg_start]
        suffix = self._lines[cfg_end:]

        cfgs = []
        for gen, gen_cfgs in self._index.items():
            # when the only entry is the default one, don't put it in the makefile
            if len(gen_cfgs) == 1 and '' in gen_cfgs and not gen_cfgs[''].params:
                continue
            cfgs.extend(map(str, gen_cfgs.values()))

        self._lines = prefix + cfgs + suffix
        self._parse_makefile()
