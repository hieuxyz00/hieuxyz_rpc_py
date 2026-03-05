from setuptools import setup, find_packages

setup(
    name="hieuxyz-rpc",
    version="0.0.2",
    author="hieuxyz",
    author_email="khongbt446@gmail.com",
    description="A powerful Discord Rich Presence library for Python",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/hieuxyz00/hieuxyz_rpc_py",
    project_urls={
        "Bug Tracker": "https://github.com/hieuxyz00/hieuxyz_rpc_py/issues",
    },
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.11"
)