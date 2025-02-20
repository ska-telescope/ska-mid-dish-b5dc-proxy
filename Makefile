#############################
# BASE
#############################
SHELL=/bin/bash
.SHELLFLAGS=-o pipefail -c

NAME=ska-mid-dish-b5dc-proxy
VERSION=$(shell grep -e "^version = s*" pyproject.toml | cut -d = -f 2 | xargs)
IMAGE=$(CAR_OCI_REGISTRY_HOST)/$(NAME)
DOCKER_BUILD_CONTEXT=.
DOCKER_FILE_PATH=Dockerfile

MINIKUBE ?= true ## Minikube or not
SKA_TANGO_OPERATOR = true
TANGO_HOST ?= tango-databaseds:10000  ## TANGO_HOST connection to the Tango DS
CLUSTER_DOMAIN ?= cluster.local ## Domain used for naming Tango Device Servers

-include .make/base.mk


#############################
# DOCS
#############################
-include .make/docs.mk


#############################
# PYTHON
#############################
# set line length for all linters
PYTHON_LINE_LENGTH = 99

# Set the specific environment variables required for pytest
PYTHON_VARS_BEFORE_PYTEST ?= PYTHONPATH=.:./src \
							 TANGO_HOST=$(TANGO_HOST)
PYTHON_VARS_AFTER_PYTEST ?= -m '$(MARK)' --forked --json-report --json-report-file=build/report.json --junitxml=build/report.xml

python-test: MARK = unit
k8s-test-runner: MARK = acceptance
k8s-test-runner: TANGO_HOST = tango-databaseds.$(KUBE_NAMESPACE).svc.$(CLUSTER_DOMAIN):10000

-include .make/python.mk


#############################
# OCI, K8s, Helm
#############################
OCI_TAG = $(VERSION)-dev.c$(CI_COMMIT_SHORT_SHA)

CI_REGISTRY ?= registry.gitlab.com

# Use the previously built image when running in the pipeline
ifneq ($(CI_JOB_ID),)
CUSTOM_VALUES = --set b5dcmanager.image.image=$(NAME) \
	--set b5dcmanager.image.registry=$(CI_REGISTRY)/ska-telescope/$(NAME) \
	--set b5dcmanager.image.tag=$(OCI_TAG) \
	--set ska-mid-dish-dcp-lib.enabled=true  \
	--set ska-mid-dish-dcp-lib.b5dcSimulator.enabled=true \
	--set ska-tango-base.enabled=true \
	--set global.dishes="{001}"
K8S_TEST_IMAGE_TO_TEST=$(CI_REGISTRY)/ska-telescope/$(NAME)/$(NAME):$(OCI_TAG)
K8S_TIMEOUT=600s
endif

K8S_CHART_PARAMS = --set global.minikube=$(MINIKUBE) \
	--set global.tango_host=$(TANGO_HOST) \
	--set global.operator=$(SKA_TANGO_OPERATOR) \
	--set global.cluster_domain=$(CLUSTER_DOMAIN) \
	$(CUSTOM_VALUES)

-include .make/oci.mk
-include .make/k8s.mk
-include .make/helm.mk


# include your own private variables for custom deployment configuration
-include PrivateRules.mak
