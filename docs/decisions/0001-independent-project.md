# Decision 0001: establish an independent ECHO project

- **Date:** 2026-11-07
- **Status:** Accepted

## Context

The project lead requested a new ECHO project with a clean foundation, independent development, and a private GitHub repository. A repository named `ECHO` already exists under the account, so reusing that repository name would not create a separate project record.

## Decision

Create a new repository named `ECHO-Dancing-with-the-SARs-2026` and a separate local checkout. Use the supplied mission directive as the project brief. Do not copy source, history, datasets, or architecture from any prior ECHO codebase. Technical direction will be established from verified challenge requirements, primary scientific documentation, and project-specific experiments.

## Consequences

- This repository starts with an independent Git history and no application implementation.
- The chosen name makes the challenge association explicit and distinguishes this private project from the existing repository.
- Architecture, implementation status, and evaluation evidence must be established here as work proceeds.
- The initial repository license is intentionally unset pending a licensing and competition-rule review.
