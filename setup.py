from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="adbh",
    version="0.1.1",
    author="Matt Hills",
    author_email="mattintech@gmail.com",
    description="A cross-platform ADB helper tool for Android device management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mattintech/adbhelper",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.1.0",
        "rich>=13.0.0",
        "pyyaml>=6.0",
        "psutil>=5.9.0",
        "watchdog>=3.0.0",
        "qrcode[pil]>=7.4.0",
        "zeroconf>=0.131.0",
        "spake2>=0.8",
        "cryptography>=41.0.0",
    ],
    entry_points={
        "console_scripts": [
            "adbhelper=adbhelper.cli:main",
            "adbh=adbhelper.cli:main",  # Short alias
        ],
    },
    include_package_data=True,
)