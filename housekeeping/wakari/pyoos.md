#Creating your own PYOOS environment on Wakari

To build your own `pyoos` environment on Wakari, first create a `conda` environment with all the 
necessary conda packages. You can do this by loading an existing conda "spec" file, which is just a text file list of packages.  Here's mine:  https://github.com/ioos/system-test/blob/master/wakari/pyoos.spec

This particular list may contain
more packages than is strictly needed for pyoos -- I made it by typing in my Wakari account:
```
source activate pyoos
conda list -e | tee pyoos.spec
```
So here's what you type in Wakari's shell terminal to replicate this environment. 

First load the conda packages:
```
mkdir $HOME/pyoos-env
cd $HOME/pyoos-env
wget https://raw2.github.com/ioos/system-test/master/wakari/pyoos.spec
conda create --name pyoos --file pyoos.spec
```
Activate the pyoos environment:
```
source activate pyoos
```


Then install the paegan and pyoos packages using pip:
```
pip install -e git+https://github.com/asascience-open/paegan.git#egg=paegan
pip install -e git+https://github.com/asascience-open/pyoos.git#egg=pyoos
```

(Or, install paegan and pyoos using a git clone fallback method):
```
git clone https://github.com/asascience-open/paegan.git
pip install -e ./paegan
git clone https://github.com/asascience-open/pyoos.git
pip install -e ./pyoos
```
