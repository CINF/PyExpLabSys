This folder is for tests of different kinds, both unit test and
integration tests and functional test.

For this project we define:

 * **Unittest:** (non-controversially) as being the test of the single
   unit of code, isolated from everything else
 * **Integration test:** as being the test of any combination of units
   of code, except full function and not involving any hardware
   (equipment)
 * **Functional test:** as being the test of the complete function,
   including hardware (if required)

Please order the tests with a folder for each of the categories (common,
drivers, parsers etc.) and a file inside for each class.

The tests are made to be run with pytest, which will automatically
pick up tests from files and (classes and functions) that start with
'test'. To execute the test, enter e.g. the common folder and do:

```sh
python -m pytest
```
to run all tests in there, or
```sh
python -m pytest test_continous_logger.py
```
to run only the tests of the continous logger.

More information about pytest can be read on the homepage:
http://pytest.org/latest/
