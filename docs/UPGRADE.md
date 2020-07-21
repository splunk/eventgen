# Upgrade

There are multiple ways to use Eventgen, two major ways to use Eventgen - as a PyPI module and as a Splunk App.

## Eventgen PyPI module upgrade

For PyPI module upgrade, you can follow [setup page](./SETUP.md#pypi-installation) to install eventgen PyPI module with the latest release source code.

<a id="sa-app-upgrade"></a>
## Eventgen Splunk app upgrade

Normally, follow these steps to upgrade your eventgen SA.

1. Download the latest SA-eventgen app from [splunkbase](https://splunkbase.splunk.com/app/1924/)
1. Log in to Splunk Web and navigate to Apps > Manage Apps.
1. Click "Install app from file".
1. Navigate to the path where your downloaded tgz file is and select.
1. Check the checkbox "Upgrade app. Checking this will overwrite the app if it already exists."
1. Restart Splunk after you have been notified of a successful upgrade.

<a id="sa-app-upgrade-to-7"></a>
### Upgrade Eventgen Splunk app from 6.x to 7.x

> :bangbang: Starting from Eventgen 7.x, Eventgen only supports python3. A lot of changes in python code between 6.x and 7.x. And these changes break the SA-eventgen upgrade from 6.x to 7.x.

**Read the following guide carefully if you want to upgrade SA-eventgen from 6.x to 7.x.**

:heavy_exclamation_mark: **A new installation of SA-Eventgen 7.x is recommended**.
Because splunk enterprise upgrades the app by copying all the files in new app package to the app folder. If you just ugprade SA-eventgen by normal steps, without a new installation for SA-Eventgen 7.x, there will be some python files which only exist in SA-Eventgen 6.x. These outdated python files will break modinput in SA-eventgen 7.x.

Follow these steps to upgrade SA-eventgen from 6.x to 7.x.

1. Backup your conf files in `<SPKUNK_HOME>/etc/apps/SA-Eventgen/local`
1. *Optional* backup your customized sample files in `<SPKUNK_HOME>/etc/apps/SA-Eventgen/samples`. If you do not put any sample files in SA-eventgen samples folder, you can skip this step.
1. Remove all the files in `<SPKUNK_HOME>/etc/apps/SA-Eventgen/*`
1. Download the SA-eventgen app 7.x from [splunkbase](https://splunkbase.splunk.com/app/1924/)
1. Log in to Splunk Web and navigate to Apps > Manage Apps.
1. Click "Install app from file".
1. Navigate to the path where your downloaded tgz file is and select.
1. Check the checkbox "Upgrade app. Checking this will overwrite the app if it already exists."
1. Restore your SA-eventgen conf backup files to `<SPKUNK_HOME>/etc/apps/SA-Eventgen/local`
1. *Optional* restore your backup sample files to `<SPKUNK_HOME>/etc/apps/SA-Eventgen/samples`
1. Restart Splunk after you have been notified of a successful upgrade.




