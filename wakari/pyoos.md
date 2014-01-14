To build pyoos environment on wakari:
```
conda create --name pyoos --file pyoos.spec
```
https://github.com/ioos/system-test/blob/master/wakari/pyoos.spec

then: 
```
source activate pyoos

mkdir pyoos-env
cd pyoos-env

git clone https://github.com/asascience-open/paegan.git
pip install -e ./paegan
git clone https://github.com/asascience-open/pyoos.git
pip install -e ./pyoos
```
