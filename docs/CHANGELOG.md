6.3.4:
- New release notes

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