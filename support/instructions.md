## Build a Custom EPR Docker Image for a Specific Kibana Version

Requirements:
1. Docker

This directory was created by running the `build.py` script to extract EPR assets for Kibana Version {version}.

The directory contains an `/integrations` directory with all of the EPR assets and a `Dockerfile` to build the Docker image.

## Build the Image

From this directory, run the Docker build command with an appropriate tag (-t) and platform (linux/amd64,linux/arm64,linux/arm/v7).

```bash
docker build . -t elastic-epr/custom:v{version}   # This will build to your host machine

docker build . -t elastic-epr/custom:v{version} --platform=linux/amd64/v3 # Example of a specific platform

docker build . -t elastic-epr/custom:v{version} --platform=linux/amd64,linux/arm64,linux/arm/v7
```

Run and Test Locally

```bash
docker run -it --name epr-{version}  -p 8080:8080 elastic-epr/custom:v{version}
```

## Deploy

Refer to [Install Fleet Agents - Air-gapped environments](https://www.elastic.co/guide/en/fleet/current/air-gapped.html) for more detailed information.

1. Save the custom EPR image as a tar file

```bash
docker save -o package-registry-custom-{version}.tar elastic-epr/custom:v{version}
```

2. Transfer the image to the air-gapped environment and load it:

```bash
docker load -i package-registry-custom-{version}.tar
```

3. Run the Elastic Package Registry:

```bash
# Run in the terminal
docker run -it -p 8080:8080 elastic-epr/custom:v{version}

# Run in the background
docker run -d -p 8080:8080 elastic-epr/custom:v{version}
```

4. Connect Kibana to your hosted Elastic Package Registry

Use the `xpack.fleet.registryUrl` property in the `kibana.yml` to set the URL of your hosted package registry. For example:

```bash
xpack.fleet.registryUrl: "http://localhost:8080"
```

Refer to Elastic Docs [TLS configuration of the Elastic Package Registry](https://www.elastic.co/guide/en/fleet/current/air-gapped.html#:~:text=configuration%20of%20the%20Elastic-,Package,-Registry) for information on setting up for secure HTTPS port using TLS (Not tested).