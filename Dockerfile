ARG BUILD_IMAGE=artefact.skao.int/ska-build-python:0.1.1
ARG BASE_IMAGE=artefact.skao.int/ska-tango-images-tango-python:0.1.0
FROM $BUILD_IMAGE AS build

# Set up environment variables for Poetry and virtualenv configuration
ENV VIRTUAL_ENV=/app \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1

RUN set -xe; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        python3-venv; \
    python3 -m venv $VIRTUAL_ENV; \
    mkdir /build; \
    ln -s $VIRTUAL_ENV /build/.venv
ENV PATH=$VIRTUAL_ENV/bin:$PATH

WORKDIR /build

# Copy project dependency files
COPY pyproject.toml poetry.lock* ./

# Install third-party dependencies from PyPI and CAR
RUN poetry install --only main --no-root --no-directory

# Copy the source code and install the application code
COPY README.md ./
COPY src ./src
RUN pip install --no-deps .

# We don't want to copy pip into the runtime image
RUN pip uninstall -y pip

# Use the base image for the final stage
FROM $BASE_IMAGE

ENV VIRTUAL_ENV=/app
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY --from=build $VIRTUAL_ENV $VIRTUAL_ENV

# Add source code to the PYTHONPATH so Python can locate the package
COPY ./src/ska_mid_dish_b5dc_proxy ./ska_mid_dish_b5dc_proxy
ENV PYTHONPATH=${PYTHONPATH}:/app/

# Metadata labels
LABEL int.skao.image.team="TEAM KAROO" \
      int.skao.image.authors="samuel.twum@skao.int" \
      int.skao.image.url="https://gitlab.com/ska-telescope/ska-mid-dish-b5dc-proxy" \
      description="Tango device which exposes a tango interface to control and monitor the Band 5 Downconverter device" \
      license="BSD-3-Clause"
