6.4.0
- Fix exception log error
- Fix CircleCI status badage error
- Fix navigation error for app if installed with Splunk Stream
- Fix generatorWorkers not working error
- Fix interval error when end = 1
- Fix fileName in global stanza error
- Add 3rd party libs in SA-Eventgen App
- Add httpeventAllowFailureCount for httpevent
- Add 3rd party libs in license credit
- Disable logging queue in multiprocess mode
- Change implementation of extendIndex for better performance

6.3.6
- Add functional tests for jinja template and modular input feature
- Fix default jinja template directory is not correctly resolved when sampleDir is set issue
- Fix verbose flag not working in splunk_eventgen command line issue
- Fix index, source, sourcetype are not correct when using splunkstream mode issue
- Fix ssh to container issue
- Fix perdayvolume without end setting error
- Update documentation for better reading and remove unrelated part

6.3.5
- Added extendIndexes feature to support a list of indexes
- Fixed timer and token logic
- Changed end=-1 to continuously iterate without stopping
- Changed end=0 to not execute
- Added a linter for code quality
- Updated docs / docs format
- Added a suite of functional tests

6.3.4:
- Documentation cleanup
- Jinja template bugfix in app
- Implementation of 'timeMultiple’ option
- Templates for bugs/feature requests
- Fixed Jinja test configuration stanzas
- Default behavior for 'count' edge cases

6.3.3:
- Added performance metrics compared to Eventgen 5.x
- New config option for generation-time metrics: outputCounter
- Jinja template fixes
- Timestamp parsing fix
- Output queueing fix for outputMode splunkstream
- Count rater fixes, now supports indefinite generation

6.3.2:
- Fixed verbosity bug
- Added documentation

6.3.1:
- Fixed Eventgen Volume APIs
- Improved Eventgen Server Logging
- Corrected Eventgen Server and Controller conf syncing issue
- Adding verbosity options (ERROR, INFO, DEBUG) to Eventgen modinput
- Implemented future event generation support in replay mode
- Fixed Jinja template's missing default values
- Adjusted logging message levels for less verbosity
- Fixed event count off by 1 issue
- Fixed unnecessary empty data generators being created
- Updated dependency list

6.3.0:
- Bug fixes for the customer issues
- Documentation upgrade
- Code refactoring for version unification
- Logging improvements

6.2.1:
- Fixing SA-Eventgen Dashboard and log searching
- Improving internal logging and fixing splunkd logging issue
- Fixing timestamping in default generator
- Fixing custom plugin integration
- Fixing SA-Eventgen app settings
- Supporting Eventgen 5 backward compatibility with additional features
- Better modinput process management
- Minor Bugfixes with various customer cases
