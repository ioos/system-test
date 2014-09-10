# IOOS System Test - Theme 2 - Extreme Events

## Scenario 2A - Coastal Inundation

### Comprehensive spin-off notebook

#### Requirements

1. Using `pip`
    ```bash
    pip install -r pip-requirements.txt
    pip install git+https://github.com/birdage/folium.git@clustered_markers#egg=folium    
    ```

2. Using `conda`
    ```bash
    conda install --file conda-requirements.txt
    ```
    If you are using environments within conda, be sure to specify it
    ```bash
    conda install -n yourenvname --file conda-requirements.txt
    ```
    
    You will still have to pip install folium
    pip install git+https://github.com/birdage/folium.git@clustered_markers#egg=folium


#### Helper methods

Some helper functions have been abstracted into the file called `utilities.py`
so the IPython notebook can maintain a certain degree of readability.


**Note:** If your `gdal-config` binary is in an uncommon location, you may need
to specify the path when installing.
```bash
PATH=/your/path/to/gdal/bin:$PATH PIP_OR_CONDA_INSTALL_COMMAND
```
