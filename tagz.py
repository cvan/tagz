import os
import subprocess
import sys


GIT_ROOT_PATH = '/tmp/'


def _open_pipe(cmd, cwd=None):
    return subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, cwd=cwd)


def get_team_repo(remote_url):
    """
    Takes remote URL (e.g., `git@github.com:mozilla/fireplace.git`)
    and returns team/repo pair (e.g., `mozilla/rocketfuel`)

    """
    if ':' not in remote_url:
        return remote_url
    return remote_url.split(':')[1].replace('.git', '')


def git_path(remote_url):
    repo = get_team_repo(remote_url).replace('/', '___')
    dir_name = os.path.join(GIT_ROOT_PATH, repo)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
        git(dir_name,
            'clone {remote_url} {dir_name}'.format(remote_url=remote_url,
                                                   dir_name=dir_name))
    return dir_name


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
    sha = None
    try:
        sha = args[3]
    except IndexError:
        if cmd == 'append':
            usage(args)

    repos = [x.strip() for x in open('repos').readlines()
             if not x.strip().startswith('#')]

    urls = []

    for remote_url in repos:
        path = git_path(remote_url)

        team, repo = get_team_repo(remote_url).split('/')

        if cmd == 'create':
            # Fetch the latest tags
            # (where origin is the upstream remote repo).
            git(path, 'fetch --tags')
            git(path, 'pull')

            # Identify the latest tag.
            tag_prev = git(path, 'for-each-ref refs/tags --sort=-authordate '
                           '--format="%(refname)" --count=1')
            tag_prev = tag_prev.replace('refs/tags/', '').strip('\'"\n')

            # Tag master.
            git(path, 'tag %s' % tag)

            # Point to the releases permalink page.
            #print '* Tagged {team}/{repo}: {tag}'.format(
            #    team=team, repo=repo, tag=tag)
            #print github_url(team, repo, '/releases/{tag}'.format(tag=tag))

            # Point to the tag comparison page.
            url = github_url(
                team, repo, '/compare/{previous_tag}...{tag}'.format(
                    previous_tag=tag_prev, tag=tag
                )
            )
            print url
            urls.append(url)

            # Push tag.
            git(path, 'push --tags')

        elif cmd == 'cherrypick':
            # Fetch the latest tags and code.
            git(path, 'fetch --tags')
            git(path, 'pull')

            # Checkout existing tag.
            git(path, 'checkout %s' % tag)

            # Delete existing tag.
            git(path, 'tag -d %s' % tag)

            # Delete existing remote tag.
            git(path, 'push origin :%s' % tag)

            # Cherrypick commit.
            git(path, 'cherry-pick %s' % sha)

            # Create new tag.
            git(path, 'tag %s' % tag)

            # Push new tag.
            git(path, 'push --tags')

            # Identify the latest tag.
            tag_prev = git(path, 'for-each-ref refs/tags --sort=-authordate '
                           '--format="%(refname)" --count=1')
            tag_prev = tag_prev.replace('refs/tags/', '').strip('\'"\n')

            # Point to the tag comparison page.
            url = github_url(
                team, repo, '/compare/{previous_tag}...{tag}'.format(
                    previous_tag=tag_prev, tag=tag
                )
            )
            print url
            urls.append(url)

        elif cmd == 'delete':
            # Fetch the latest tags and code.
            git(path, 'fetch --tags')
            git(path, 'pull')

            # Delete tag.
            git(path, 'tag -d %s' % tag)

            # Delete remote tag.
            git(path, 'push origin :%s' % tag)

    if urls:
        pbcopy('\n'.join(urls))
