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

pics_dir = 'pics'
blogs_dir = 'blogs'
top_uri = '/page/1'
top_referer = ''
last_referer = ''
headers = {
	'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
	'Accept-Encoding': 'UTF-8',
	'Accept-Language': 'en-US,en;q=0.8',
	'Connection': 'keep-alive',
	'Host': '',
	'Referer': '',
	'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36',
}
previous_page_pics = []
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
    #time.sleep(random.random())
    headers['Referer'] = last_referer
    headers['Host'] = connection.host
    last_referer = uri
    try:
        connection.request('GET', uri, '', headers)
    except:
        time.sleep(10)
        try:
            connection.request('GET', uri, '', headers)
        except:
            return None, None, None
    response = connection.getresponse()
    print 'get:', response.status, response.reason, connection.host.split('.')[0], uri
    return response.status, response.reason, response.read()

#
# Parse the pictures page for the user name of the user and the
# number of pages that are in their pictures.
#
def parse_tumblr_page(data, user, sub_page=False, deep_page=False):
    pages = set()
    images = set()
    iframes = set()

    image_regexp = r'http://\d+\.media\.tumblr\.com/(?:[a-f0-9]+/)?tumblr_[^.]+\.(?:jpg|png|gif|bmp)'
    matches = re.findall(image_regexp, data, re.I)
    images = images.union(matches)

    #if sub_page: print ' --> ',
    #if deep_page: print ' --> ',
    #print 'Images before:'
    #for i in images:
    #    if sub_page: print ' --> ',
    #    if deep_page: print ' --> ',
    #    print i

    post_a_tags_regexp = r'<a\b[^>]*?href="(http://%s\.tumblr\.com/post/[^"]+)"[^>]*?>(.*?)</a>' % (user,)
    matches = re.findall(post_a_tags_regexp, data, re.I|re.S)
    for post in matches:
       img = re.findall(image_regexp, post[1], re.I)
       if img:
           pages = pages.union([post[0]])
           images = images.difference(img)

    image_a_tags_regexp = r'<a\b[^>]*?href="(http://%s\.tumblr\.com/image/[^"]+)"[^>]*?>(.*?)</a>' % (user,)
    matches = re.findall(image_a_tags_regexp, data, re.I|re.S)
    for image in matches:
       img = re.findall(image_regexp, image[1], re.I)
       if img:
           pages = pages.union([image[0]])
           images = images.difference(img)
       
    #if sub_page: print ' --> ',
    #if deep_page: print ' --> ',
    #print 'Pages to capture:'
    #for i in pages:
    #    if sub_page: print ' --> ',
    #    if deep_page: print ' --> ',
    #    print i

    #if sub_page: print ' --> ',
    #if deep_page: print ' --> ',
    #print 'Images after:'
    #for i in images:
    #    if sub_page: print ' --> ',
    #    if deep_page: print ' --> ',
    #    print i

    iframe_regexp = r'http://%s\.tumblr\.com/post/\d+/photoset_iframe/%s/tumblr_[^"]+' % (user, user)
    matches = re.findall(iframe_regexp, data, re.I)
    iframes = iframes.union(matches)

    #if sub_page: print ' --> ',
    #if deep_page: print ' --> ',
    #print 'Iframes to capture:'
    #for i in iframes:
    #    if sub_page: print ' --> ',
    #    if deep_page: print ' --> ',
    #    print i

    pages = pages.union(iframes)
    return list(pages), list(images)

def get_remote_file(url, to_dir):
    file_name = url.split('/')[-1]
    try:
    	u = urllib2.urlopen(url)
    except Exception, e:
        print "ERROR: Downloading failed for %s. Reason: %s" % (file_name, str(e))
        return
    
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

# Set up the path where the blogs are going to live
if not os.path.exists(blogs_dir):
    os.makedirs(blogs_dir)

# Set up the path where the blogs are going to live
if not os.path.exists(pics_dir):
    os.makedirs(pics_dir)

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
        if i.endswith('\r'):
            i = i[:-2]
        user_ids.add(i)
        todo_ids.add(i)

print "My Tumblr picture getter!"
print ""
print "Getting these users: %s" % (user_ids,)
print ""



bad_user_ids = set()
for user in user_ids:
    c = httplib.HTTPConnection("%s.tumblr.com" % (user,))
    
    # Try to get a user's picture dashboard page and add it
    # to the list to be grabbed if it's good and add it
    # to the failed list if it's bad. This optimization
    # is for when you want to store the user information
    # for immediate caching.
    status, reason, data = get(c, '/')
    if status == 200:
        # The user ID entered is valid, enter it into the USER_LIST
        # file if it isn't already there
        if not user in user_list:
            with open('USER_LIST','a') as fh:
                fh.write(user+"\r\n")
    else:
        print 'Could not get blog of user %s' % (user,)
        if user not in user_list_failed:
            with open('USER_LIST_FAILED', 'a') as fh:
                fh.write(user+"\r\n")
            bad_user_ids.add(user)
        try:
            todo_ids.remove(user)
        except:
            pass

    c.close()

if len(todo_ids) > 0:
    user_ids = set(todo_ids)

