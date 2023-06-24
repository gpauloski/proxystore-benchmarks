# ProxyStore Benchmark Suite

[![DOI](https://zenodo.org/badge/517741889.svg)](https://zenodo.org/badge/latestdoi/517741889)
[![tests](https://github.com/proxystore/proxystore-benchmarks/actions/workflows/tests.yml/badge.svg)](https://github.com/proxystore/proxystore-benchmarks/actions)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/proxystore/proxystore-benchmarks/main.svg)](https://results.pre-commit.ci/latest/github/proxystore/proxystore-benchmarks/main)

[ProxyStore](https://github.com/proxystore/proxystore) benchmark repository.
Check out the [benchmark instructions](docs/) to get started.

# Installation

```
$ virtualenv venv
$ . venv/bin/activate
$ pip install -e .
```
The `psbench` package can also be installed into a Conda environment if that
is your jam.

## Development Installation

[Tox](https://tox.wiki/en/3.0.0/index.html)'s `--devenv` is the recommended
way to configure a development environment.
```
$ tox --devenv venv -e py 310
$ . venv/bin/activate
$ pre-commit install
```

Alternatively, a development environment can be manually configured.
```
$ virtualenv venv
$ . venv/bin/activate
$ pip install -e .[dev]
$ pre-commit install
```

The test suite can be run with `tox` or for a specific Python version with
`tox -e py39`. Linting/type-checking/etc. can be run using pre-commit:
`pre-commit run --all-files`.
