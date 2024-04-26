import argparse
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

import requests

__version__ = '1.0.0'

def get_version():
    return __version__

logging.basicConfig(level=logging.INFO, format=' %(message)s')

class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        logging.error(message)
        self.print_help()
        sys.exit(2)

def parse_arguments():
    """Parse command line arguments for the script."""
    parser = CustomArgumentParser(
        description='This script downloads integration files for a specified Kibana version.'
    )
    parser.add_argument('-v', '--version', required=True, help='Specify the Kibana version. Example: -v 8.11.1')
    return parser.parse_args().version

def create_dockerfile(base_dir):
    """Create a Dockerfile with predefined content in the base directory."""
    dockerfile_content = (
        "FROM docker.elastic.co/package-registry/package-registry:main\n"
        "COPY ../integrations/ /packages/package-registry/\n"
        "WORKDIR /package-registry\n"
    )
    dockerfile_path = base_dir / 'Dockerfile'
    with dockerfile_path.open('w') as dockerfile:
        dockerfile.write(dockerfile_content)
    logging.info(f"Dockerfile created at {dockerfile_path}")

def copy_and_modify_readme(base_dir, kibana_version):
    """Copy the 'instructions.md' file from the support directory, rename it to 'readme.md', and modify its contents."""
    source_path = Path(__file__).parent / 'support' / 'instructions.md'
    destination_path = base_dir / 'readme.md'
    
    # Copy and rename the file
    shutil.copy(source_path, destination_path)
    logging.info(f"Create 'readme.md' at {destination_path}")
    
    # Modify the content of the readme file
    with open(destination_path, 'r+') as file:
        content = file.read()
        modified_content = content.replace('{version}', kibana_version)
        file.seek(0)  # Move the cursor to the beginning of the file
        file.write(modified_content)
        file.truncate()  # Remove any remaining part of the old content

def create_builds_directory(kibana_version):
    """Create a timestamped builds directory based on the Kibana version."""
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    folder_name = f"{timestamp}-{kibana_version}"
    base_dir = Path(__file__).parent / 'builds' / folder_name
    base_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / 'integrations').mkdir(exist_ok=True)
    return base_dir, base_dir / 'integrations'

def fetch_and_count_files(kibana_version):
    """Fetch the list of packages and count the total files to download."""
    url = f"https://epr.elastic.co/search?kibana.version={kibana_version}"
    response = requests.get(url)
    response.raise_for_status()
    packages = response.json()
    return 2 * len(packages)  # Each package has a file and a signature file


def verify_downloaded_files(integrations_dir, expected_files):
    """Verify that all expected files have been downloaded."""

    print('..... verify all downloads .... ')
    downloaded_files = set(integrations_dir.iterdir())
    missing_files = [file.name for file in expected_files if file not in downloaded_files]
    if not missing_files:
        logging.info("All files have been successfully downloaded and verified.")
    else:
        logging.warning(f"Missing files: {missing_files}")

def download_file(url, path):
    """Download a file from a URL to a specified path."""
    response = requests.get(url)
    response.raise_for_status()
    with path.open('wb') as file:
        file.write(response.content)
    return path

def fetch_and_download_files(kibana_version, integrations_dir, total_files):
    """Fetch and download files based on the Kibana version, logging the total files count."""
    url = f"https://epr.elastic.co/search?kibana.version={kibana_version}"
    response = requests.get(url)
    response.raise_for_status()
    packages = response.json()
    
    downloaded_count = 0
    expected_files = []

    for package in packages:
        base_url = "https://epr.elastic.co"
        file_path = integrations_dir / Path(package['download']).name
        signature_path = integrations_dir / Path(package['signature_path']).name
        
        expected_files.append(file_path)
        expected_files.append(signature_path)

        download_file(base_url + package['download'], file_path)
        downloaded_count += 1
        logging.info(f"Downloaded: ({downloaded_count} of {total_files}) {file_path.name}")

        download_file(base_url + package['signature_path'], signature_path)
        downloaded_count += 1
        logging.info(f"Downloaded: ({downloaded_count} of {total_files}) {signature_path.name}")

    verify_downloaded_files(integrations_dir, expected_files)


def main():
    kibana_version = parse_arguments()
    logging.info(f".............................................................")
    logging.info(f"Starting the script with Kibana version: {kibana_version}")
    
    base_dir, integrations_dir = create_builds_directory(kibana_version)
    total_files = fetch_and_count_files(kibana_version)
    logging.info(f"Total files to download: {total_files}")
    logging.info(f".............................................................")
    
    fetch_and_download_files(kibana_version, integrations_dir, total_files)
    create_dockerfile(base_dir)
    copy_and_modify_readme(base_dir, kibana_version)
    
    # Success message
    logging.info(f"Script completed successfully!")

    # Display a fancy ending message with the location of the readme.md
    readme_location = base_dir / 'readme.md'
    print("\n" + "*"*40)
    print("\033[1mEPR Build Completed\033[0m")
    print(f"Refer to the documentation in: \033[1m{readme_location}\033[0m")
    print("*"*40 + "\n")


if __name__ == "__main__":
    main()