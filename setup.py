from distutils.core import setup
setup(
    name = 'python-awk',
    packages = ['pawk'],
    version = "0.0.10",
    description = 'Placeholder description',
    author = "Jason Trigg",
    author_email = "jasontrigg0@gmail.com",
    url = "https://github.com/jasontrigg0/pawk",
    download_url = 'https://github.com/jasontrigg0/pawk/tarball/0.0.10',
    scripts=["pawk/pawk"],
    install_requires=["jtutils",
                      "argparse",
                      "six"
    ],
    keywords = [],
    classifiers = [],
)
