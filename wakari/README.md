# Custom Wakari environments that facilitate the system-test

To install packages on Wakari, first check to see if a conda package is available at binstar.org.  
Search for the package name, then click on the `Conda` tab to narrow the results down to conda packages only.
Binstar will show you the install instructions.

Here are some:

* PYOOS :  `conda install -c rsignell pyoos`
* IRIS  :  `conda install -c rsignell iris`
* ULMO : `conda install -c rsignell ulmo`

So to build a complete environment for the system-test on Wakari, do this:

```
conda create -n ioos_np18py27 python=2.7 numpy=1.8 pandas matplotlib netcdf4 ipython ipython-notebook scipy
source activate ioos_np18py27
conda install -c rsignell pyoos iris ulmo
```

If you are interesting in blogging with Ipython notebooks on Wakari, check this out:
https://github.com/rsignell-usgs/blog/blob/master/wakari.md
