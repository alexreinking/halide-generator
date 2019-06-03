from itertools import product
from unittest import TestCase

from src.makefile import BuildConfig


class TestBuildConfig(TestCase):
    def test_from_makefile(self):
        generator_names = ['foo', 'f_oo']
        config_names = [None, 'bar', '_bar', 'bar_', '_bar_', '__bar', 'bar__', '__bar__']
        values = ['', 'baz', 'baz test', '   fooo    ']
        spacing = [0, 1, 10]

        # Test a combination of tricky, but valid, configuration lines
        for test_case in product(generator_names, config_names, values, spacing, spacing):
            generator, config_name, params, lspace, rspace = test_case
            lspace = ' ' * lspace
            rspace = ' ' * rspace

            if config_name is None:
                line = f'CFG__{generator}{lspace}={rspace}{params}'
            else:
                line = f'CFG__{generator}__{config_name}{lspace}={rspace}{params}'

            with self.subTest(msg=line):
                config = BuildConfig.from_makefile(line)
                self.assertIsNotNone(config)
                self.assertEqual(config.generator, generator)
                self.assertEqual(config.config_name, config_name)
                self.assertEqual(config.params, params.strip())

        # Test all the previous combinations, but with an illegal empty config name.
        # These should throw a ValueError
        for test_case in product(generator_names, values, spacing, spacing):
            generator, params, lspace, rspace = test_case
            lspace = ' ' * lspace
            rspace = ' ' * rspace

            line = f'CFG__{generator}__{lspace}={rspace}{params}'

            with self.subTest(msg=line):
                self.assertRaises(ValueError, lambda: BuildConfig.from_makefile(line))
