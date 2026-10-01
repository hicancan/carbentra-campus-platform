"""Bundle the authoritative schemas into wheels without maintaining a second source."""
from pathlib import Path
import shutil
from setuptools import setup
from setuptools.command.build_py import build_py

class BuildWithSchemas(build_py):
    def run(self):
        super().run()
        root = Path(__file__).resolve().parent
        target = Path(self.build_lib) / 'carbentra_iot_contract' / 'data'
        shutil.copytree(root / 'schemas', target / 'schemas', dirs_exist_ok=True)
        shutil.copytree(root / 'protocols', target / 'protocols', dirs_exist_ok=True)
        shutil.copyfile(root / 'capabilities.json', target / 'capabilities.json')
        shutil.copyfile(root / 'products.json', target / 'products.json')

setup(cmdclass={'build_py': BuildWithSchemas})
