tumblrgetpics
=============

This little bundle of code is a picture scraper for Tumblr.

License and Copyright 
---------------------

MIT License and Copyright (C) 2013 jonmsawyer

Requires
--------

This little app requires Python. It is tested on 2.7, but I think 2.6
will work.

Platform
--------

This app will run on Linux, Mac, and Windows. Unfortunately, Windows
doesn't have `symlinks` so Windows can't utilize the full intended
power of `tumblrgetpics`. But, never fret.

Running the app
---------------

`cd` into the directory where this script lives and execute `./getpics.py`
or do `$ python getpics.py`. Note: this script is designed to be executed
in the directory where `getpics.py` is located. A folder called "pics"
will be made followed by the rest of the pictures scraped from the site.

Usage: `./getpics.py [blogname [blogname ...]]`

blogname - the name of the blog. If you want http://myblog.tumblr.com, use `myblog`

Withough arguments: `./getpics.py` will finish downloading pictures from any
interrupted users. If there are no users in the `TODO_LIST`, then `./getpics.py`
will check and download any *new* pictures from ALL blogs in `USER_LIST`.

Examples:

`$ ./getpics.py`
> Finish everything in `TODO_LIST`. If `TODO_LIST` is empty, fetch everything
> in `USER_LIST`

`$ ./getpics.py myblog hisblog herblog`
> Fetch all pictures in these blogs located at http://myblog.tumblr.com,
> http://hisblog.tumblr.com and http://herblog.tumblr.com. If process is
> interuppted, you may finish again by simply executing `./getpics.py`

Contributing
------------

Please feel free to contribute.
 
Simply fork this repo, make your changes, and submit a pull request.
If I don't understand your patch, I'll ask for documentation or some
tests. But do feel free to try. Thanks!

