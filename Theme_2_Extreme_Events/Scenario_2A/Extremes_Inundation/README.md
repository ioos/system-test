# IOOS System Test - Theme 2 - Exteme Events

## Scenario 2A - Coastal Inundation

### Extreme Value Analysis - Inundation

#### Requirements

1. Using `pip`
    ```bash
    pip install -r pip-requirements.txt
    pip install git+https://github.com/wrobstory/folium.git#egg=folium
    pip install git+https://github.com/SciTools/cartopy.git@v0.10.0
    pip install git+https://github.com/SciTools/iris.git@v1.6.1
    ```

2. Using `conda`
    ```bash
    conda install --file conda-requirements.txt
    conda install -c https://conda.binstar.org/rsignell iris prettyplotlib
    ```
    If you are using environments within conda, be sure to specify it
    ```bash
    conda install -n yourenvname --file conda-requirements.txt
    conda install -n yourenvname -c https://conda.binstar.org/rsignell iris prettyplotlib
    ```

#### Helper methods

Some helper functions have been abstracted into the file called `utilities.py`
so the IPython notebook can maintain a certain degree of readability.


**Note:** If your HDF5 and/or NETCDF4 libraries are in uncommon locations, you
may need to specify the paths when installing netCDF4.
```bash
HDF5_DIR=/your/path/to/hdf5 NETCDF4_DIR=/your/path/to/netcdf4 PIP_OR_CONDA_INSTALL_COMMAND
```

**Note:** If your `gdal-config` binary is in an uncommon location, you may need
to specify the path when installing.
```bash
PATH=/your/path/to/gdal/bin:$PATH PIP_OR_CONDA_INSTALL_COMMAND
```