for user in user_ids:
    c = httplib.HTTPConnection("%s.tumblr.com" % (user,))
    user_pic_path = os.path.join(blogs_dir, user)
    all_pics_path = pics_dir
    
    # Create the directory structure for the user: blogs/{{user_id}} 
    if not os.path.exists(user_pic_path):
        os.makedirs(user_pic_path)

    errors_in_row = 0
    current_page = 1
    while current_page > 0:
        # Try to get a user's page
        if current_page == 1:
            status, reason, data = get(c, '/')
        else:
            status, reason, data = get(c, '/page/%s' % (current_page,))

        if status == None and reason == None and data == None:
            if errors_in_row >= 1:
                break
            else:
                errors_in_row += 1
            current_page += 1
            continue

        if status != 200:
            break
        else:
            errors_in_row = 0

        pages, all_pics = parse_tumblr_page(data, user)
        if pages == [] and all_pics == []:
           current_page = -1 # we're done
           continue

        every_page = list(pages)

        pic_pages_file = os.path.join(user_pic_path, '.pic_pages.txt')
        touch(pic_pages_file)
        with open(pic_pages_file) as fh:
            pic_pages_buf = fh.read().split()
        
        # Parse sub pages (level 2)
        for page in pages:
            pic_url = '/'+'/'.join(page.split('/')[3:])
            if pic_url in pic_pages_buf:
                print "("+user+") Not checking", pic_url, "..."
                continue
            else:
                page_status, page_reason, page_data = get(c, page.replace('http://%s.tumblr.com' % (user,), ''))
            if page_status != 200:
               continue
            page_pages, page_all_pics = parse_tumblr_page(page_data, user, sub_page=True)
            all_pics.extend(page_all_pics)
            every_page.extend(page_pages)

            # Parse sub pages of sub pages (level 3) [this is far as we'll go]
            for deep_page in page_pages:
                deep_status, deep_reason, deep_data = get(c, deep_page.replace('http://%s.tumblr.com' % (user,), ''))
                if deep_status != 200:
                    continue
                deep_pages, deep_all_pics = parse_tumblr_page(deep_data, user, sub_page=True, deep_page=True)
                all_pics.extend(deep_all_pics)
                every_page.extend(deep_pages)
                if deep_pages != []:
                    print 'WARNING: expected empty page set, instead got %s pages!' % (len(deep_pages),)

        #for page in every_page:
        #    print '/'+'/'.join(page.split('/')[3:])
        for pic in all_pics:
            print pic
        #exit()
        
        # Grab the largest pic in the set
        old_all_pics = list(set(all_pics))
        old_all_pics.sort(key=lambda s: s.split('_',1)[1])
        all_pics = []
        key = ''
        size = 0
        for pic in old_all_pics:
            p = pic.split('_')
            if len(p) == 4:
                p[1] = "_".join([p[1], p[2]])
                p.remove(p[2])
            if key != p[1]:
                all_pics.append(pic)
                key = p[1]
                try:
                    size = int(p[2].split('.')[0])
                except ValueError as e:
                    continue
            else:
                p_size = int(p[2].split('.')[0])
                if size >= p_size:
                    continue
                else:
                    size = p_size
                    for i in all_pics:
                        if p[1] in i:
                            all_pics.remove(i)
                            all_pics.append(pic)
                            break
        print '(%s)' % (user,), 'Getting', len(all_pics), 'pics for page', current_page
        #if all_pics == previous_page_pics:
        if every_page == previous_page_pics:
            current_page = -1
            continue
        else:
            #previous_page_pics = list(all_pics)
            previous_page_pics = list(every_page)
            current_page = current_page + 1
        
        #mklink(os.path.join(blogs_dir, user), os.path.join(pics_dir, user_name))

        #profile_name_file = os.path.join(pics_dir, blogs_dir, user, '.profile_username.txt')
        #with open(profile_name_file, 'w') as fh:
        #    fh.write(user_name+"\r\n")

        # Grab a list of links to all pics pages for this user profile
        #all_pics = []
        #for i in xrange(0, num_pages):
        #    status, reason, data = get_ajax_page(c, '/users/%s/pictures?page=%s' % (user, i+1))
        #    obj = json.loads(data)
        #    all_pics.extend(obj)
        
        #print 'length of all_pics == num_pics?', len(all_pics) == num_pics
        
        # Get a list of picture pages we've already downloaded
        pic_pages_file = os.path.join(user_pic_path, '.pic_pages.txt')
        touch(pic_pages_file)
        with open(pic_pages_file) as fh:
            pic_pages = fh.read()

        with open(pic_pages_file, 'a') as fh:
            for url in all_pics:
                if not url.split('/', 3)[3] in pic_pages:
                    print "     (%s) Getting %s ..." % (user, url)
                    picname = url.split('/')[-1]
                    if not os.path.exists(os.path.join(all_pics_path, picname)):
                        try:
                            get_remote_file(url, all_pics_path)
                            #subprocess.check_output("wget %s -N -P %s/" % (url, user_pic_path), shell=True)
                        except:
                            raise
                            #try:
                            #    url = url.replace("_958.jpg", "_720.jpg")
                            #    get_remote_file(url, user_pic_path)
                            #    #subprocess.check_output("wget %s -N -P %s/" % (url, user_pic_path), shell=True)
                            #except:
                            #    raise
                    if not os.path.exists(os.path.join(user_pic_path, picname)):
                        mklink(
                            os.path.join('..', '..', all_pics_path, picname),
                            os.path.join(user_pic_path, picname)
                        )
                        
                    #with open(os.path.join(user_pic_path, url.split('/')[-1]+'.txt'), 'w') as meta_h:
                    #    meta_h.write(json.dumps(pic_ob, sort_keys=True, indent=2))
                    fh.write(url.split('/', 3)[3]+"\r\n")
        with open(pic_pages_file, 'a') as fh:
            for page in every_page:
                fh.write('/'+'/'.join(page.split('/')[3:])+"\r\n")
    try:
        todo_ids.remove(user)
        with open('TODO_LIST', 'w') as fh:
            fh.write("\r\n".join(todo_ids)+"\r\n")
    except KeyError:
        pass
    #exit(0)

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

