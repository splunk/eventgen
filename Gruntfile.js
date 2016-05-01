module.exports = function(grunt) {
    'use strict';

    var utils = require('./node_modules/ext-grunt-basebuild/common/utils.js');

    var buildinfo = {
        "name": "SA-Eventgen",
        "version": "5.0.0",
        "packagefiles": {
            "files": [{
                "dir": "package",
                "src": ["**/*","!**/.*","!local/**","!build/**","!**/*-gist","!**/*.xcf","!build.*"],
                "dest": "stage"
            }]
        },
        "extension": "spl",
	"buildNumber": process.env['BUILDNUMBER'] || 0
    };

    buildinfo = utils.overrideconfigs(buildinfo, "local.properties.json");

    try {

        require('ext-grunt-horde')
            .create(grunt)
            .demand('initConfig.buildinfo', buildinfo)
            .loot('ext-grunt-basebuild')
            .attack();
    } catch (e) {
        console.log(e.lineNumber);
    }
};
