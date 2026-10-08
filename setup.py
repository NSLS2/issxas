"""Compatibility entry point; metadata lives in pyproject.toml."""
from setuptools import setup
from setuptools.command.build_py import build_py


class BuildLibrary(build_py):
    def find_package_modules(self, package, package_dir):
        return [entry for entry in super().find_package_modules(package, package_dir)
                if entry[1] != "scratch"]


setup(cmdclass={"build_py": BuildLibrary})
