import setuptools

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="zerobot",
    version="1.0.0",
    description="Zerobot",
    url="https://github.com/CitadelCore/Zerobot",
    author="Alex Zero",
    author_email="me@alex0.net",
    license="mit",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(include=["zerobot", "zerobot.*"]),
    package_data={"zerobot": ["assets/**"]},
    include_package_data=True,
    entry_points={"console_scripts": ["zerobot = zerobot.entrypoint:main"]},
    classifiers=[
        "Programming Language :: Python :: 3"
    ],
    python_requires=">=3.9",
    install_requires=[
        "accelerate",
        "aiofiles",
        "aiosqlite",
        "torch>=1.3",
        "datasets>=1.8.0",
        "disnake",
        "evaluate",
        "protobuf",
        "tensorflow",
        "toml",
        "sklearn",
        "sentencepiece!=0.1.92"
        "sqlalchemy",
        "sqlalchemy[asyncio]"
    ],
    dependency_links=[
        "https://download.pytorch.org/whl/cu116/torch"
    ]
)
