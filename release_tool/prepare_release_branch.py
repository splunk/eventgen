import argparse
import json
import logging
import os
import re
import subprocess
import sys

import requests

logging.getLogger().setLevel(logging.INFO)
root_repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_args():
    def validate_version_str(version):
        v_str = str(version).strip()
        if not v_str:
            raise argparse.ArgumentTypeError("verison str can not be emtpy.")
        err_message = 'version string should be of format "major.minor.hotfix"'
        numbers = v_str.split(".")
        if len(numbers) != 3:
            raise argparse.ArgumentTypeError(err_message)
        for n in numbers:
            valid = False
            try:
                v = int(n)
                valid = v >= 0
            except:
                valid = False
            if not valid:
                raise argparse.ArgumentTypeError(err_message)
        return v_str

    def validate_token(token):
        t = token.strip()
        if not t:
            raise argparse.ArgumentTypeError("token can not be empty")
        return t

    parser = argparse.ArgumentParser(
        "prepare_release_branch.py",
        description="eventgen release branch tool.\n"
        "create the release branch, set the right version and push the pull request.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        default=False,
        action="store_true",
        help="enable the verbose logging",
    )
    parser.add_argument("-n", "--version_str", type=validate_version_str, required=True)
    parser.add_argument(
        "-a",
        "--token",
        help="your github access token.",
        default=None,
        type=validate_token,
    )
    return parser.parse_args(sys.argv[1:])


def setup_logging(verbose=None):
    log_level = logging.DEBUG if verbose is True else logging.INFO
    logging.getLogger().setLevel(log_level)


def setup_env():
    """
    by default, we use this hard code current working dir.
    because curent working dir has impact about the child sh process.
    we need to setup it before launching any process.
    if there is concrete requirement about setting the current
    working dir, we can change it to cmd arguemnt.
    """
    logging.debug(f"try to change current working directory to {root_repo_dir}")
    os.chdir(root_repo_dir)


def run_sh_cmd(args, exit_on_error=None):
    should_exit_on_error = True if exit_on_error is None else exit_on_error
    child = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = child.communicate()
    outs = out.decode("utf-8")
    errs = err.decode("utf-8")
    if child.returncode == 0:
        logging.debug(f"execute sh command {args} success.")
        logging.debug(f"children output:\n{outs}")
        return True
    logging.error(f"execute sh cmd {args} fail.\nchildren output:\n{outs}\n{errs}")
    if should_exit_on_error:
        assert False, "sh command fails."
    return False


def get_release_branch_name(version_str):
    v = version_str.replace(".", "_")
    return f"release/{v}"


def replace_version(ver):
    ver_json_file = os.path.join(root_repo_dir, "splunk_eventgen", "version.json")
    with open(ver_json_file, "w") as fp:
        json.dump({"version": ver}, fp)
    app_conf = os.path.join(
        root_repo_dir, "splunk_eventgen", "splunk_app", "default", "app.conf"
    )
    app_conf_content = []
    with open(app_conf, "r") as fp:
        app_conf_content = fp.readlines()
    app_pattern = re.compile(r"version\s*=")
    with open(app_conf, "w") as fp:
        for line in app_conf_content:
            lstr = line.strip()
            if app_pattern.search(lstr):
                fp.write(f"version = {ver}\n")
            else:
                fp.write(f"{lstr}\n")
    logging.info(f"verison is replaced with {ver}.")


def update_changelog(ver):
    changelog_file = os.path.join(root_repo_dir, "docs", "CHANGELOG.md")
    with open(changelog_file, "r") as fp:
        content = fp.readlines()
    new_content = (
        f"**{ver}**:\n\n"
        + f"- Check the release note and download the package/source from "
        f"[Here](https://github.com/splunk/eventgen/releases/tag/{ver})\n\n"
    )
    with open(changelog_file, "w") as fp:
        fp.write(new_content)
        for l in content:
            fp.write(l)
    logging.info("CHANGELOG.md is updated.")


def commit_updated_files(ver):
    ver_json_file = os.path.join("splunk_eventgen", "version.json")
    app_conf = os.path.join("splunk_eventgen", "splunk_app", "default", "app.conf")
    changelog = os.path.join("docs", "CHANGELOG.md")
    run_sh_cmd(["git", "add", ver_json_file])
    run_sh_cmd(["git", "add", app_conf])
    run_sh_cmd(["git", "add", changelog])
    run_sh_cmd(["git", "commit", "-m", f"update eventgen version to {ver}"], False)
    logging.info("committed version files.")


def create_pr(ver, token, target_branch):
    release_branch = get_release_branch_name(ver)
    response = requests.post(
        "https://api.github.com/repos/splunk/eventgen/pulls",
        json={
            "title": f"Release eventgen {ver}. Merge to {target_branch} branch.",
            "head": release_branch,
            "base": target_branch,
            "body": "As the title",
        },
        headers={
            "Accept": "application/vnd.github.full+json",
            "Content-Type": "application/json",
            "Authorization": f"token {token}",
        },
    )
    response.raise_for_status()
    data = response.json()
    pr_url = data["url"]
    logging.info(f"Pull request is created:\n\t{pr_url}")


if __name__ == "__main__":
    arg_values = parse_args()
    if arg_values is None:
        sys.exit(1)
    setup_logging(arg_values.verbose)
    setup_env()

    logging.info("checkout to the develop branch and pull the latest change...")
    run_sh_cmd(["git", "checkout", "develop"])
    run_sh_cmd(["git", "pull"])

    logging.info("check out the release branch")
    release_branch = get_release_branch_name(arg_values.version_str)
    branch_exist = run_sh_cmd(
        ["git", "show-ref", "--verify", f"refs/heads/{release_branch}"], False
    )
    if not branch_exist:
        run_sh_cmd(["git", "checkout", "-b", release_branch])
    else:
        run_sh_cmd(["git", "checkout", release_branch])

    replace_version(arg_values.version_str)
    update_changelog(arg_values.version_str)

    commit_updated_files(arg_values.version_str)

    run_sh_cmd(["git", "push", "origin", release_branch])
    logging.info(f"release branch {release_branch} is pushed to remote repo.")

    if arg_values.token:
        create_pr(arg_values.version_str, arg_values.token, "develop")
        create_pr(arg_values.version_str, arg_values.token, "master")
    else:
        pr_url = "https://github.com/splunk/eventgen/compare"
        logging.info("create pull reqeust manually by visiting this url:\n{pr_url}")
