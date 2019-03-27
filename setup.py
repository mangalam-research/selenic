from setuptools import setup, find_packages

version = open('VERSION').read().strip()

setup(
    name="selenic",
    version=version,
    packages=find_packages(),
    author="Louis-Dominique Dubeau",
    author_email="ldd@lddubeau.com",
    description="Some selenium infrastructure for testing.",
    license="MPL 2.0",
    keywords=["selenium", "testing"],
    url="https://github.com/mangalam-research/selenic",
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Operating System :: POSIX",
        "Topic :: Software Development :: Version Control",
        "Topic :: Software Development :: Quality Assurance"
    ],
)
