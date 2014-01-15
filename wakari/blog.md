#Creating your own BLOG environment on Wakari

To build your own `pyoos` environment on Wakari, first create a `blog` environment with all the 
necessary conda packages. You can do this by loading an existing conda "spec" file, which is just a text file list of packages.  Here's mine:  https://github.com/ioos/system-test/blob/master/wakari/pyoos.spec

This particular list may contain
more packages than is strictly needed for the blog -- I made it by typing in my Wakari account:
```
source activate blog
conda list -e | tee blog.spec
```
So here's what you type in Wakari to replicate this environment. 

First load the conda packages:
```
mkdir $HOME/blog
cd $HOME/blog
wget https://raw2.github.com/ioos/system-test/master/wakari/blog.spec
conda create --name blog --file blog.spec
```


then clone my blog environment from github:  
```
source activate blog
git clone https://github.com/rsignell-usgs/blog.git
```
