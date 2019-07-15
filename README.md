# Near Miss Detection

## Overview

Near Miss Detection is being done by tracking objects using common approach used within CUIP. What differs is the calculation of a predicted future location, and using that to calculate Time Til Collision (TTC). With TTC, we can set a threshold to determine how low TTC can be before a **near miss** is detected. This offers a calculated definition for the written definition of Near Miss:

> Any situation in which may result in an accident or injury, but did not due to timely evasive maneuvers

This means that distance between objects has nothing to do with Near-Miss, but trajectory and TTC make up the entirety of the problem.

## Installation

This repository contains a Pipfile for your convenience. Otherwise you'll need the following libraries for **Python 3.6.5**:

- opencv-python
- cython
- confluent-kafka
- torch
- torchvision
- numba
- scikit-image
- sklearn
- filterpy
- numpy
- pyyaml
- logbook
- quart
- cryptography
- Jinja2
