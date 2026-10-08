---
title: "Containers for the workload"
description: "Opt-in rootless Docker for tools that run their own containers: what changes, how images enter, target networks, model calls and checks."
---

Some tools start their own containers: Strix and PentAGI for testing a running
application, and Mantis's reproduce and patch stages. The standard VM gives the
workload no Docker access. `create --docker` adds a Docker daemon that belongs to
the workload user.

```bash
appsec-sbx create appsec-sbx --docker --image python:3.12-slim
```

So far this has been checked on macOS only. Windows and Linux hosts follow.

## What changes

- The workload user gets its own *rootless* Docker daemon. The daemon and its
  containers act as that user, so `docker` grants nothing the workload could not
  already do. The administrator's daemon stays closed to it, as on every VM.
- Container traffic meets the same network policy as the workload's own traffic:
  allowed hosts are reachable, everything else is refused.
- All containers share one memory limit of 6 GB. A container that exceeds it is
  stopped; the harness keeps running. There are no CPU or per-container limits.
- The daemon and every container stop with the VM, including sbx's idle stop.
  Keep a session open while long container runs work.
- `reset` removes images built during the run, containers, volumes and daemon
  settings. The images named at `create` come back.
- `verify` lists the daemon, the memory limit and the provisioned images with
  their digests.

The wrapper deliberately does not give the workload the administrator's daemon.
That daemon runs as root inside the VM, and root inside the VM reaches host
interfaces that the workload otherwise cannot. The
[design note](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/design/sbx-docker-profile.md)
records the reasoning and the checks behind it.

## Getting images in

Images enter while the VM is created, before its network is locked. Name each
one with `--image`; Docker Hub and `ghcr.io` are supported. Pin a digest where
you can (`name:tag@sha256:...`): the image keeps its tag, and `create` records
the digest of every image. `curlimages/curl` is always included for the network
checks below.

During a run, `docker pull` fails unless you allowed a container registry with
`--registry dockerhub` or `--registry ghcr`. The harness and every container can
then reach that registry, and it can receive data like any allowed host.

To build an image during a run, provision its base images with `--image`, allow
the registry its dependencies come from (for example `--registry pypi`), and
build with `docker build --pull=false`. Every container can use that registry
for the rest of the run, not only the build.

`--docker-disk` sets the size of the VM's Docker volume, which holds images and
containers (default 32 GB). Very large images, such as PentAGI's Kali worker
(about 13 GB unpacked), need more.

## Run targets on an internal network

Run the application under test on a network with no route out:

```bash
docker network create --internal targets
docker run -d --name app --network targets my-target:latest
docker network connect targets <tool-container>
```

Containers on the internal network reach each other and nothing else.
Containers on the default network reach every allowed host, including the
model service and any registry. Keep a tool container off the default network
where the tool allows it.

Publish ports to `127.0.0.1` only. Containers cannot reach services that listen
on the VM's own loopback address, so run the target as a container rather than
as a process in the workload.

## Model calls from containers

Prefer tools that call the model from the workload, outside their containers;
Strix does this. A container that calls the model itself needs the key
placeholder, the forward proxy and the VM's CA bundle, because the proxy
inspects TLS to the model host to add the key:

```bash
docker run --rm \
  -e HTTPS_PROXY=http://gateway.docker.internal:3128 \
  -e OPENROUTER_API_KEY=proxy-managed \
  -v /etc/ssl/certs/ca-certificates.crt:/etc/ssl/certs/ca-certificates.crt:ro \
  my-tool:latest
```

Any container on the default network can use the stored key this way. Keep the
provider-side budget in place.

## Check the container paths

After `create`, repeat the [network denial checks](/sandbox/sbx/lifetime/#check-network-denial)
from a container. Inside `appsec-sbx shell`:

```bash
docker run --rm curlimages/curl -sS -o /dev/null -w '%{http_code}\n' https://openrouter.ai/api/v1/models
docker run --rm curlimages/curl -sS --max-time 10 https://example.com
docker run --rm curlimages/curl -sSk --max-time 10 https://1.1.1.1
docker pull busybox
docker network create --internal check
docker run --rm --network check curlimages/curl -sS --max-time 5 https://openrouter.ai
docker network rm check
```

Expect a status code from the allowed provider host and failures for the rest.
`appsec-sbx logs` shows the matching denials. The log names the VM, not the
container that sent a request.

## Example: Strix

[Strix](/tools/shortlist/#strix) calls the model from the workload and drives
its tool container through Docker. A run against an application you own, with
a Python target built inside the VM:

```bash
appsec-sbx create appsec-sbx --docker --registry pypi \
  --image ghcr.io/usestrix/strix-sandbox:1.3.0@sha256:f6906c3114e504fd1a218fcf028d7a0e46851118403a438b63956de6ea7c4331 \
  --image python:3.12-slim
appsec-sbx put appsec-sbx ./strix-1.7.0-linux-arm64 /home/appsec/bin/strix
appsec-sbx import appsec-sbx /path/to/app
appsec-sbx shell --key appsec-sbx
```

Download the release binary on the host and check it first; take
`linux-x86_64` on Windows and Linux hosts, `linux-arm64` on Apple silicon.
Inside the shell:

```bash
chmod +x ~/bin/strix
docker build --pull=false -t app ~/target/source
docker network create --internal targets
docker run -d --name app --network targets app
export STRIX_LLM=openrouter/<model> LLM_API_KEY=proxy-managed
export STRIX_IMAGE=ghcr.io/usestrix/strix-sandbox:1.3.0
export STRIX_TELEMETRY=0 STRIX_NO_UPDATE_CHECK=1 LITELLM_LOCAL_MODEL_COST_MAP=True
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
# Strix starts its tool container on the default network; join it to the target's.
( until c=$(docker ps --format '{{.ID}} {{.Image}}' | awk '$2 ~ /strix-sandbox/ {print $1; exit}'); [ -n "$c" ]; do sleep 1; done
  docker network connect targets "$c" ) &
cd ~/out && ~/bin/strix -n -m quick --max-budget-usd 2 \
  -t http://app:8000 -t ~/target/source
```

Use the target's container name in the URL: Strix rewrites `localhost` to an
address that does not reach the VM. Strix exits with status 2 when it reports
findings. Its results land in `~/out/strix_runs/`; `export` them and review
the proofs before acting on them.

The tool container stays on the default network as well, so it can reach every
allowed host. Strix's agents may install the target's dependencies through any
registry you allowed. Its browser, out-of-band callback servers and update checks
try hosts outside the profile, which are refused.

## Limits

- Containers have no CPU limit and share one memory limit.
- The policy log does not say which container sent a request.
- Which network a container joins is your choice; the wrapper does not enforce
  internal networks.
- There is no gVisor layer. The VM remains the isolation boundary, as for every
  other workload process.
