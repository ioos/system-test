## IOOS System Test - Theme 2 - Exteme Events

## Scenario 2A - Coastal Inundation

### Notebook - Scenario_2A_ModelDataCompare_Currents

#### Progress report
Click [here] (https://github.com/ioos/system-test/issues/113) for a detailed report of the progress made in this notebook.

View the notebook in [nbviewer](http://nbviewer.ipython.org/github/ioos/system-test/blob/master/Theme_2_Extreme_Events/Scenario_2A_Coastal_Inundation/Scenario_2A_ModelDataCompare_Currents/Scenario_2A_Model_Obs_Compare_Currents.ipynb)

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
    conda install -c https://conda.binstar.org/rsignell iris=1.7.0_dev_RPS
    ```
    If you are using environments within conda, be sure to specify it
    ```bash
    conda install -n yourenvname --file conda-requirements.txt
    conda install -n yourenvname -c https://conda.binstar.org/rsignell iris=1.7.0_dev_RPS
    ```

#### Helper methods

Some helper functions have been abstracted into the file called `utilities.py`
so the IPython notebook can maintain a certain degree of readability.

**Note:** If your `gdal-config` binary is in an uncommon location, you may need
to specify the path when installing.
```bash
PATH=/your/path/to/gdal/bin:$PATH PIP_OR_CONDA_INSTALL_COMMAND
```
