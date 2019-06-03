import os
import shutil
from pathlib import Path
from unittest import TestCase

from src.project import Project

TEST_DIR = Path(os.path.dirname(os.path.realpath(__file__)))


class TestProject(TestCase):

    def setUp(self) -> None:
        self._old_cwd = os.getcwd()
        self.test_root = TEST_DIR / 'test_root'
        self.test_root.mkdir(parents=True, exist_ok=False)
        os.chdir(self.test_root)

    def test_create_simple_project(self):
        project = Project.create_new('simple')
        self.assertIsNotNone(project)
        cfgs, invalid = project.get_configurations()
        self.assertEqual(invalid, [])
        self.assertEqual(len(cfgs), 1)
        simple_cfg = cfgs[0]
        self.assertEqual(simple_cfg.generator, 'simple')
        self.assertEqual(simple_cfg.config_name, None)
        self.assertEqual(simple_cfg.params, '')

    def tearDown(self) -> None:
        os.chdir(self._old_cwd)
        shutil.rmtree(self.test_root)
