# tr069-acs

This is a *hack* to get ip.access CPE configured without using a huge tr069/ACS server like (geniacs, ...).
This simplified version only reacts on **Inform/GetRPCMethods**  and tries to set values from the configuration file without checking the state of the CPE.
It further does not create or delete objects if they don't exist. Neither does it check if the values in the ini file are valid. E.g. by getting both values and type from the device itself.

## Installation

### Windows


```sh
pip install --user pipenv
pipenv install
```

## Configuration

### config/flask.cfg

Please change the `SECRET_KEY` by generating your own. The `SECRET_KEY` is used to sign cookies.

### config/tr098.ini

- The main configuration file for TR-098. The *Common* section is used as default values which can be overriden by a specific CPE configuration.

- To override values for a specific CPE create a section with the serialnumber including leading zeros as shown for *0000123456*.

- After changing values in the tr098.ini the CPE cell can be either rebooted or wait until the CPE is informing us again (see periodic inform / tr069).

## Running

From within the repository call:
```
pipenv run waitress-serve --listen=*:80 app:app
```

## Troubleshooting

### CPE stops reacting on ACS data

Ensure the xml files contain an extra newline (ascii 0xa) on the end of the request.

## Bugs / Limitations

It doesn't use any external database (mysql) or cache system (redis) to reduce the amount of external dependencies and simplify the setup.

## Thanks

Thanks to:

* [Thomas Steen 'tykling' Rasmussen](https://github.com/tykling/)
* [pentonet for their genieacs setup](https://github.com/Pentonet/pentonet-genieacs-package)
