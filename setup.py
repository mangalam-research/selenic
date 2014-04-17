from setuptools import setup, find_packages

setup(
    name="selenic",
    version="0.3.0",
    packages=find_packages(),
    author="Louis-Dominique Dubeau",
    author_email="ldd@lddubeau.com",
    description="Some selenium infrastructure for testing.",
    license="MPL 2.0",
    keywords=["selenium", "testing"],
    url="https://github.com/mangalam-research/selenic",
    # use_2to3=True,
    classifiers=[
        "Programming Language :: Python",
        #"Programming Language :: Python :: 3",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Operating System :: POSIX",
        "Topic :: Software Development :: Version Control",
        "Topic :: Software Development :: Quality Assurance"
    ],
)
