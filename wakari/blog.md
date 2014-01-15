#Creating your own BLOG environment on Wakari

To build your own `pyoos` environment on Wakari, first create a `blog` environment with all the 
necessary conda packages. You can do this by loading an existing conda "spec" file, which is just a text file list of packages.  Here's mine:  https://github.com/ioos/system-test/blob/master/wakari/pyoos.spec

This particular list may contain
more packages than is strictly needed for the blog -- I made it by typing in my Wakari account:
```
source activate blog
conda list -e | tee blog.spec
```
##Recipe

* Create the `blog` environment with the necessary conda packages:
```
mkdir $HOME/blog
cd $HOME/blog
wget https://raw2.github.com/ioos/system-test/master/wakari/blog.spec
conda create --name blog --file blog.spec
```


* Activate the `blog` environment:  
```
source activate blog
```

* Go to https://github.com/rsignell-usgs/blog and click the `fork` button to fork my blog repository.
* In Wakari, clone your blog repository from github, for example:
```
git clone https://github.com/dpsnowden/blog.git
```

* You should now have a $HOME/blog/blog directory.
* See if pandoc is working by typing `which pandoc` and see if it returns `/opt/anaconda/bin/pandoc`
* Edit the `pelicanconf.py` and `publishconf.py` files and customize for your settings. 
* Edit the ./octopress-theme/templates/_includes/{about.html, twitter.html} files and customize for your settings.

* Create a SSH keypair to use for pushing from Wakari to Github pages:
* Add the SSH public key $HOME/.ssh/id_rsa.pub in your Github user settings
* Add lines to `$HOME\.bashrc` to start SSH agent
* New notebooks go in `$HOME\blog\blog\content\downloads\notebooks`
* Create a new markdown file in `$HOME\blog\blog\content that points to the new notebook
* In the directory `$HOME\blog\blog`, type `make github` to convert notebooks to html and push to gh-pages
