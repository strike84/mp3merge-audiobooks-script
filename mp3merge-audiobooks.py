import subprocess
import os
import requests
import logging
import json

# Configure logging
logging.basicConfig(filename='audiobook_merge.log', level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

# State file to keep track of processed books
STATE_FILE = 'processed_books.json'

def load_processed_books():
    """
    Load the state of processed books from a JSON file.
    
    Returns:
        dict: A dictionary containing the processed book directories.
    """
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}

def save_processed_books(processed_books):
    """
    Save the state of processed books to a JSON file.
    
    Args:
        processed_books (dict): The dictionary containing the processed book directories.
    """
    with open(STATE_FILE, 'w', encoding='utf-8') as file:
        json.dump(processed_books, file, indent=4)

def scan_for_mp3_books(base_path, processed_books):
    """
    Scan the base directory for audiobook files, check for new books, and merge their parts.

    Args:
        base_path (str): The root directory to scan for audiobooks.
        processed_books (dict): Dictionary containing already processed books.
    """
    base_path = os.path.abspath(base_path)
    for root, dirs, files in os.walk(base_path, topdown=True):
        book_title = os.path.basename(root)  # Get the book title (the name of the current directory)

        # Skip already processed books
        if book_title in processed_books:
            continue

        # Check for subdirectories like CD1, CD2, ...
        cd_folders = [os.path.join(root, d) for d in dirs if d.lower().startswith('cd')]
        if cd_folders:
            # Gather all mp3 files from CD folders
            mp3_files = []
            for cd_folder in cd_folders:
                for root_cd, dirs_cd, files_cd in os.walk(cd_folder):
                    mp3_files.extend([os.path.join(root_cd, file) for file in files_cd if file.endswith('.mp3')])
            if mp3_files:
                logging.info(f"Found book with CD folders: {book_title} containing {len(mp3_files)} parts")
                if merge_mp3_files(mp3_files, root, book_title):
                    logging.info(f"Merging successful for book: {book_title}. Removing original files...")
                    remove_original_files(mp3_files)
                    processed_books[book_title] = True
                else:
                    logging.warning(f"Merging was not successful for book: {book_title}. Original files are kept.")
            dirs[:] = []  # Skip deeper directories below CD folders
        else:
            # Process MP3 files directly within book directories
            mp3_files = [os.path.join(root, file) for file in files if file.endswith('.mp3')]
            if len(mp3_files) > 1:
                logging.info(f"Found book with {len(mp3_files)} parts: {book_title}")
                if merge_mp3_files(mp3_files, root, book_title):
                    logging.info(f"Merging successful for book: {book_title}. Removing original files...")
                    remove_original_files(mp3_files)
                    processed_books[book_title] = True
                else:
                    logging.warning(f"Merging was not successful for book: {book_title}. Original files are kept.")

def merge_mp3_files(mp3_files, output_folder, book_title):
    """
    Merge multiple MP3 files into a single file using FFmpeg.

    Args:
        mp3_files (list): List of MP3 file paths to merge.
        output_folder (str): The directory to save the merged file.
        book_title (str): The title of the book (used for naming the output file).
    
    Returns:
        bool: True if merging was successful, False otherwise.
    """
    filelist_path = os.path.join(output_folder, "filelist.txt")
    output_file = os.path.join(output_folder, f"{book_title}-merged.mp3")
    generate_filelist_file(mp3_files, filelist_path)

    try:
        subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', filelist_path, '-c', 'copy', output_file], check=True)
        logging.info(f"Merge successful: {output_file}")
        return True
    except subprocess.CalledProcessError as error:
        logging.error(f"Failed to merge {book_title}: {error}")
        return False
    finally:
        os.remove(filelist_path)

def generate_filelist_file(mp3_files, filelist_path):
    """
    Generate a file list for FFmpeg from a list of MP3 file paths.

    Args:
        mp3_files (list): List of MP3 file paths to merge.
        filelist_path (str): The path to save the file list.
    """
    with open(filelist_path, 'w', encoding='utf-8') as filelist:
        for mp3_file in mp3_files:
            ffmpeg_path = mp3_file.replace('\\', '/')
            filelist.write(f"file '{ffmpeg_path}'\n")

def remove_original_files(mp3_files):
    """
    Remove original individual MP3 files after a successful merge.

    Args:
        mp3_files (list): List of MP3 file paths to delete.
    """
    for file_path in mp3_files:
        try:
            os.remove(file_path)
            logging.info(f"Removed original file: {file_path}")
        except Exception as e:
            logging.exception(f"Failed to remove file {file_path}: {e}")

def scan_audiobookshelf_library(base_url, library_id, token):
    """
    Trigger a library scan in Audiobookshelf via the API.

    Args:
        base_url (str): The base URL of the Audiobookshelf server.
        library_id (str): The ID of the library to scan.
        token (str): The API token for authentication.
    """
    api_endpoint = f"{base_url}/api/libraries/{library_id}/scan"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.post(api_endpoint, headers=headers)
        if response.status_code == 200:
            logging.info("Library scan initiated successfully.")
        else:
            logging.error(f"Failed to initiate library scan: {response.status_code} - {response.text}")
    except Exception as e:
        logging.exception(f"Error initiating library scan: {e}")

if __name__ == '__main__':
    # Set your paths and credentials
    base_path = r'Z:\test\mp3merge'  # Update to your audiobooks directory
    base_url = 'http://your.audiobookshelf.host:port'  # Update with your Audiobookshelf server URL
    library_id = 'your_library_id'  # Update with your specific library ID
    token = 'your_api_token'  # Update with your actual API token

    # Load processed books state
    processed_books = load_processed_books()

    # Scan for new books and process them
    scan_for_mp3_books(base_path, processed_books)

    # Save the updated state
    save_processed_books(processed_books)

    # Trigger library scan after all merging is completed
    scan_audiobookshelf_library(base_url, library_id, token)
    logging.info("Audiobookshelf library scan process has been initiated.")
