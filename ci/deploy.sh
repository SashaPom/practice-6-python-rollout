#!/usr/bin/env bash
set -Eeuo pipefail

repository="${1:?supply the registry image repository}"
revision="${2:?supply the commit hash}"
candidate="$repository:$revision"
stable="$repository:stable"
origin="http://127.0.0.1:${HOST_PORT:-8098}"
mkdir -p reports/deploy

verify_image() {
    local image="$1" version="$2" phase="$3"
    local container failed=0
    export APP_IMAGE="$image"

    echo "Phase $phase: $image"
    docker compose up -d --force-recreate --pull never --wait --wait-timeout 25 \
        2>&1 | tee "reports/deploy/$phase-compose.log" || failed=1
    container=$(docker compose ps --all --quiet service) || failed=1
    if [[ -n "$container" ]]; then
        python -m pytest -q infra --hosts="docker://$container" \
            --junitxml="reports/deploy/$phase-testinfra.xml" \
            2>&1 | tee "reports/deploy/$phase-testinfra.log" || failed=1
    else
        echo "Compose did not create a service container" | tee "reports/deploy/$phase-testinfra.log"
        failed=1
    fi
    python ci/probe.py "$origin" "$version" \
        2>&1 | tee "reports/deploy/$phase-http.log" || failed=1
    docker compose logs --no-color --timestamps service \
        > "reports/deploy/$phase-container.log" 2>&1 || failed=1
    return "$failed"
}

previous=""
previous_revision=""
if docker pull "$stable" > reports/deploy/previous-pull.log 2>&1; then
    digest=$(awk '/^Digest: sha256:/ { print $2 }' reports/deploy/previous-pull.log)
    if [[ ! "$digest" =~ ^sha256:[a-f0-9]{64}$ ]]; then
        echo "Could not determine the stable image digest" >&2
        exit 1
    fi
    previous="$repository@$digest"
    previous_revision=$(docker image inspect \
        --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$previous")
    [[ "$previous_revision" =~ ^[a-f0-9]{40}$ ]]
    verify_image "$previous" "$previous_revision" baseline
elif grep -Eqi 'manifest unknown|not found' reports/deploy/previous-pull.log; then
    echo "No stable image yet; bootstrapping the training environment"
else
    cat reports/deploy/previous-pull.log >&2
    exit 1
fi

if verify_image "$candidate" "$revision" candidate; then
    if docker tag "$candidate" "$stable" && docker push "$stable"; then
        echo "Promoted $revision to stable"
        exit 0
    fi
    echo "Stable promotion failed" >&2
else
    echo "Candidate $revision failed verification" >&2
fi

if [[ -n "$previous" ]]; then
    echo "Rolling back to $previous_revision ($previous)"
    if verify_image "$previous" "$previous_revision" rollback; then
        echo "Rollback verified: /health=200, /version=$previous_revision"
    else
        echo "Rollback verification failed" >&2
    fi
else
    echo "No earlier image is available for rollback" >&2
fi
exit 1
