# ska-mid-dish-b5dc-proxy

Tango proxy to the Band 5 down-converter


## Documentation

[![Documentation Status](https://readthedocs.org/projects/ska-telescope-ska-mid-dish-b5dc-proxy/badge/?version=latest)](https://developer.skao.int/projects/ska-mid-dish-b5dc-proxy/en/latest/?badge=latest)

The documentation for this project, including how to get started with it, can be found in the `docs` folder, or browsed in the SKA development portal:

* [ska-mid-dish-b5dc-proxy documentation](https://developer.skatelescope.org/projects/ska-mid-dish-b5dc-proxy/en/latest/index.html "SKA Developer Portal: ska-mid-dish-b5dc-proxy documentation")

## Installation

This project's requirement is managed with poetry and can be installed using a package manager or from source.

### From source

- Clone the repo

```bash
git clone git@gitlab.com:ska-telescope/ska-mid-dish-b5dc-proxy.git
```

- Install poetry

```bash
pip install poetry
```

Install the dependencies and the package.

```bash
poetry install
```

## Testing

- Run the unit tests

```bash
make python-test

- Lint

```bash
make python-lint
```

## Development
### Deploy Band 5 Down-Converter(B5dc) Manager with B5dc simulator

- Deploy b5dcmanager with UDP server from ska-mid-dish-dcp-lib

```bash
kubectl create namespace b5dc-manager
```

```bash
$  helm upgrade --install dev charts/ska-mid-dish-b5dc-proxy -n b5dc-manager \
--set global.minikube=true \
--set global.operator=true \
--set global.dishes="{001,002}" \ # number of instances to deploy; if not specified defaults to 001
--set ska-mid-dish-dcp-lib.enabled=true  \
--set ska-mid-dish-dcp-lib.b5dcSimulator.enabled=true
```

`ska-tango-base` is not deployed by default, to deploy it add the `--set` below:

```bash
--set ska-tango-base.enabled=true
```

## Writing documentation

The documentation for this project can be found in the docs folder. For local builds,
plantuml is required to render the UML diagrams. Download `plantuml.jar` from the [plantuml website](https://plantuml.com/download), move it to `./docs/src/utils` and run `export LOCAL_BUILD=True`. Then
run the command below and browse the docs from `docs/build/html/index.html`.

```bash
make docs-build html
```