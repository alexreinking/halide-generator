import os
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase

from src.makefile import BuildConfig
from src.project import Project

TEST_DIR = Path(os.path.dirname(os.path.realpath(__file__)))


class TestProject(TestCase):

    def setUp(self) -> None:
        self._old_cwd = os.getcwd()
        self.test_root = Path(tempfile.mkdtemp(suffix='.hltest'))
        os.chdir(self.test_root)

    def test_create_simple_project(self):
        with TestCaseProject(self) as project:
            # Check that it creates the right set
            cfgs, invalid = project.get_configurations()
            self.assertEqual(invalid, [])
            self.assertEqual(set(cfgs), {BuildConfig(project.name, None, '')})

    def test_create_generators(self):
        with TestCaseProject(self) as project:
            # Add a new generator and a configuration
            project.create_generator('gen2')
            project.create_configuration('gen2', 'foo', 'bar=baz')

            # Check that it creates the right set
            cfgs, invalid = project.get_configurations()
            self.assertEqual(invalid, [])
            self.assertEqual(set(cfgs),
                             {BuildConfig(project.name, None, ''),
                              BuildConfig('gen2', None, ''),
                              BuildConfig('gen2', 'foo', 'bar=baz')})

    def test_delete_default_config(self):
        with TestCaseProject(self) as project:
            # Add new config, delete default
            project.create_configuration(project.name, 'foo', 'target=host-cuda')
            project.delete_configuration(project.name, None)

            # Check that it creates the right set
            cfgs, invalid = project.get_configurations()
            self.assertEqual(invalid, [])
            self.assertEqual(set(cfgs), {BuildConfig(project.name, 'foo', 'target=host-cuda')})

    def test_delete_default_generator(self):
        with TestCaseProject(self) as project:
            # Empty out the project
            project.delete_generator(project.name)

            # Check that it creates the right set
            cfgs, invalid = project.get_configurations()
            self.assertEqual(cfgs, [])
            self.assertEqual(invalid, [])

    def tearDown(self) -> None:
        os.chdir(self._old_cwd)
        shutil.rmtree(self.test_root)


class TestCaseProject(object):
    def __init__(self, test_case: TestProject):
        self.test_case = test_case
        project_name = test_case.id().split('.')[-1]  # due to https://stackoverflow.com/a/14954405/2137996
        self.project = Project.create_new(project_name)
        test_case.assertIsNotNone(self.project)

    def __enter__(self):
        return self.project

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            cfgs, invalid = self.project.get_configurations()
            self.project.save()
            project_from_disk = Project(self.project.root)

            cfgs_from_disk, invalid_from_disk = project_from_disk.get_configurations()
            self.test_case.assertEqual(set(cfgs), set(cfgs_from_disk))
            self.test_case.assertEqual(set(invalid), set(invalid_from_disk))
