#!/usr/bin/env bash
# Détecte la version depuis le tag Git exact; retourne "dev" si non taguée ou arbre sale.
TAG=$(git describe --exact-match --tags HEAD 2>/dev/null)
if [ -n "$TAG" ] && git diff --quiet && git diff --cached --quiet; then
    echo "${TAG#v}"
else
    echo "dev"
fi
