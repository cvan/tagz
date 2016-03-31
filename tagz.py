#!/usr/bin/env python
"""
This is a script to automatically tag repos on GitHub.

Sample usage:

* To create a tag:

    $ python tagz.py -r mozilla/fireplace -c create -t 2014.02.11

NOTE: annotated tags are used by default (-a). If you want lightweight tags,
      you can pass -l:

    $ python tagz.py -l -r mozilla/fireplace -c create -t 2014.02.11

ALSO: this script will use whatever type of tag the first found refname is.
      You cannot use this script to mix use of the two in the same repo.

* To create multiple tags:

    $ python tagz.py -r mozilla/zamboni,mozilla/fireplace -c create -t 2014.02.11

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


def git(path, args, limit=None):
    if DRYRUN:
        print 'cd %s; git %s' % (path, args)
        return ''
    if limit:
        stdout, stderr = _open_pipe(['git'] + args.split(' ', limit),
                                    cwd=path).communicate()
    else:
        stdout, stderr = _open_pipe(['git'] + args.split(' '),
                                    cwd=path).communicate()
    if VERBOSE and stderr:
        print stderr
    return stderr or stdout


def git_create_tag(path, tag, annotated):
    # Create new tag. Assumes tag has no spaces.
    if annotated:
        git(path, 'tag -a %s -m tag for %s' % (tag, tag), 4)
    else:
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


def resolve_annotate(path, use_annotate):
    """Be internally consistent with tag type."""

    retval = use_annotate
    first_tag = (git(path, 'for-each-ref refs/tags --sort=refname --count=1 '
                     '--format="%(taggerdate:raw)|%(refname:strip=2)"')
                 .strip(' \n')
                 .replace('"', '')
                 .split('|'))
    if len(first_tag) > 1:
        if ((use_annotate and first_tag[0] == '') or
            (not use_annotate and first_tag[0] != '')):
            retval = not use_annotate
    return retval


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
    p.add_argument('-v', '--verbose', dest='verbose', action='store',
        help='make lots of noise', default=VERBOSE)
    p.add_argument('-n', '--dry-run', dest='dryrun', action='store',
        help="Show git actions to perform but don't do them", default=DRYRUN)
    group = p.add_mutually_exclusive_group(required=False)
    group.add_argument('-a', '--annotate', dest='useannotate',
        action='store_true')
    group.add_argument('-l', '--lightweight', dest='useannotate',
        action='store_false')
    p.set_defaults(useannotate=True)
    args = p.parse_args()

    cmd, repo, sha, tag = (args.cmd, args.repo, args.sha, args.tag)
    VERBOSE, DRYRUN, use_annotated = (args.verbose, args.dryrun,
                                      args.useannotate)

    if tag == 'YYYY.MM.DD':
        p.error('tag should be the date of push, not: %s' % tag)

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

        set_annotate = resolve_annotate(path, use_annotated)
        if set_annotate != use_annotated:
            if set_annotate:
                print 'Convention is to use annotated tags. Conforming...'
            else:
                print 'Convention is to use lightweight tags. Conforming...'

        if cmd == 'create':
            git_create_tag(path, tag, set_annotate)

        elif cmd == 'cherrypick':
            # Check out existing tag.
            git(path, 'checkout %s' % tag)

            git_delete_tag(path, tag)

            # Cherry-pick commit.
            git(path, 'cherry-pick %s' % sha)

            git_create_tag(path, tag, set_annotate)

        elif cmd == 'delete':
            git_delete_tag(path, tag)

        elif cmd == 'revert':
            # Check out existing tag.
            git(path, 'checkout %s' % tag)

            git_delete_tag(path, tag)

            # Revert commit.
            git(path, 'revert %s' % sha)

            git_create_tag(path, tag, set_annotate)

        # Identify the latest two tags.
        # This will only work if a repo:
        #   a) contains strictly lightweight OR annotated tags
        #   b) has a defined tag syntax, e.g. /YYYY\.MM\.DD(-\d)?/
        #   c) only tags in linear sequence
        # Because lightweight tags point to commits and annotated
        # tags are explicit objects, you can't rely on dereferencing
        # fields between the two for comparisons.
        # Meaning, something like this:
        #   git for-each-ref --format='%(*committerdate:raw)%(committerdate:raw) %(refname) \
        #    %(*objectname) %(objectname)' refs/tags | sort -n -r | awk '{ print $3; }' | head -2
        # won't work because the %(committerdate) field is unreliable
        # as a timeline sequence between lightweight and annotated tags.
        # Which is why "latest" tags assume that tags are not
        # applied to points in a branch prior to another tag.

        # Be internally consistent:
        formatstring = 'for-each-ref refs/tags --format="%(refname:strip=2)" --count=2 '
        if set_annotate:
            formatstring += '--sort=-refname --sort=-*committerdate'
        else:
            formatstring += '--sort=-refname --sort=-committerdate'

        prev_tags = (git(path, formatstring)
                     .strip(' \n')
                     .replace('"', '')
                     .replace("'", '')
                     .split('\n'))

        if not DRYRUN:
            if len(prev_tags) == 1:
                prev_tags.append('master')

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
