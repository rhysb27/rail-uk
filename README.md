# Rail UK

[![CircleCI](https://circleci.com/gh/rhysb27/rail-uk/tree/master.svg?style=svg)](https://circleci.com/gh/rhysb27/rail-uk/tree/master)
[![codecov](https://codecov.io/gh/rhysb27/rail-uk/branch/master/graph/badge.svg)](https://codecov.io/gh/rhysb27/rail-uk)

## Project Overview

Rail UK is a Skill for Amazon's [Alexa](https://www.amazon.com/Amazon-Echo-And-Alexa-Devices/b?ie=UTF8&node=9818047011), which aims to provide reliable and accurate train times within the UK by way of an intuitive voice interface. It currently offers the following features:

* **Set Home Station** - Allows the user to specify a "home station", as well as how long it takes the user to travel to the station. The skill will then remember this information and factor it into future requests when no origin station is specified. The travel time the user provides will be used to ensure that the skill doesn't tell the user about a train that they won't be able to get to in time.

* **Next Train** - Retrieves the next train to a specified destination, departing from either the user's home station (if set) or a specified origin, along with live departure information.

* **Fastest Train** - Retrieves the fastest train to a specified destination, departing from either the user's home station (if set) or a specified origin, along with live departure information.
* **Last Train** - Retrieves the last train of the current day to a specified destination, departing from either the user's home station (if set) or a specified origin, along with live departure information if the train is timetabled to depart within the next two hours.



## Technical Overview

The Rail UK skill is comprised of three components:

1. **Alexa Voice Interaction Model** - High-level definition of the ways in which users can interact with the skill, implemented using the [Alexa Development Console](https://developer.amazon.com/alexa).
2. **Python Codebase** - Implementation of the Skill's underlying logic, hosted on [AWS Lambda](https://aws.amazon.com/lambda/).
3. **NoSQL Database** - Storage of users' home station data, using [Amazon DynamoDB](https://aws.amazon.com/dynamodb/)

This repository only contains one of these components - the **Python Codebase**.



#### Third Party Services

Rail UK also uses two APIs for fetching departure information:

1. **[OpenLDBWS](http://lite.realtime.nationalrail.co.uk/openldbws/)** - SOAP API for live departure information.

2. **[TransportAPI](https://developer.transportapi.com/docs?raml=https://transportapi.com/v3/raml/transportapi.raml)** - REST API for future timetable information.



### Project Structure

This project does not follow a conventional Python project structure. This is because AWS Lambda requires the function that handles incoming lambda triggers (`lambda_entry` in this case) to be in a file in the root directory of the deployment package.

The structure is as follows:

```
rail-uk/
├── .circleci
│   └── config.yml			# Configuration for CI/CD.
│
├── rail_uk/                # Rail UK's underlying logic.
│   ├── __init__.py
│   ├── data.py             # Creates, sends and parses SOAP and HTTP requests
│   ├── dtos.py             # Houses Data Transfer Object definitions
│   ├── dynamodb.py         # Communicates with Amazon DynamoDB
│   ├── events.py           # Handles various Alexa Skill events and wraps intent handlers
│	├── exceptions.py		# Custom exceptions used by the Skill
│   ├── intents.py          # Handles all skill intents
│   └── lambda_handler.py   # Handles incoming function triggers
│
├── scripts/                # Scripts for deploying Python packages to AWS Lambda
├── res/                    # Static resources used by Rail UK 
│   ├── templates/          # SOAP templates for OpenLDBWS requests
│   └── stations.csv        # Values used by Alexa to match station names
│
├── tests/
│   ├── helpers/     		# Package containing helpers for tests
│   ├── mock_responses/     # Example responses for testing
│   ├── <module>_test.py	# Unit tests for a specific module
│   └── end_to_end_tests.py	# End-to-end tests for skill's happy paths
│
├── lamdba_entry.py			# Provides a simple entry point for Lambda trigger
├── README.md				# This file
├── requirements.txt        # Runtime dependencies
├── requirements-dev.txt    # Development/Testing dependencies
├── setup.cfg               # Py.test configuration
└── template.env            # Template environment variable file
```



#### Intents

Rail UK, just like all Alexa Skills, is based on the idea of **intents**. At a high level, intents are essentially features. Currently, four intents have been implemented:

#### `SetHomeStation`

This intent allows users to set or update their home station, which is persisted and can be used as a default value for the `origin` slot in service-related queries.

When a user's home station is set and used when using the `FastestTrain` or `NextTrain` intents, the `distance` value is used as a time offset in the query so that the user will only be given information on departures that they'll be realistically able to get to the station in time for.

The slots this intent uses are:

* `home` - The name/colloquial name of the desired home station
* `distance` - The time it typically takes the user to travel to the desired home station



#### `NextTrain`

This intent retrieves live departure information about the **next** direct train to `destination` from `origin`. 

The slots this intent uses are:

* `destination` - The name/colloquial name of the station the user would like to travel to.

* `origin` (_Optional_) - The name/colloquial name of the station the user would like to travel _from_.

  This slot may be omitted when a Home Station has been set. In this case, the intent will instead find the user's home station details, use the station as the value of the `origin` slot, and use the `distance` value as an offset in the OpenLDBWS query.



#### `FastestTrain`

This intent retrieves live departure information about the **fastest** direct train to `destination` from `origin`, where "fastest train" is defined as the train that _reaches `destination` soonest_.

For slots, see `NextTrain`.



#### `LastTrain`

This intent finds the last direct service from `origin` to `destination` on that day.

Unlike `NextTrain` and `FastestTrain`, this intent *does not* factor the home station's `distance` into the TransportAPI query when `origin` is omitted. This is because the intent will always return the last service on any particular day, regardless of the relative time of the user's request (i.e. before or after).

For slots, see `NextTrain`.



---

Intent delegation is handled by the Alexa service.



## Setup

Setting up Rail UK for testing purposes is extremely simple.
1. Ensure `python3` (>=3.6), `venv` and `pip`/`pip3` are installed.

2. Create and activate a virtual environment:

    `python3 -m venv venv`

    `source venv/bin/activate`

3. Install dependencies:

    `pip install -r dev-requirements.txt`

Setup for runtime is significantly more involved and is discussed in a later section of this README.



## Run Tests

This project uses `pytest` and `pytest-cov` for unit and end-to-end testing. These packages will already be pre-installed the setup section has been followed.

#### Unit Tests

To run the full suite of unit tests with coverage reporting, navigate to the project's root directory and run:

​	`python3 -m pytest --cov-report term-missing --cov=rail_uk`

#### End-to-End Tests

For simplicity's sake - and permitted by the [high coverage](https://codecov.io/gh/rhysb27/rail-uk) acheived by the unit tests - end-to-end tests currently only cover happy paths for each of the "Get Train"-style intents:

1. `NextTrain` with `origin` and `destination` slots supplied
2. `FastestTrain` with `origin` and `destination` slots supplied
3. `LastTrain` with `origin` and `destination` slots supplied

The end-to-end tests use mocked responses for OpenLDBWS and TransportAPI requests, and have no need to communicate with DynamoDB. This is to remove dependency on full setup and the third-party services themselves during testing. The tests can be run with:

​	`python3 -m pytest tests/end_to_end_tests.py`




## Run
**Note**: While running Rail UK locally is technically possible, there's currently no script for actually supplying the right data to the `lambda_entry` module and providing a response. An Alexa Simulator is currently in development, which will draw in heavily from the implementation of the end-to-end tests and allow local users to call upon intents with their desired slot values in order to get real, live departure information. **/Note**

This project was specifically designed for execution within an AWS Lambda function as part of an Alexa skill. As a consequence, running Rail UK locally will require users to set up some AWS resources and gain access to two third-party APIs.

#### Third Party Resources
* **OpenLDBWS** - Register [here](http://realtime.nationalrail.co.uk/OpenLDBWSRegistration/).
* **TransportAPI** - Register [here](https://developer.transportapi.com/signup).
* **[Amazon DynamoDB](https://aws.amazon.com/dynamodb/)**

#### Configuring
Once registered for OpenLDBWS and TransportAPI, API configuration is as simple as populating some environment variables. A [template](template.env) `.env` file has been provided to give the naming scheme of these variables. A suitable copy should be made and populated with the appropriate values.

Configuring DynamoDB is more involved. You'll need to follow Amazon's documentation to setup a table with the **name** 'RailUK' and **partition key** 'UserID'. You'll also need setup the appropriate IAM permissions, and install and configure [`awscli`](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html) so that `boto3` can work it's magic and communicate with your table.

*Side Note: I'll eventually abstract the table name and partition key into appropriate environment variables.*

Once you've done all that, you should be able to run this project! To actually make use of the project, a script will need to be written that provides a valid Alexa request object to the `lambda_entry` module.
