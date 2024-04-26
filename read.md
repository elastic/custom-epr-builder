# Build a Custom EPR Docker Image for a Specific Kibana Version

The `builds.py` script downloads all integrations for a selected Kibana version from `https://epr.elastic.co` and generates a Dockerfile that can be used to build an EPR docker image.

Details on using the image once created can be found at Refer to [Install Fleet Agents - Air-gapped environments](https://www.elastic.co/guide/en/fleet/current/air-gapped.html).

Requirements:

1. Python
2. Docker

# Extract EPR Assets for a Kibana Version

Clone this repo and run the python script `build.py` with the version of Kibana you are targeting:

```python
python build.py -v 8.13.1
```

All EPR Assets will be downloaded into a time stamped folder with the Kibana version in the `/build` directory created at the same location as the build.py script.

The timestamped folder will contain an `/integrations` directory with all of the assets and a `Dockerfile` to build the Docker image.

# Build the Image

Navigate to the time stamped build folder with the Dockerfile and run the Docker build command with an appropriate tag (-t) and platform (linux/amd64,linux/arm64,linux/arm/v7).

```bash
docker build . -t elastic-epr/custom:v8.13.1   # This will build to your host machine

docker build . -t elastic-epr/custom:v8.13.1 --platform=linux/amd64/v3 # Example of a specific platform

docker build . -t elastic-epr/custom:v8.13.1 --platform=linux/amd64,linux/arm64,linux/arm/v7
```

Run and Test Locally

```bash
docker run -it --name epr-8.13.1  -p 8080:8080 elastic-epr/custom:v8.13.1
```

# Deploy

Refer to [Install Fleet Agents - Air-gapped environments](https://www.elastic.co/guide/en/fleet/current/air-gapped.html) for more detailed information.

1. Save the custom EPR image as a tar file

```bash
docker save -o package-registry-custom-8.13.1.tar elastic-epr/custom:v8.13.1
```

2. Transfer the image to the air-gapped environment and load it:

```bash
docker load -i package-registry-custom-8.13.1.tar
```

3. Run the Elastic Package Registry:

```bash
# Run in the terminal
docker run -it -p 8080:8080 elastic-epr/custom:v8.13.1

# Run in the background
docker run -d -p 8080:8080 elastic-epr/custom:v8.13.1
```

4. Connect Kibana to your hosted Elastic Package Registry

Use the `xpack.fleet.registryUrl` property in the `kibana.yml` to set the URL of your hosted package registry. For example:

```bash
xpack.fleet.registryUrl: "http://localhost:8080"
```

Refer to Elastic Docs [TLS configuration of the Elastic Package Registry](https://www.elastic.co/guide/en/fleet/current/air-gapped.html#:~:text=configuration%20of%20the%20Elastic-,Package,-Registry) for information on setting up for secure HTTPS port using TLS (Not tested).