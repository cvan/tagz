#!/usr/bin/env python
"""
This is a script to automatically tag repos on GitHub.

Sample usage:

* To create a tag:

    $ python tagz.py -r mozilla/fireplace -c create -t 2014.02.11

* To create multiple tags:

    $ python tagz.py -r mozilla/fireplace,mozilla/zamboni -c create -t 2014.02.11

* To delete a tag:

    $ python tagz.py -r mozilla/fireplace -c delete -t 2014.02.11

* To cherry-pick a commit onto a tag:

    $ python tagz.py -r mozilla/fireplace -c cherrypick -t 2014.02.11 -s b4dc0ffee

* To remove a commit from a tag:

    $ python tagz.py -r mozilla/fireplace -c revert -t 2014.02.11 -s b4dc0ffee

"""

import datetime
import os
import platform
import subprocess

import argparse


GIT_ROOT_PATH = '/tmp/'
VERBOSE = False
DRYRUN = False


def _open_pipe(cmd, cwd=None):
    return subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, cwd=cwd)


def get_team_repo(remote_url):
    """
    Takes remote URL (e.g., `git@github.com:mozilla/fireplace.git`) and
    returns team/repo pair (e.g., `mozilla/fireplace`).

    """
    if ':' not in remote_url:
        return remote_url
    return remote_url.split(':')[1].replace('.git', '')


def get_remote_url(remote_url):
    """
    Takes a GitHub remote URL (e.g., `mozilla/fireplace`) and
    returns full remote URL (e.g., `git@github.com:mozilla/fireplace.git`).

    """
    if ':' not in remote_url:
        remote_url = 'git@github.com:' + remote_url
    if not remote_url.endswith('.git'):
        remote_url += '.git'
    return remote_url


def get_git_path(remote_url):
    repo = ''.join(x for x in get_team_repo(remote_url)
                   if x.isalnum() or x == '/')
    dir_name = os.path.join(GIT_ROOT_PATH, repo.replace('/', '__'))
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
        git(dir_name,
            'clone {remote_url} {dir_name}'.format(remote_url=remote_url,
                                                   dir_name=dir_name))
    return dir_name


def get_github_url(team, repo, url=''):
    return 'https://github.com/{team}/{repo}{url}'.format(
        team=team, repo=repo, url=url)


def git(path, args):
    if DRYRUN:
        print 'cd %s; git %s' % (path, args)
        return ''
    stdout, stderr = _open_pipe(['git'] + args.split(' '),
                                cwd=path).communicate()
    if VERBOSE and stderr:
        print stderr
    return stderr or stdout


def git_create_tag(path, tag):
    # Create new tag.
    git(path, 'tag %s' % tag)

    # Push tag.
    git(path, 'push --tags')


def git_delete_tag(path, tag):
    # Delete tag.
    git(path, 'tag -d %s' % tag)

    # Delete remote tag.
    git(path, 'push origin :%s' % tag)


def pbcopy(data):
    """Copy to clipboard on Mac OS X/Linux."""

    mac, linux = False, False
    if os.name == 'mac' or platform.system() == 'Darwin':
        mac = True
    elif os.name == 'posix' or platform.system() == 'Linux':
        linux = True
    else:
        return

    if mac:
        pb = _open_pipe(['pbcopy'])
    elif linux:
        pb = _open_pipe(['xsel', '--clipboard', '--input'])

    pb.stdin.write(data)
    pb.stdin.close()
    return pb.wait()


def main():
    global VERBOSE, DRYRUN

    p = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('-c', '--command', dest='cmd', action='store',
        choices=['cherrypick', 'create', 'delete', 'revert'],
        help='command to run')
    p.add_argument('-r', '--repo', dest='repo', action='store', default='',
        help='remote repository URL (e.g., '
             '`git@github.com:mozilla/fireplace.git` or '
             '`mozilla/fireplace`)', required=True)
    p.add_argument('-s', '--sha', dest='sha', action='store',
        help='sha1 hash of git commit')
    p.add_argument('-t', '--tag', dest='tag', action='store',
        help='name of git tag', required=True)
    p.add_argument('-v', '--verbose', dest='verbose', action='store_true',
        help='make lots of noise', default=False)
    p.add_argument('-n', '--dry-run', dest='dryrun', action='store_true',
        help="Show git actions to perform but don't do them", default=False)
    args = p.parse_args()

    cmd, repo, sha, tag, VERBOSE, DRYRUN = (args.cmd, args.repo, args.sha,
                                            args.tag, args.verbose,
                                            args.dryrun)

    try:
        tagdate = datetime.datetime.strptime(tag, '%Y.%m.%d')
        if tagdate.weekday() == 4:
            p.error('%s is a Friday. Did you really mean %s?'
                    % (tag, (tagdate + datetime.timedelta(days=4)
                   ).strftime('%Y.%m.%d')))
    except ValueError:
        # Not parseable as a date, no big deal.
        pass

    if cmd in ('cherrypick', 'revert') and not sha:
        p.error(
            'argument -s/--sha is required is when cherry-picking a commit')

    repos = [get_remote_url(x.strip()) for x in repo.split(',')]
    urls = []

    for remote_url in repos:
        path = get_git_path(remote_url)
        team, repo = get_team_repo(remote_url).split('/')

        # Check out master.
        git(path, 'checkout master')

        # Fetch the latest tags and code.
        git(path, 'fetch --tags')
        git(path, 'pull --rebase')

        if cmd == 'create':
            git_create_tag(path, tag)

        elif cmd == 'cherrypick':
            # Check out existing tag.
            git(path, 'checkout %s' % tag)

            git_delete_tag(path, tag)

            # Cherry-pick commit.
            git(path, 'cherry-pick %s' % sha)

            git_create_tag(path, tag)

        elif cmd == 'delete':
            git_delete_tag(path, tag)

        elif cmd == 'revert':
            # Check out existing tag.
            git(path, 'checkout %s' % tag)

            git_delete_tag(path, tag)

            # Revert commit.
            git(path, 'revert %s' % sha)

            git_create_tag(path, tag)

        # Identify the latest two tags.
        prev_tags = (git(path,
                         'for-each-ref refs/tags --sort=-committerdate '
                         '--format="%(refname)" --count=2')
                     .replace('refs/tags/', '')
                     .strip(' \n')
                     .replace('"', '')
                     .replace("'", '')
                     .split('\n'))
        if not DRYRUN:
            # Get the URL of the tag comparison page.
            urls.append(get_github_url(
                team, repo, '/compare/{previous_tag}...{latest_tag}'.format(
                    previous_tag=prev_tags[1],
                    latest_tag=prev_tags[0]
                )
            ))

    if urls:
        urls = '\n'.join(urls)
        print urls
        pbcopy(urls)


if __name__ == '__main__':
    main()
