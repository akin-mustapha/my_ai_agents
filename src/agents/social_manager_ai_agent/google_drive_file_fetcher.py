# src/clients/google/google_drive_file_fetcher.py (rename your file)
import os
from datetime import datetime, timedelta, timezone # Import timezone here
from typing import List, Dict, Optional, Union

# Assuming google_drive_client.py is in the same directory or accessible via PYTHONPATH
from src.clients.google.google_drive_client import GoogleDriveClient

class GoogleDriveFileFetcher:
    """
    A client to fetch various file types (media, documents, code, etc.)
    from a specified Google Drive folder and store them in type-specific subfolders.
    It utilizes the GoogleDriveClient for underlying Drive API interactions.
    """

    # Define a comprehensive list of common MIME types and map them to friendly folder names
    FILE_TYPE_MAPPING = {
        # Images
        'image/jpeg': 'images', 'image/png': 'images', 'image/gif': 'images',
        'image/bmp': 'images', 'image/webp': 'images', 'image/tiff': 'images',
        'image/svg+xml': 'images',

        # Videos
        'video/mp4': 'videos', 'video/x-msvideo': 'videos', 'video/quicktime': 'videos',
        'video/x-flv': 'videos', 'video/webm': 'videos', 'video/mpeg': 'videos',
        'video/3gpp': 'videos', 'video/x-matroska': 'videos', # .mkv

        # Documents
        'application/pdf': 'pdf',
        'application/msword': 'word', # .doc
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'word', # .docx
        'application/vnd.ms-excel': 'excel', # .xls
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'excel', # .xlsx
        'application/vnd.ms-powerpoint': 'powerpoint', # .ppt
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'powerpoint', # .pptx
        'text/plain': 'text',
        'text/html': 'html',
        'application/rtf': 'rtf',

        # Code/Scripts
        'text/x-python': 'python',
        'application/javascript': 'javascript', 'text/javascript': 'javascript',
        'text/css': 'css',
        'application/json': 'json',
        'text/xml': 'xml', 'application/xml': 'xml',
        'text/csv': 'csv',

        # Archives
        'application/zip': 'archives',
        'application/x-rar-compressed': 'archives',
        'application/x-7z-compressed': 'archives',

        # Spreadsheets (OpenDocument)
        'application/vnd.oasis.opendocument.spreadsheet': 'opendoc_spreadsheet',
        'application/vnd.oasis.opendocument.text': 'opendoc_text',
        'application/vnd.oasis.opendocument.presentation': 'opendoc_presentation',
    }

    # Extract all supported MIME types from the mapping for query construction
    SUPPORTED_MIME_TYPES = list(FILE_TYPE_MAPPING.keys())

    def __init__(self, google_drive_client: GoogleDriveClient, folder_id: str):
        """
        Initializes the GoogleDriveFileFetcher.

        Args:
            google_drive_client (GoogleDriveClient): An authenticated instance of GoogleDriveClient.
            folder_id (str): The ID of the Google Drive folder to monitor for files.
                             You can find this in the Google Drive URL:
                             e.g., https://drive.google.com/drive/folders/THIS_IS_YOUR_FOLDER_ID
        """
        if not isinstance(google_drive_client, GoogleDriveClient):
            raise TypeError("google_drive_client must be an instance of GoogleDriveClient.")
        if not google_drive_client.service:
            print("Warning: GoogleDriveClient is not authenticated. File fetching may fail.")

        self.drive_client = google_drive_client
        self.folder_id = folder_id
        print(f"GoogleDriveFileFetcher initialized for folder ID: {self.folder_id}")

    def _get_folder_name_for_mime_type(self, mime_type: str) -> str:
        """
        Determines the appropriate subfolder name based on the file's MIME type.
        Defaults to 'other' if the MIME type is not explicitly mapped.
        """
        return self.FILE_TYPE_MAPPING.get(mime_type, 'other')

    def list_files(self, query_string: Optional[str] = None) -> List[Dict]:
        """
        Lists all supported file types within the configured Google Drive folder.

        Args:
            query_string (str, optional): Additional Google Drive API search query string
                                          (e.g., "name contains 'report'").

        Returns:
            list: A list of dictionaries, each representing a file
                  (e.g., {'id': 'file_id', 'name': 'File Name', 'mimeType': 'image/jpeg', 'modifiedTime': 'ISO-string'}).
                  Returns an empty list if no files or an error occurs.
        """
        print(f"Listing supported files in folder '{self.folder_id}'...")

        # Build the MIME type query part for all supported types
        mime_type_queries = [f"mimeType = '{mt}'" for mt in self.SUPPORTED_MIME_TYPES]

        # Combine with folder ID and trash filter
        base_query = f"'{self.folder_id}' in parents and trashed = false and ({' or '.join(mime_type_queries)})"

        if query_string:
            final_query = f"{base_query} and ({query_string})"
        else:
            final_query = base_query

        # The underlying list_files_in_folder handles the actual API call
        files_list = self.drive_client.list_files_in_folder(
            folder_id=self.folder_id,
            query_string=final_query # Pass the combined query
        )

        print(f"Found {len(files_list)} supported files in folder '{self.folder_id}'.")
        return files_list

    def fetch_new_files(self,
                        destination_base_dir: str,
                        last_fetch_time: Optional[datetime] = None,
                        query_string: Optional[str] = None) -> List[Dict]:
        """
        Fetches new or updated files from the configured Google Drive folder
        since the last fetch time. Downloads them to type-specific subdirectories
        within the specified base directory.

        Args:
            destination_base_dir (str): The base local directory to save downloaded files.
                                        Subfolders like 'pdf', 'images', 'word' will be created here.
            last_fetch_time (datetime, optional): The datetime of the last successful fetch.
                                                  Only files modified after this time will be considered "new".
            query_string (str, optional): Additional Google Drive API search query string.

        Returns:
            list: A list of dictionaries for successfully downloaded new files,
                  each including 'local_path' indicating where it was saved.
        """
        print(f"Fetching new files to base directory '{destination_base_dir}'...")
        os.makedirs(destination_base_dir, exist_ok=True)

        all_supported_files = self.list_files(query_string=query_string)
        new_files_to_download = []

        for file in all_supported_files:
            file_id = file['id']
            file_name = file['name']
            mime_type = file.get('mimeType', 'application/octet-stream') # Default to generic binary
            modified_time_str = file.get('modifiedTime')

            if modified_time_str:
                # Parse ISO 8601 string to datetime object
                modified_time = datetime.fromisoformat(modified_time_str.replace('Z', '+00:00'))

                # Check if file is new/modified since last fetch
                if last_fetch_time and modified_time <= last_fetch_time:
                    print(f"  Skipping '{file_name}' (ID: {file_id}) - not new or modified since last fetch.")
                    continue

            # Determine the subfolder based on MIME type
            subfolder_name = self._get_folder_name_for_mime_type(mime_type)
            destination_sub_dir = os.path.join(destination_base_dir, subfolder_name)
            os.makedirs(destination_sub_dir, exist_ok=True) # Create subfolder if it doesn't exist

            # Construct a safe local path for download
            local_file_path = os.path.join(destination_sub_dir, file_name)

            # Check for name collisions and append a number if file already exists locally
            counter = 1
            original_local_file_path = local_file_path
            while os.path.exists(local_file_path):
                name_parts = os.path.splitext(original_local_file_path)
                local_file_path = f"{name_parts[0]}_{counter}{name_parts[1]}"
                counter += 1

            print(f"  Downloading '{file_name}' (ID: {file_id}, Type: {mime_type}) to '{local_file_path}'...")
            if self.drive_client.download_file(file_id, local_file_path):
                file['local_path'] = local_file_path
                new_files_to_download.append(file)
            else:
                print(f"  Failed to download '{file_name}' (ID: {file_id}).")

        print(f"Successfully fetched {len(new_files_to_download)} new files.")
        return new_files_to_download

