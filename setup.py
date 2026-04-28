from pathlib import Path

from setuptools import find_packages, setup


APP_NAME = "company_creation"


def read_requirements() -> list[str]:
	requirements_file = Path("requirements.txt")
	if not requirements_file.exists():
		return []
	return [
		line.strip()
		for line in requirements_file.read_text(encoding="utf-8").splitlines()
		if line.strip() and not line.strip().startswith("#")
	]


version = {}
with open(Path(APP_NAME) / "__init__.py", encoding="utf-8") as f:
	exec(f.read(), version)


setup(
	name=APP_NAME,
	version=version.get("__version__", "0.0.1"),
	description="Custom app to handle company formation requests",
	author="Fatiha khassil",
	author_email="fatiha.khassil1@gmail.com",
	packages=find_packages(),
	include_package_data=True,
	zip_safe=False,
	install_requires=read_requirements(),
)
