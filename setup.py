import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="instruments",  # Replace with your own username
    version="0.1",
    author="Jean-Loup Smirr",
    author_email="jean-loup.smirr@college-de-france.fr",
    description="Python interface for VISA instruments",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/FluxQuantumLab/instruments",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
