Convention:
* Test conf files are located at `conf` folder;
* Sample files are located at `sample` folder;
* Other utils related tools are located at `utils` folder;
* `fileName` in `conf` settings is relative which will write results to folder `tests/large/results`;

How to add a new functional test:
* Add eventgen conf file in `conf` folder;(`sampleDir = ../sample` should be in the conf stanza)
* Add sample file defined in above eventgen conf in folder `sample`;
* Add a new functional test `py` file and add test case;
* Use `eventgen_test_helper` fixture to create a helper instance and use `get_events()` to get events generated;
* Pass `timeout=60` if you want to stop eventgen instance after 60s;
