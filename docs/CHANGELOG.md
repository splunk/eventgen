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