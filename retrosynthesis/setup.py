from setuptools import setup, find_packages

def readfile(filename):
    with open(filename, 'r+') as f:
        return f.read()

setup(
    name="RetroSynthesis",
    version="0.0.1",
    description="Generate potential heterologous pathways between an organism of interest and a target molecule",
    #long_description=readfile('../README.md'),
    author="melclic",
    author_email="melclic1988@gmail.com",
    url="https://github.com/Melclic/metaxime",
    py_modules=[''],
    #license=readfile('../LICENSE'),
    entry_points={
        'console_scripts': [
            'rppipeline = retroPipeline:main',
            'retrorules = runRR:main',
            'runRP2paths = runRP2paths:main',
            'runRP2 = runRP2:main',
        ]
    },
)
