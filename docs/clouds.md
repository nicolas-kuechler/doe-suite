# Clouds

Doe supports multiple _clouds_.
A cloud refers to an environment in which servers are set up and configured.
So far, we support AWS (aws) and Leonhard (leonhard, ETH compute cluster).

## Supported clouds

| Cloud    | Description                    |
|----------|--------------------------------|
| aws      | Amazon Web Services            |
| leonhard | Leonhard (ETH compute cluster) |

## Migration guide

After the transition to support for clouds, some things must be changed:

### Setup roles
In `does_config/roles/**`, rename `main.yml` to `aws.yml`

