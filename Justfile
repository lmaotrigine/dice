#!/usr/bin/env -S just -f

_default:
  @just --list

types:
  pyright
  pyright --verifytypes dice --ignoreexternal

lint: types
  ruff check
  ruff format --check --diff

fmt:
  ruff format

_test fast="":
  pytest --cov=dice --cov-report=term-missing:skip-covered --cov-report=xml \
    --cov-config={{justfile_directory()/"pyproject.toml"}} \
    {{ if fast == "fast" { "-k 'not test_hypothesis'" } else { "" } }}

fasttest: (_test "fast")
test: _test

ws:
  ! rg '\r'
