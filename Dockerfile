ARG BUILD_IMAGE=artefact.skao.int/ska-build-python:0.1.1
ARG BASE_IMAGE=artefact.skao.int/ska-tango-images-tango-python:0.1.0
FROM $BUILD_IMAGE as build

# Set up environment variables for Poetry and virtualenv configuration
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1

WORKDIR /build

# Copy project dependency files (pyproject.toml, poetry.lock, etc.)
COPY pyproject.toml poetry.lock* README.md ./

# Uncomment below to rebuild lock file
# RUN poetry lock --no-update

# Install third-party dependencies from PyPI and CAR
RUN poetry install --no-root --no-directory

# Copy the source code and install only the application code
COPY src/ ./src

RUN poetry install --only main

# Use the base image for the final stage
FROM $BASE_IMAGE

WORKDIR /app

# Set up virtual environment path
ENV VIRTUAL_ENV=/build/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy the virtual environment from the build stage
COPY --from=build ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY --from=build /build/pyproject.toml .

# Uncomment below to store lock file
# COPY --from=build /build/poetry.lock /app/poetry.lock

# Add source code to the PYTHONPATH so Python can locate the package
COPY ./src/ska_mid_dish_b5dc_proxy/ ./ska_mid_dish_b5dc_proxy/
ENV PYTHONPATH=${PYTHONPATH}:/app/

# Metadata labels
LABEL int.skao.image.team="TEAM KAROO" \
      int.skao.image.authors="samuel.twum@skao.int" \
      int.skao.image.url="https://gitlab.com/ska-telescope/ska-mid-dish-b5dc-proxy" \
      description="Tango device which exposes a tango interface to control and monitor the Band 5 Downconverter device" \
      license="BSD-3-Clause"
