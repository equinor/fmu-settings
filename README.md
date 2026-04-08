# fmu-settings

[![ci](https://github.com/equinor/fmu-settings/actions/workflows/ci.yml/badge.svg)](https://github.com/equinor/fmu-settings/actions/workflows/ci.yml)
[![docs](https://github.com/equinor/fmu-settings/actions/workflows/docs.yml/badge.svg)](https://github.com/equinor/fmu-settings/actions/workflows/docs.yml)

---

**Documentation**: <a href="https://equinor.github.io/fmu-settings/" target="_blank">https://equinor.github.io/fmu-settings/</a>

**Source Code**: <a href="https://github.com/equinor/fmu-settings/" target="_blank">https://github.com/equinor/fmu-settings/</a>

---

**fmu-settings** is a package to manage and interface with `.fmu/`
directories, where the FMU settings are contained.

## Developing

Clone and install into a virtual environment.

```sh
git clone git@github.com:equinor/fmu-settings.git
cd fmu-settings
# Create or source virtual/Komodo env
pip install -U pip
pip install -e ".[dev]"
# Make a feature branch for your changes
git checkout -b some-feature-branch
```

Run the tests with

```sh
pytest -n auto tests
```

Ensure your changes will pass the various linters before making a pull
request. It is expected that all code will be typed and validated with
mypy.

```sh
ruff check
ruff format --check
mypy src tests
```

See the [contributing document](CONTRIBUTING.md) for more.
