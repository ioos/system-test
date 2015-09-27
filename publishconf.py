#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

# This file is only used if you use `make publish` or
# explicitly specify it as your config file.

import os
import sys
sys.path.append(os.curdir)
from pelicanconf import *

SITEURL = 'https://ioos.github.io/system-test'

DELETE_OUTPUT_DIRECTORY = True

# Following items are often useful when publishing.

# Uncomment following line for absolute URLs in production:
# RELATIVE_URLS = False

GOOGLE_ANALYTICS = 'UA-9133259-16'
DISQUS_SITENAME = 'system-test'
