"""
Setup configuration for FastAPI Comprehensive Guide project.

This file enables the project to be installed as a package and manages dependencies.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="fastapi-comprehensive-guide",
    version="1.0.0",
    author="FastAPI Guide Team",
    author_email="example@example.com",
    description="A comprehensive FastAPI guide for beginners and advanced users",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/fastapi-guide",
    packages=find_packages(where="app"),
    package_dir={"": "app"},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.14",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Framework :: FastAPI",
    ],
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.109.0",
        "uvicorn[standard]>=0.27.0",
        "pydantic>=2.5.3",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.4",
            "pytest-asyncio>=0.23.3",
            "pytest-cov>=4.1.0",
            "black>=23.12.1",
            "isort>=5.13.2",
            "flake8>=7.0.0",
            "mypy>=1.8.0",
        ],
    },
)
