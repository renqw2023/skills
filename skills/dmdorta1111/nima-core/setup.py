from setuptools import setup, find_packages

setup(
    name="nima-core",
    version="1.1.0",
    description="Biologically-inspired cognitive memory architecture for AI agents",
    long_description=open("README.md").read() if __import__("os").path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="NIMA Project",
    url="https://github.com/nima-project/nima-core",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "torch>=2.0.0",
        "numpy>=1.24.0",
        "sentence-transformers>=2.2.0",
        "scikit-learn>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "nima-core=nima_core.cli.setup:main",
            "nima-capture=nima_core.capture_message:main",
            "nima-recall=nima_core.recall_query:main",
            "nima-dream=nima_core.dream:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Programming Language :: Python :: 3",
    ],
)
