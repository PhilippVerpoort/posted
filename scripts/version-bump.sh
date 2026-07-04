#!/usr/bin/env bash
#
# version-bump.sh — perform all required steps before releasing a new version.
#
# This updates the version number and release date in the project's metadata
# files, creates a "Version bump." commit, and creates an annotated git tag.
# It does NOT push; review the commit and tag, then push manually, e.g.:
#
#     git push && git push --tags
#
# Usage:
#     scripts/version-bump.sh <new-version> <tag-message>
#
# Arguments:
#     <new-version>   New version number without leading "v" (e.g. 0.5.5).
#     <tag-message>   Annotation message for the git tag (e.g.
#                     "Releasing v0.5.5 that fixes ...").
#
# Example:
#     scripts/version-bump.sh 0.5.5 "Releasing v0.5.5 with new data."

set -euo pipefail

# --- Parse and validate arguments -------------------------------------------

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <new-version> <tag-message>" >&2
    exit 1
fi

version="$1"
tag_message="$2"

if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: version '$version' is not of the form MAJOR.MINOR.PATCH." >&2
    exit 1
fi

tag="v${version}"
release_date="$(date +%F)"  # ISO 8601 date, e.g. 2026-07-04

# --- Locate the repository root ----------------------------------------------

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
    echo "Error: working tree has uncommitted changes; aborting." >&2
    exit 1
fi

if git rev-parse -q --verify "refs/tags/${tag}" >/dev/null; then
    echo "Error: tag '${tag}' already exists." >&2
    exit 1
fi

# --- Update metadata files ---------------------------------------------------

# pyproject.toml: version = "X.Y.Z"
sed -i -E "s/^version = \"[^\"]*\"/version = \"${version}\"/" pyproject.toml

# .zenodo.json: "version": "X.Y.Z" and "publication_date": "YYYY-MM-DD"
sed -i -E "s/(\"version\": \")[^\"]*(\")/\1${version}\2/" .zenodo.json
sed -i -E "s/(\"publication_date\": \")[^\"]*(\")/\1${release_date}\2/" .zenodo.json

# CITATION.cff: version: vX.Y.Z and date-released: YYYY-MM-DD
sed -i -E "s/^version: .*/version: ${tag}/" CITATION.cff
sed -i -E "s/^date-released: .*/date-released: ${release_date}/" CITATION.cff

# --- Show the diff for confirmation ------------------------------------------

echo "Updated metadata files to version ${version} (released ${release_date}):"
git --no-pager diff -- pyproject.toml .zenodo.json CITATION.cff

# --- Commit and tag ----------------------------------------------------------

git add pyproject.toml .zenodo.json CITATION.cff
git commit -m "Version bump."
git tag -a "${tag}" -m "${tag_message}"

echo
echo "Created commit and annotated tag '${tag}'."
echo "Nothing has been pushed. To publish the release, run:"
echo "    git push && git push --tags"
