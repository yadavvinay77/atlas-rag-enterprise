# Contributing

Use short-lived branches from `main`, such as `feature/hybrid-retrieval` or
`fix/follow-up-context`. Open a pull request and merge only after CI passes.

Use Conventional Commit messages:

- `feat: add hybrid retrieval`
- `fix: keep follow-up queries on topic`
- `docs: update local setup`
- `test: cover MMR ranking`

Versions follow Semantic Versioning (`MAJOR.MINOR.PATCH`). Update `pyproject.toml` and
`CHANGELOG.md`, commit the release, then create a tag such as `v0.3.0`. Tag pushes publish
the corresponding container image through GitHub Actions.

