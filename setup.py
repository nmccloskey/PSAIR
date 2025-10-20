from setuptools import setup, find_packages
from pathlib import Path

# Read requirements.txt
def read_requirements():
    req_file = Path(__file__).parent / "requirements.txt"
    return req_file.read_text().splitlines() if req_file.exists() else []

setup(
    name="infoscopy",
    version="0.1.0",
    description="A backend scaffold for data analysis pipelines",
    author="Nick McCloskey",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=read_requirements(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)
