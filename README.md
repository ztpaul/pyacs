# 1 Introduction

pyacs is a tr069 acs written by python. The following features have been finished.

## 1.1 ACS RPC Methods
- GetRPCMethods
- Inform

# 2 Installation

*make sure you have installed python3(3.10 is recommended) in your platform.*


```sh
pip install --user pipenv
pipenv install
```

# 3 Configuration

## 3.1 config/flask.cfg

Please change the `SECRET_KEY` by generating your own. The `SECRET_KEY` is used to sign cookies.

## 3.2 config/tr098.ini

- The main configuration file for TR-098. The *Common* section is used as default values which can be overriden by a specific CPE configuration.

- To override values for a specific CPE create a section with the serialnumber including leading zeros as shown for *0000123456*.

- After changing values in the tr098.ini the CPE cell can be either rebooted or wait until the CPE is informing us again (see periodic inform / tr069).

# 4 Running

From within the repository call:
```
pipenv run waitress-serve --listen=*:80 pyacs:app
```

# 5 Troubleshooting

## 5.1 CPE stops reacting on ACS data

Ensure the xml files contain an extra newline (ascii 0xa) on the end of the request.

# 6 Bugs / Limitations

It doesn't use any external database (mysql) or cache system (redis) to reduce the amount of external dependencies and simplify the setup.
