# Contribute Code To Eventgen

If you want to contribute code to eventgen, please read over the following guidelines before creating any pull request.


## Pull request guidelines

If you want to contribute to an eventgen repo, please use a GitHub pull request. This is the fastest way for us to evaluate your code and to merge it into the code base. Please don’t file an issue with snippets of code. Doing so means that we need to manually merge the changes in and update any appropriate tests. That decreases the likelihood that your code is going to get included in a timely manner. Please use pull requests.


## Release versioning guidelines

Major Release — Increment the first digit by 1 if the new features break backwards compatibility/current features

Minor Release — Increment the middle digit by 1 if the new features don’t break any existing features and are compatible with the app in it’s current state

Patch Release — Increment the last digit by 1 if you’re publishing bug/patch fixes to your app

### Get started

If you’d like to work on a pull request and you’ve never submitted code before, follow these steps:
1. fork eventgen to your github workspace
2. If you want to fix bugs or make enhancement, please make sure there is a issue in eventgen project. Refer [this guide](FILE_ISSUES.md) to create a issue.

After that, you’re ready to start working on code.


### Working on the code

The process of submitting a pull request is fairly straightforward and generally follows the same pattern each time:
1. Create a new branch
2. Make your changes and check into local branch
3. Rebase onto upstream
4. Run the test
5. Push your change
6. Submit the pull request

#### Step1: Create a new branch

The first step to sending a pull request is to create a new branch in your eventgen fork. Give the branch a descriptive name that describes what it is you’re fixing. Although the branch name can be any words, we highly recommend you to use some descriptive and structured name. It will be good for you to manage the branches when there are many branches in your fork.
```bash
# The branch name contains 2 parts. First part works like a label, it describe what type of issue this branch is working on. Second part is the issue id.
# For example, if the code change is a bug fix
$ git checkout -b bug/issue123
# For example, if the code change is to address change request
$ git checkout -b change/issue123
# For example, if the code change is only about refine the build process, such as making changes about CICD process
$ git checkout -b build/issue123
# For example, if the code change is only about refining the test cases or paying for tech debt
$ git checkout -b chore/issue123
```

#### Step2: Make your changes and check into local branch

Once you finished your change, commit them into your local branch.
```bash
$ git add -A
$ git commit 
```

Our commit message format is as follows:
```
Tag: Short description (fixes #1234)
// empty line
Longer description here if necessary
```

The first line of the commit message (the summary) must have a specific format. This format is checked by our build tools.

The <span style="color:blue;background-color:#d4d4f7">**Tag**</span> is one of the following:

* <span style="color:blue;background-color:#d4d4f7">**Fix**</span> - for a bug fix.
* <span style="color:blue;background-color:#d4d4f7">**Update**</span> - update or enhance an existing feature.
* <span style="color:blue;background-color:#d4d4f7">**New**</span> - implemented a new feature.
* <span style="color:blue;background-color:#d4d4f7">**Docs**</span> - changes to documentation only.
* <span style="color:blue;background-color:#d4d4f7">**Build**</span> - changes to build process only, updating the dependency libs etc.
* <span style="color:blue;background-color:#d4d4f7">**Chore**</span> - for refactoring, adding tests, paying tech debt etc. (anything that isn’t user-facing).


Use the labels of the issue you are working on to determine the best tag.

The message summary should be a one-sentence description of the change, and it must be 72 characters in length or shorter. Please make the short description concise. If the pull request addresses an issue, then the issue number should be mentioned at the end. If the commit doesn’t completely fix the issue, then use (refs #1234) instead of (fixes #1234).

**Note**: please squash you changes in one commit before firing the pull request. One commit in one PR keeps the git history clean.


#### Step 3: Rebase onto upstream

Before you send the pull request, be sure to rebase onto the upstream source. This ensures your code is running on the latest available code. We prefer rebase instead of merge when upstream changes. Rebase keeps the git history clearer.
```bash
git fetch upstream
git rebase upstream/master
```


#### Step 4: Run the tests

The is a place holder as well. We should write about 
* how to run unit test
* how to run funcional test
* what is the acceptance criteria about the test
* how to add test cases


#### Step 5: Push your change
Before pushing the changes, double check your changes follows the [code style](#code-style-and-formatting-tools) and all tests are passed.


Next, push your changes to your clone:
```bash
git push origin fix/issue123
```


#### Step 6: Submit the pull request

Before creating a pull request, here are some recommended **check points**. 

1. Ensure any install or build dependencies are removed before the end of the layer when doing a
   build.
2. Update the splunk_eventgen/README/eventgen.conf.spec with details of changes to the interface, this includes new environment
   variables, exposed ports, useful file locations and container parameters. Also, update the necessary documentation.
3. Make sure the build is successful and all test cases are passed.
4. You may merge the Pull Request in once you have the sign-off of two other developers, or if you
   do not have permission to do that, you may request the second reviewer to merge it for you.


Next, create a pull request from your branch to the eventgen develop branch.
Mark @lephino , @arctan5x , @jmeixensperger , @li-wu , @GordonWang as the reviewers.


## Code style and formatting tools

Since Eventgen is written in python, we apply a coding style based on [PEP8](https://www.python.org/dev/peps/pep-0008/).


**TODO: Add section refrencing the code formatter.**


## How to build eventgen

**TODO: consolidate the setup page information into this section.**

### Build eventgen pip module

### Build eventgen splunk app

### Run unit test

### Run functional test