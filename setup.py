import setuptools

# Kris 15/06/2023: taken from GSE-FOXSI-4

setuptools.setup(
    name="flarepred",
    version="0.0.1",
    description="Flare prediction code based on GOES data",
    url="https://github.com/pet00184/flarepred",
    install_requires=[
            "pandas==2.0.1",
            "pyqtgraph==0.13.3",
            "numpy==1.24.3", 
            "PyQt6",  
            "wget==3.2", 
            "matplotlib" 
        ],
    packages=setuptools.find_packages(),
    zip_safe=False
)