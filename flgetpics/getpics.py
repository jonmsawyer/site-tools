#!/usr/bin/env python

import os
import sys
import httplib
import zlib
import json
import re
import random
import time
import subprocess
import signal
import platform
import urllib2
import tempfile
import shutil

# local lookup
import cookie

host = ''
site_name = ''
pics_dir = 'pics'
users_dir = 'users'
top_uri = '/home/v4'
top_referer = 'https://'+host+top_uri
last_referer = 'https://'+host
headers = {
	'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
	'Accept-Encoding': 'UTF-8',
	'Accept-Language': 'en-US,en;q=0.8',
	'Connection': 'keep-alive',
	'Cookie': cookie.cookie,
	'Host': host,
	'Referer': top_referer,
	'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36',
}
headers_ajax_page = {
    'Accept-Encoding': 'UTF-8',
    'Host': host,
    'Accept-Language': 'en-US,en;q=0.8',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Referer': 'https://'+host,
    'X-Requested-With': 'XMLHttpRequest',
    'Connection': 'keep-alive',
    'Cookie': headers['Cookie']
}

todo_ids = set()
def signal_handler(sig, frame):
    global todo_ids
    print "Writing TODOs to TODO_LIST."
    with open('TODO_LIST') as fh:
       todo_list = fh.read()
    for item in todo_list.split():
        todo_ids.add(item)
    if len(todo_ids) > 0:
        print "\nWriting TODOs to TODO_LIST."
    with open('TODO_LIST', 'w') as fh:
        for todo in todo_ids:
            fh.write("%s\r\n" % (todo,))
    sys.exit(0)

#
# Implement unix-like 'touch'
#
def touch(fname, times=None):
    fhandle = file(fname, 'a')
    try:
        os.utime(fname, times)
    finally:
        fhandle.close()

def is_windows():
    if 'Windows' in platform.system():
        return True
    else:
        return False

__CSL = None
def mklink(source, link_name):
    '''mklink(source, link_name)
       Creates a symbolic link pointing to source named link_name'''
    if is_windows():
        return None
        # figure out how we wanna process symlinks in Windows
        print 'making link in windows'
        global __CSL
        if __CSL is None:
            import ctypes
            csl = ctypes.windll.kernel32.CreateSymbolicLinkW
            csl.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
            csl.restype = ctypes.c_ubyte
            __CSL = csl
        flags = 0
        if source is not None and os.path.isdir(source):
            flags = 1
        if __CSL(link_name, source, flags) == 0:
            raise ctypes.WinError()
    else:
        # Remove current symlink if it exists and create a new one
        # (in case user changes their name and somone else takes their name)
        if os.path.exists(link_name):
            os.unlink(link_name)
        os.symlink(source, link_name)

#
# If the page is compressed with zlib, uncompress it.
#
def inflate(data):
    decompressed_data = zlib.decompress(data, 16+zlib.MAX_WBITS)
    return decompressed_data

#
# Get the main page and the pictures page content.
#
def get(connection, uri):
    global last_referer, headers
    time.sleep(random.random())
    headers['Referer'] = last_referer
    last_referer = uri
    connection.request('GET', uri, '', headers)
    response = connection.getresponse()
    print 'get:', response.status, response.reason, uri
    return response.status, response.reason, response.read()

#
# Get the pictures ajax page.
#
def get_ajax_page(connection, uri):
    global last_referer, headers_ajax_page
    time.sleep(random.random())
    headers_ajax_page['Referer'] = last_referer
    last_referer = uri
    connection.request('GET', uri, '', headers_ajax_page)
    response = connection.getresponse()
    print 'get ajax page:', response.status, response.reason, uri
    return response.status, response.reason, response.read()

#
# Parse the pictures page for the user name of the user and the
# number of pages that are in their pictures.
#
def parse_picture_page(data):
    match = re.search(r'<title>(.+)&(.+)'+site_name+r'</title>', data, re.M|re.I)
    try:
        user_name = match.group(1)
    except:
        user_name = None

    match = re.search(r'data-total-pages=\"([0-9]+)\".*data-total-items=\"([0-9]+)\"', data, re.M)
    try:
        num_pages = int(match.group(1))
        num_pics = int(match.group(2))
    except:
        num_pages = None
        num_pics = None
    return user_name, num_pages, num_pics

#
# Parse this singular picture page data for the final picture URL
#
def parse_picture_page_for_final_url(data):
    match = re.search(r"<style>.*@media.*@media.*@media.*\.fake_img.*background-image: url\('(.+)'\); \}  \}.*</style>", data, re.M|re.S)
    try:
        url = match.group(1)
    except:
        url = None
    return url

def get_remote_file(url, to_dir):
    file_name = url.split('/')[-1]
    u = urllib2.urlopen(url)
    f = open(tempfile.mktemp(), 'wb')
    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    last_modified = meta.getheaders("Last-Modified")[0]
    time_struct = time.strptime(last_modified, '%a, %d %b %Y %H:%M:%S %Z')
    m_time = time.mktime(time_struct)
    
    print "Downloading: %s Bytes: %s" % (file_name, file_size)

    file_size_dl = 0
    block_sz = 8192
    while True:
        buffer = u.read(block_sz)
        if not buffer:
            break

        file_size_dl += len(buffer)
        f.write(buffer)
        status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
        status = status + chr(8)*(len(status)+1)
        print status,

    f.close()
    shutil.move(f.name, os.path.join(to_dir, file_name))
    # set local modified time to that of remote file
    os.utime(os.path.join(to_dir, file_name), (m_time, m_time))

