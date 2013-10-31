import os
import subprocess
import sys

GIT_PATH = '/opt/'


def _open_pipe(cmd, cwd=None):
    return subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, cwd=cwd)

def git_path(repo):
    return os.path.join(GIT_PATH, repo)


def git(path, args):
    stdout, stderr = _open_pipe(['git'] + args.split(' '),
                                cwd=path).communicate()
    if stderr:
        print stderr
    return stderr or stdout


def github_url(team, repo, url=None):
    return 'http://github.com/{team}/{repo}{url}'.format(
        team=team, repo=repo, url=url or '')


def pbcopy(data):
    """Copy to clipboard on Mac OS X."""
    print data
    pb = _open_pipe(['pbcopy'])
    pb.stdin.write(data)
    pb.stdin.close()
    return pb.wait()


def usage(args):
    print 'Usage: {program} [command] [tag] [sha]? [repo]?\n'.format(
        program=args[0])
    print 'Commands:'
    print '- append: Cherrypick a [sha] to [tag]'
    print '- create: Create a new [tag]'
    print '- delete: Delete an existing [tag]'
    sys.exit(1)


if __name__ == '__main__':
    args = [x.strip() for x in sys.argv]
    if len(args) < 3:
        usage(args)

    cmd, tag = args[1:3]
    try:
        sha = args[3]
    except IndexError:
        if cmd == 'append':
            usage(args)

    repos = [x.strip() for x in open('repos').readlines()
             if not x.strip().startswith('#')]

    for repo in repos:
        team, repo = repo.split('/')

        if cmd == 'create':
            path = git_path(repo)

            # Fetch the latest tags
            # (where origin is the upstream remote repo).
            git(path, 'fetch --tags')

            # Identify the latest tag.
            tag_prev = git(path,
                'for-each-ref refs/tags --sort=-authordate '
                '--format="%(refname)" --count=1')
            tag_prev = tag_prev.replace('refs/tags/', '').strip('\'"\n')

            # Tag master.
            git(path, 'tag %s' % tag)

            # Point to the releases permalink page.
            print '* Tagged {team}/{repo}: {tag}'.format(
                team=team, repo=repo, tag=tag)
            print github_url(team, repo, '/releases/{tag}'.format(tag=tag))

            # Point to the tag comparison page.
            pbcopy(github_url(team, repo,
                              '/compare/{previous_tag}...{tag}'.format(
                                  previous_tag=tag_prev,
                                  tag=tag
                               )
            ))
            git(path, 'push --tags')
