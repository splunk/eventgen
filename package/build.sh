#!/usr/bin/env sh
# This should be run from the $SPLUNK_HOME/etc/apps/oidemo directory.

# Save for later
CURRENT_PWD=`pwd`

# Cleanup
rm $CURRENT_PWD/eventgen.spl

# Create a build directory that we can use
BUILD_DIR=.build/SA-Eventgen
BUILD_DIR_PARENT=.build
mkdir -p $BUILD_DIR

cp -R * $BUILD_DIR
cd $BUILD_DIR_PARENT
rm SA-Eventgen/local/eventgen-standalone.conf
tar cfz $CURRENT_PWD/eventgen.spl SA-Eventgen --exclude "SA-Eventgen/eventgen.spl" --exclude "SA-Eventgen/.*"
cd $CURRENT_PWD
rm -rf $BUILD_DIR

echo "Build Complete"
