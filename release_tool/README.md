# Release tool

Use script to bump the release verison and create the release PR to merge to develop branch.

**Note: this script only works with python3.**

- If you have generated your github access token, you can use the following command to bump versions and send PR automatically.
    ```bash
    python prepare_release_branch.py -v -n <release_version> -a <your_access_token>
    ```

- If the access token is not given, this script only is only used to bump the release version and push the commit to remote repo. You need to go to github web page to create your PR manually.
    ```
    python prepare_release_branch.py -v -n <release_version>
    ```
