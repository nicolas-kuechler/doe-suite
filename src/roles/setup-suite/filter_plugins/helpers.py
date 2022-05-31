
def git_repo_list(git_remote_repository):

    """
    Ensures that the git repository is a list of the form: [{"repo": <GIT_REMOTE>, "version": <VERSION>}, ...]
    """

    def _extract_dir(i, clone_str):
        if i == 0:
            return "code"
        else:
            # extract the repo name from the repo clone string
            return entry["repo"].rstrip('/').rsplit('/', maxsplit=1)[-1].removesuffix('.git')



    if isinstance(git_remote_repository, list):
        for i, entry in enumerate(git_remote_repository):
            if "repo" not in entry:
                raise ValueError("repo must bed define in git_remote_repository entry (under group_vars/all")
            if "version" not in entry:
                entry["version"] = "HEAD"
            if "dir" not in entry:
                entry["dir"] = _extract_dir(i, entry["repo"])

        return git_remote_repository

    elif isinstance(git_remote_repository, dict):
        if "version" not in git_remote_repository:
            git_remote_repository["version"] = "HEAD"
        if "repo" not in git_remote_repository:
            raise ValueError("repo must bed define in git_remote_repository (under group_vars/all")
        if "dir" not in git_remote_repository:
            git_remote_repository["dir"] = _extract_dir(i, entry["repo"])
        return [{"repo": git_remote_repository["repo"], "version": git_remote_repository["version"], "dir": git_remote_repository["dir"]}]

    elif isinstance(git_remote_repository, str):
        return [{"repo": git_remote_repository, "version": "HEAD", "dir": "code"}]

    else:
        raise ValueError(f"unknown format: {git_remote_repository}")




class FilterModule(object):
    ''' jinja2 filters '''

    def filters(self):
        return {
            'git_repo_list': git_repo_list,
        }