# --- Example Usage (for testing GoogleDriveFileFetcher) ---
if __name__ == "__main__":
    # Ensure your .env and client_secrets.json are set up for Google Drive API.
    # The GOOGLE_DRIVE_SCOPES in your .env must include at least 'https://www.googleapis.com/auth/drive.readonly'
    # or 'https://www.googleapis.com/auth/drive'.

    # 1. Initialize GoogleDriveClient (this handles authentication)
    drive_client = GoogleDriveClient()

    if drive_client.service:
        # 2. IMPORTANT: REPLACE THIS WITH YOUR ACTUAL GOOGLE DRIVE FOLDER ID
        # Example: https://drive.google.com/drive/folders/1aBcDeFgHiJkLmNoPqRsTuVwXyZ <-- This part is the ID
        # For production, get from .env
        GOOGLE_DRIVE_DATA_FOLDER_ID = os.getenv("GOOGLE_DRIVE_DATA_FOLDER_ID", "YOUR_GOOGLE_DRIVE_DATA_FOLDER_ID")

        if GOOGLE_DRIVE_DATA_FOLDER_ID == "YOUR_GOOGLE_DRIVE_DATA_FOLDER_ID":
            print("\n!!! WARNING !!!")
            print("Please set the 'GOOGLE_DRIVE_DATA_FOLDER_ID' environment variable in your .env file.")
            print("You can find this in the URL when you open the folder in your browser.")
            print("Example: https://drive.google.com/drive/folders/1aBcDeFgHiJkLmNoPqRsTuVwXyZ <-- This part is the ID")
            exit()

        # 3. Initialize GoogleDriveFileFetcher
        file_fetcher = GoogleDriveFileFetcher(drive_client, GOOGLE_DRIVE_DATA_FOLDER_ID)

        # 4. Define a base directory for downloads
        download_base_destination = "downloaded_drive_files"
        os.makedirs(download_base_destination, exist_ok=True) # Ensure base directory exists

        # --- Test Case 1: List all supported files ---
        print("\n--- Listing ALL supported files in the folder ---")
        all_files = file_fetcher.list_files(query_string="name contains 'report' or name contains 'photo'")
        if all_files:
            for file_info in all_files:
                print(f"  Found: {file_info['name']} (ID: {file_info['id']}, Type: {file_info['mimeType']}, Modified: {file_info['modifiedTime']})")
        else:
            print("  No supported files found in the specified folder.")

        # --- Test Case 2: Fetch new files (simulate subsequent run) ---
        print("\n--- Fetching NEW files (e.g., since 2 days ago) ---")
        # To test, upload new files (PDFs, images, Excel, etc.) to your specified Google Drive folder,
        # then run this script.

        # Simulate 'last fetch time' from a previous run
        # For a real application, you'd load this from a persistent store (e.g., a database, a file)
        two_days_ago = datetime.now(timezone.utc) - timedelta(days=2) # CORRECTED: Made timezone-aware
        print(f"Looking for files modified after: {two_days_ago}")

        newly_downloaded_files = file_fetcher.fetch_new_files(
            destination_base_dir=download_base_destination,
            last_fetch_time=two_days_ago
        )

        if newly_downloaded_files:
            print(f"\nDownloaded {len(newly_downloaded_files)} new files:")
            for file_info in newly_downloaded_files:
                print(f"  - '{file_info['name']}' (Type: {file_info['mimeType']}) saved to '{file_info['local_path']}'")
        else:
            print("\nNo new files to download.")

    else:
        print("GoogleDriveClient service is not available. Please check your authentication.")