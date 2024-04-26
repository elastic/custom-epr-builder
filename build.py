import argparse
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    shutil.copy(source_path, destination_path)
    logging.info(f"Created 'readme.md' at {destination_path}")
    with open(destination_path, 'r+') as file:
        content = file.read()
        modified_content = content.replace('{version}', kibana_version)
        file.seek(0)
        file.write(modified_content)
        file.truncate()

def create_builds_directory(kibana_version):
    """Create a timestamped builds directory based on the Kibana version."""
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    folder_name = f"{timestamp}-{kibana_version}"
    base_dir = Path(__file__).parent / 'builds' / folder_name
    base_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / 'integrations').mkdir(exist_ok=True)
    return base_dir, base_dir / 'integrations'

def setup_download_session():
    """Set up a requests session with retry logic."""
    retry_strategy = Retry(
        total=5,  # Total number of retries to allow.
        backoff_factor=1,  # A backoff factor to apply between attempts after the second try.
        status_forcelist=(500, 502, 504),  # A set of HTTP status codes that we should force a retry on.
        method_whitelist=["HEAD", "GET", "OPTIONS"]  # Optional: set methods to retry
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session

def fetch_and_count_files(kibana_version):
    """Fetch the list of packages and count the total files to download based on the Kibana version."""
    url = f"https://epr.elastic.co/search?kibana.version={kibana_version}"
    session = setup_download_session()
    response = session.get(url)
    response.raise_for_status()
    packages = response.json()
    
    # Assuming each package has one main file and one signature file
    total_files = 2 * len(packages)
    return total_files


def download_file(session, url, path):
    """Download a file from a URL to a specified path with a session that has retry logic."""
    try:
        response = session.get(url)
        response.raise_for_status()
        with path.open('wb') as file:
            file.write(response.content)
        return path
    except requests.RequestException as e:
        logging.error(f"Failed to download {url}: {e}")
        return None
    
def verify_downloaded_files(integrations_dir, expected_files):
    """Verify that all expected files have been downloaded."""
    downloaded_files = set(file.name for file in integrations_dir.iterdir())
    missing_files = [file.name for file in expected_files if file.name not in downloaded_files]
    
    if missing_files:
        logging.warning(f"Missing files: {missing_files}")
    else:
        logging.info("All files have been successfully downloaded and verified.")

def fetch_and_download_files(kibana_version, integrations_dir, total_files):
    """Fetch and download files based on the Kibana version, logging the total files count."""
    url = f"https://epr.elastic.co/search?kibana.version={kibana_version}"
    session = setup_download_session()
    response = session.get(url)
    response.raise_for_status()
    packages = response.json()
    
    downloaded_count = 0
    expected_files = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_file = {}
        for pkg in packages:
            base_url = "https://epr.elastic.co"
            file_path = integrations_dir / Path(pkg['download']).name
            signature_path = integrations_dir / Path(pkg['signature_path']).name
            
            expected_files.append(file_path)
            expected_files.append(signature_path)

            future_to_file[executor.submit(download_file, session, base_url + pkg['download'], file_path)] = file_path
            future_to_file[executor.submit(download_file, session, base_url + pkg['signature_path'], signature_path)] = signature_path

        for future in as_completed(future_to_file):
            path = future_to_file[future]
            try:
                result = future.result()
                if result:
                    downloaded_count += 1
                    logging.info(f"Downloaded: ({downloaded_count} of {total_files}) {path.name}")
            except Exception as e:
                logging.error(f"File download failed for {path.name}: {e}")

    verify_downloaded_files(integrations_dir, expected_files)


def main():
    kibana_version = parse_arguments()
    logging.info(".............................................................")
    logging.info(f"Starting the script with Kibana version: {kibana_version}")
    
    base_dir, integrations_dir = create_builds_directory(kibana_version)
    total_files = fetch_and_count_files(kibana_version)  # Ensure this function is defined
    logging.info(f"Total files to download: {total_files}")
    logging.info(".............................................................")
    
    fetch_and_download_files(kibana_version, integrations_dir, total_files)
    create_dockerfile(base_dir)
    copy_and_modify_readme(base_dir, kibana_version)
    
    # Display a fancy ending message with the location of the readme.md
    readme_location = base_dir / 'readme.md'
    print("\n" + "*" * 40)
    print("\033[1mEPR Build Completed\033[0m")
    print(f"Refer to the documentation in: \033[1m{readme_location}\033[0m")
    print("*" * 40 + "\n")
    logging.info("Script completed successfully!")

if __name__ == "__main__":
    main()
