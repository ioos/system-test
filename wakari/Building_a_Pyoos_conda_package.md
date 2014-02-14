##Building Pyoos as a Conda package on Wakari

From Ian Stokes-Rees at Continuum:
It is definitely possible to build conda recipes within Wakari. To do so, you'll need the "conda-build" package in your "root" env. This can be installed by doing:
```
conda install -n root conda-build

conda skeleton pypi pyoos
conda build pyoos
```
This will return a package error (paegan for me), so then you need to recurse to get packages for all the dependencies:
```
conda skeleton pypi paegan
conda build paegan
```
and continue recursing because this will require a "python-dateutil" package:
```
conda skeleton pypi python-dateutil
conda build python-dateutil
```
For me this worked, so I can then go back to paegan:
```
conda build paegan
```
And this won't work because you need to add "- setuptools" as one of the "run:" requirements in "paegan/meta.yaml" (right now it is only listed as a "build:" requirement, but the tests won't run without it). With that done, you can try to build again (or just fix it first and then build again):
```
conda build paegan
```
And then going back to pyoos:
```
conda build pyoos
```
will show that you'll need to repeat the above "skeleton" and "build" process for OWSLib, Fiona, beautifulsoup4, etc.

For Fiona, I had to add "- gdal" and "- setuptools" for both a "build:" and "run:" dependency in "fiona/meta.yaml"

For beautifulsoup4 I had to *remove* "beautifulsoup4" from the "import tests" in the "beautifulsoup4/meta.yaml" file.

For pyoos I ended up having to make a conda recipe for it that tweaked setup.py, removed "tests" from the testing regime, and set the "ignore egg dirs" flag.



At the end of all this, there is now a conda package available for linux-64 that you can get by doing:
```
conda install -c ijstokes pyoos
```