# Catch sigint
signal.signal(signal.SIGINT, signal_handler)

# Set up the path where the pictures are going to live
if not os.path.exists(os.path.join(pics_dir, users_dir)):
    os.makedirs(os.path.join(pics_dir, users_dir))

touch('TODO_LIST')
with open('TODO_LIST') as fh:
    todo_list = fh.read()
todo_ids = set(todo_list.split())

touch('USER_LIST')
with open('USER_LIST') as fh:
    user_list = fh.read()
user_ids = set(user_list.split())

touch('USER_LIST_FAILED')
with open('USER_LIST_FAILED') as fh:
    user_list_failed = fh.read()
user_ids_failed = set(user_list_failed.split())

if len(sys.argv) == 1:
    if len(todo_ids) > 0:
        user_list = str(todo_list)
        user_ids = set(todo_ids)
else:
    user_ids = set()
    count = 0
    for i in sys.argv:
        # don't append the name of the calling script
        if count == 0:
            count = count + 1
            continue
        user_ids.add(i)
        todo_ids.add(i)

print "My %s picture getter!" % (site_name,)
print ""
print "Getting these users: %s" % (user_ids,)
print ""

c = httplib.HTTPSConnection(host)

# Try to connect to the main page
status, reason, data = get(c, top_uri)
if status != 200:
    print 'Could not get main page. Check headers.'
    exit(1)

bad_user_ids = set()
for user in user_ids:
    # Try to get a user's picture dashboard page and add it
    # to the list to be grabbed if it's good and add it
    # to the failed list if it's bad. This optimization
    # is for when you want to store the user information
    # for immediate caching.
    status, reason, data = get(c, '/users/%s' % (user,))
    if status == 200:
        # The user ID entered is valid, enter it into the USER_LIST
        # file if it isn't already there
        if not user in user_list:
            with open('USER_LIST','a') as fh:
                fh.write(user+"\r\n")
    else:
        print 'Could not get pictures page of user %s' % (user,)
        if user not in user_list_failed:
            with open('USER_LIST_FAILED', 'a') as fh:
                fh.write(user+"\r\n")
            bad_user_ids.add(user)
        todo_ids.remove(user)

if len(todo_ids) > 0:
    user_ids = set(todo_ids)

for user in user_ids:
    # Try to get a user's picture dashboard page
    status, reason, data = get(c, '/users/%s/pictures' % (user,))

    user_pic_path = os.path.join(pics_dir, users_dir, user)
    
    # Create the directory structure for the user: pics/users/{{user_id}} 
    if not os.path.exists(user_pic_path):
        os.makedirs(user_pic_path)
    
    if status != 200:
        continue
    
    user_name, num_pages, num_pics = parse_picture_page(data)
    print user_name, num_pages, num_pics
    
    if (user_name == None or num_pages == 0 or num_pics == 0):
        print 'Could not get name, num pages, or num pics of user %s' % (user,)
        break
    
    mklink(os.path.join(users_dir, user), os.path.join(pics_dir, user_name))

    profile_name_file = os.path.join(pics_dir, users_dir, user, '.profile_username.txt')
    with open(profile_name_file, 'w') as fh:
        fh.write(user_name+"\r\n")

    # Grab a list of links to all pics pages for this user profile
    all_pics = []
    for i in xrange(0, num_pages):
        status, reason, data = get_ajax_page(c, '/users/%s/pictures?page=%s' % (user, i+1))
        obj = json.loads(data)
        all_pics.extend(obj)
    
    print 'length of all_pics == num_pics?', len(all_pics) == num_pics
    
    # Get a list of picture pages we've already downloaded
    pic_pages_file = os.path.join(user_pic_path, '.pic_pages.txt')
    touch(pic_pages_file)
    with open(pic_pages_file) as fh:
        pic_pages = fh.read()

    with open(pic_pages_file, 'a') as fh:
        for pic_ob in all_pics:
            pic_page = pic_ob['href'].replace('https://'+host, '')
            if not pic_page in pic_pages:
                status, reason, data = get(c, pic_page)
                url = parse_picture_page_for_final_url(data)
                if url:
                    print "     (%s) Getting %s ..." % (user_name, url)
                    if not os.path.exists(os.path.join(user_pic_path, url.split('/')[-1])):
                        try:
                            get_remote_file(url, user_pic_path)
                            #subprocess.check_output("wget %s -N -P %s/" % (url, user_pic_path), shell=True)
                        except:
                            try:
                                url = url.replace("_958.jpg", "_720.jpg")
                                get_remote_file(url, user_pic_path)
                                #subprocess.check_output("wget %s -N -P %s/" % (url, user_pic_path), shell=True)
                            except:
                                raise
                    with open(os.path.join(user_pic_path, url.split('/')[-1]+'.txt'), 'w') as meta_h:
                        meta_h.write(json.dumps(pic_ob, sort_keys=True, indent=2))
                    fh.write(pic_page+"\r\n")
    try:
        todo_ids.remove(user)
    except KeyError:
        pass

# Remove any failed users out of the USER_LIST
# (as they are already in the bad list)
with open('USER_LIST') as fh:
    current_users = set(fh.read().split())
for user in bad_user_ids:
    try:
        current_users.remove(user)
    except:
        pass
with open('USER_LIST', 'w') as fh:
    for user in current_users:
        fh.write(user+"\r\n")

# finally, write a clean todo list
with open('TODO_LIST', 'w') as fh:
    pass

