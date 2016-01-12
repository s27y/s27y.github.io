from fabric.api import *
import fabric.contrib.project as project
import os
import shutil
import sys
import SocketServer
import re
import datetime
from pelican.server import ComplexHTTPRequestHandler

# Local path configuration (can be absolute or relative to fabfile)
env.deploy_path = 'output'
DEPLOY_PATH = env.deploy_path

# Remote server configuration
production = 'root@localhost:22'
dest_path = '/var/www'

# Rackspace Cloud Files configuration settings
env.cloudfiles_username = 'my_rackspace_username'
env.cloudfiles_api_key = 'my_rackspace_api_key'
env.cloudfiles_container = 'my_cloudfiles_container'

# Github Pages configuration
env.github_pages_branch = "gh-pages"

# Port for `serve`
PORT = 8000

TEMPLATE = """
Title: {title}
Date: {year}-{month}-{day} {hour}:{minute}
Modified: {year}-{month}-{day} {hour}:{minute}
Category: 
Tags:
Slug: {slug}
Authors: Yang Sun
Summary:
Status: draft

Hello World!
"""

def clean():
    """Remove generated files"""
    if os.path.isdir(DEPLOY_PATH):
        shutil.rmtree(DEPLOY_PATH)
        os.makedirs(DEPLOY_PATH)

def build():
    """Build local version of site"""
    local('pelican -s pelicanconf.py')

def rebuild():
    """`clean` then `build`"""
    clean()
    build()

def regenerate():
    """Automatically regenerate site upon file modification"""
    local('pelican -r -s pelicanconf.py')

def serve():
    """Serve site at http://localhost:8000/"""
    os.chdir(env.deploy_path)

    class AddressReuseTCPServer(SocketServer.TCPServer):
        allow_reuse_address = True

    server = AddressReuseTCPServer(('', PORT), ComplexHTTPRequestHandler)

    sys.stderr.write('Serving on port {0} ...\n'.format(PORT))
    server.serve_forever()

def reserve():
    """`build`, then `serve`"""
    build()
    serve()

def preview():
    """Build production version of site"""
    local('pelican -s publishconf.py')

def cf_upload():
    """Publish to Rackspace Cloud Files"""
    rebuild()
    with lcd(DEPLOY_PATH):
        local('swift -v -A https://auth.api.rackspacecloud.com/v1.0 '
              '-U {cloudfiles_username} '
              '-K {cloudfiles_api_key} '
              'upload -c {cloudfiles_container} .'.format(**env))

@hosts(production)
def publish():
    """Publish to production via rsync"""
    local('pelican -s publishconf.py')
    project.rsync_project(
        remote_dir=dest_path,
        exclude=".DS_Store",
        local_dir=DEPLOY_PATH.rstrip('/') + '/',
        delete=True,
        extra_opts='-c',
    )

def gh_pages():
    """Publish to GitHub Pages"""
    rebuild()
    local("ghp-import -b {github_pages_branch} {deploy_path}".format(**env))
    local("git push origin {github_pages_branch}".format(**env))

def make_entry(title, slug=None, overwrite="no"):
    if slug is None:
        slug = slugify(title)

    now = datetime.datetime.now()
    month_part = now.strftime("%Y-%m")
    post_date = now.strftime("%Y-%m-%d")
    f_create = "content/posts/{}/{}.md".format(month_part, slug)
    t = TEMPLATE.strip().format(title=title,
                                hashes='#' * len(title),
                                year=now.year,
                                month=now.month,
                                day=now.day,
                                hour=now.hour,
                                minute=now.minute,
                                slug=slug)
    if not os.path.exists(f_create) or overwrite.lower() == "yes":
        with open(f_create, 'w') as w:
            w.write(t)
        print("File created -> " + f_create)
    else:
        print("{} already exists. Pass 'overwrite=yes' to destroy it.".
            format(out_file))


def slugify(text):
    normalized = "".join([c.lower() if c.isalnum() else "-"
            for c in text])
    no_repetitions = re.sub(r"--+", "-", normalized)
    clean_start = re.sub(r"^-+", "", no_repetitions)
    clean_end = re.sub(r"-+$", "", clean_start)
    return clean_end
