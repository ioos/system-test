# IOOS System Test - Theme 1 - Baseline

## Scenario 1B - Core Variable Strings

Using a list of Core IOOS Variables and the MMI SPARQL service, can we search and quantify records from CSW endpoints that relate to core variables?


#### Requirements

1. Using `pip`
    ```bash
    pip install -r pip-requirements.txt
    ```

2. Using `conda`
    ```bash
    conda install --file conda-requirements.txt
    ```
    If you are using environments within conda, be sure to specify it
    ```bash
    conda install -n yourenvname --file conda-requirements.txt
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
