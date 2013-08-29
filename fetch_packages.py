#!/usr/bin/python
import os
import re
import shutil
import subprocess

_OPT_VERBOSE = None
_OPT_DRY_RUN = None
_PACKAGE_CACHE='/tmp/cache/third_party'

from lxml import objectify

def getFilename(pkg, url):
    element = pkg.find("local-filename")
    if element:
        return str(element)

    (path, filename) = url.rsplit('/', 1)
    m = re.match(r'\w+\?\w+=(.*)', filename)
    if m:
        filename = m.group(1)
    return filename

def getTgzDestination(tgzfile):
    cmd = subprocess.Popen(['tar', 'ztvf', tgzfile], stdout=subprocess.PIPE)
    (output, _) = cmd.communicate()
    (first, _) = output.split('\n', 1)
    fields = first.split()
    return fields[5]

def ApplyPatches(pkg):
    stree = pkg.find('patches')
    if stree is None:
        return
    for patch in stree.getchildren():
        cmd = ['patch']
        if patch.get('strip'):
            cmd.append('-p')
            cmd.append(patch.get('strip'))
        if _OPT_VERBOSE:
            print "Patching %s <%s..." % (' '.join(cmd), str(patch))
        if not _OPT_DRY_RUN:
            fp = open(str(patch), 'r')
            proc = subprocess.Popen(cmd, stdin = fp)
            proc.communicate()

#def VarSubst(cmdstr, filename):
#    return re.sub(r'\${filename}', filename, cmdstr)

def ProcessPackage(pkg):
    print "Processing %s ..." % (pkg['name'])
    url = str(pkg['url'])
    filename = getFilename(pkg, url)
    ccfile = _PACKAGE_CACHE + '/' + filename
    if not os.path.isfile(ccfile):
        subprocess.call(['wget', '-O', ccfile, url])

    #
    # clean directory before unpacking and applying patches
    #
    dest = None
    unpackdir = pkg.find('unpack-directory')
    if unpackdir:
        dest = str(unpackdir)

    if pkg.format == 'tgz':
        dest = getTgzDestination(ccfile)

    if dest and os.path.isdir(dest):
        if _OPT_VERBOSE:
            print "Clean directory %s" % dest
        if not _OPT_DRY_RUN:
            shutil.rmtree(dest)

    if unpackdir:
        try:
            os.makedirs(str(unpackdir))
        except OSError as exc:
            pass
        

    if pkg.format == 'tgz':
        cmd = ['tar', 'zxvf', ccfile]
    elif pkg.format == 'tbz':
        cmd = ['tar', 'jxvf', ccfile]
    elif pkg.format == 'zip':
        cmd = ['unzip', '-o', ccfile]
    else:
        print 'Unexpected format: %s' % (pkg.format)
        return
    if not _OPT_DRY_RUN:
        cd = None
        if unpackdir:
            cd = str(unpackdir)
        p = subprocess.Popen(cmd, cwd = cd)
        p.wait()

    ApplyPatches(pkg)

def main(filename):
    tree = objectify.parse(filename)
    root = tree.getroot()

    for object in root.iterchildren():
        if object.tag == 'package':
            ProcessPackage(object)

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    try:
        os.makedirs(_PACKAGE_CACHE)
    except OSError as exc:
        pass

    main('packages.xml')
