flgetpics
=========

This little bundle of code is a picture scraper for a popular website.

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
power of `flgetpics`. But, never fret.

cookie.py
---------

Log into the popular website, grab the cookie from the browser, and
plop the cookie into this file's `cookie` variable.

getpics.py
----------

Open up this file and fill in the `host` and `site_name` variables. If
these are not filled in *just* right, this script will not work. :(

Running the app
---------------

`cd` into the directory where this script lives and execute `./getpics.py`
or do `$ python getpics.py`. Note: this script is designed to be executed
in the directory where `getpics.py` is located. A folder called "pics"
will be made followed by the rest of the pictures scraped from the site.

Usage: `./getpics.py [user_id [user_id ...]]`

user_id - the user id of the profile to scrape

Withough arguments: `./getpics.py` will finish downloading pictures from any
interrupted users. If there are no users in the `TODO_LIST`, then `./getpics.py`
will check and download any *new* pictures from ALL profiles in `USER_LIST`.

Examples:

`$ ./getpics.py`
> Finish everything in `TODO_LIST`. If `TODO_LIST` is empty, fetch everything
> in `USER_LIST`

`$ ./getpics.py 1234 5678 9012`
> Fetch all pictures in these users profiles. If process is interuppted, you may
> finish again by simply executing `./getpics.py`

Contributing
------------

Please feel free to contribute. If you have to ask which site this
scraper works on, then you probably don't need to know. Sorry, I won't
tell you.

Simply fork this repo, make your changes, and submit a change request.
If I don't understand your patch, I'll ask for documentation or some
tests. But do feel free to try. Thanks!

