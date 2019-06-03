import glob
import os
import re
from pathlib import Path
from typing import Dict, Optional

from src.logging import warn


def interpose(it, x):
    past_start = False
    for i in it:
        if past_start:
            yield x
        yield i
        past_start = True


class BuildConfig(object):
    _cfg_line_re = re.compile(r'^CFG__(\w+?)(?:__(\w*))?[ \t]*=[ \t]*([^\s].*?)?[ \t]*$')

    def __init__(self, generator: str, config_name: Optional[str] = None, value: Optional[str] = None, *, source=None):
        if not generator:
            raise ValueError('cannot define nameless generator!')
        if config_name == '':
            raise ValueError('config_name cannot be empty string!')
        self.generator = generator
        self.config_name = config_name
        self.params = (value or '').strip()
        self.source = source

    @staticmethod
    def from_makefile(source):
        # Is there a way to do this without lazy groups?
        m = BuildConfig._cfg_line_re.match(str(source))
        if not m:
            return None
        return BuildConfig(*m.group(1, 2, 3), source=source)

    def __repr__(self):
        return self._render()

    def __str__(self):
        return self._render().rstrip() + '\n'

    def _render(self):
        if self.source:
            return self.source
        suffix = '' if not self.config_name else f'__{self.config_name}'
        return f'CFG__{self.generator}{suffix} = {self.params}'


class Makefile(object):
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.path = project_root / 'Makefile'

        with open(str(self.path), 'r') as f:
            self._lines = f.readlines()

        self.after_comment = len(self._lines)
        self.cfg_start = len(self._lines)
        self.cfg_end = len(self._lines)
        self._index: Dict[str, Dict[str, BuildConfig]] = {}

        self.current_configurations = []
        self.invalid_configurations = []
        self._regenerate()

    def save(self):
        with open(str(self.path), 'w') as f:
            f.writelines(self._lines)

    def has_generator(self, generator_name):
        return generator_name in self._index

    def get_generators(self):
        return self.current_configurations, self.invalid_configurations

    def add_generator(self, generator_name):
        if self.has_generator(generator_name):
            raise ValueError(f'generator {generator_name} already exists!')
        self._index[generator_name] = {}
        self._index[generator_name][''] = BuildConfig(generator_name, None, None)

    def add_configuration(self, generator_name, config_name, params):
        if generator_name not in self._index:
            raise ValueError(f'no generator named {generator_name}')
        if config_name == '(default)':
            config_name = ''
        if config_name in self._index[generator_name]:
            raise ValueError(
                f'configuration {config_name or "(default)"} already exists. use update configuration instead')
        config = BuildConfig(generator_name, config_name, params)
        self.current_configurations.append(config)
        self._index[generator_name][config_name] = config
        self._regenerate()

    def update_configuration(self, generator_name, config_name, new_params):
        pass

    def delete_generator(self, name):
        if name not in self._index:
            raise ValueError(f'no generator named {name}')
        del self._index[name]
        self._regenerate()

    def delete_configuration(self, generator_name, config_name):
        if generator_name not in self._index:
            raise ValueError(f'no generator named {generator_name}')
        if config_name == '(default)':
            config_name = None
        if config_name not in self._index[generator_name]:
            print(repr(config_name))
            print(self._index[generator_name])
            raise ValueError(f'no configuration named {config_name} for generator {generator_name}')
        if len(self._index[generator_name]) == 1:
            raise ValueError(f'cannot leave generator unconfigured. use \'delete generator\' to delete a generator.')
        del self._index[generator_name][config_name]
        self._regenerate()

    def _regenerate(self):
        cfgs = self._linearize_index()
        new_cfg_lines = [str(x).rstrip() + '\n'
                         for grp in interpose(cfgs, [''])
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
        for gen in glob.glob(str(self.project_root / '*.gen.cpp')):
            gen = os.path.basename(gen)[:-len('.gen.cpp')]
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

            config = BuildConfig.from_makefile(line)
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
                default_config = BuildConfig(gen, None, None)
                generator2configs[gen][None] = default_config
                configurations.append(default_config)

        self._index = generator2configs
        self.after_comment = after_comment
        self.cfg_start = cfg_start
        self.cfg_end = cfg_end
        self.current_configurations = configurations
        self.invalid_configurations = invalid_configurations

    def _linearize_index(self):
        cfgs = []
        for gen, gen_cfgs in self._index.items():
            # when the only entry is the default one, don't put it in the makefile
            if len(gen_cfgs) == 1 and '' in gen_cfgs and not gen_cfgs[''].params:
                continue
            cfgs.append(list(sorted(gen_cfgs.values(), key=lambda cfg: cfg.config_name or '')))
        cfgs.sort(key=lambda grp: grp[0].generator)
        return cfgs
