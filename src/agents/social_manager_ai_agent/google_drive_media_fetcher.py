# src/clients/google/google_drive_media_fetcher.py
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Assuming google_drive_client.py is in the same directory or accessible via PYTHONPATH
# If your google_drive_client.py is in src/clients/google/, this import is correct.
from src.clients.google.google_drive_client import GoogleDriveClient

class GoogleDriveMediaFetcher:
    """
    A client to fetch image and video files from a specified Google Drive folder.
    It utilizes the GoogleDriveClient for underlying Drive API interactions.
    """

    # Common MIME types for images and videos
    IMAGE_MIME_TYPES = [
        'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp',
        'image/tiff', 'image/svg+xml'
    ]
    VIDEO_MIME_TYPES = [
        'video/mp4', 'video/x-msvideo', 'video/quicktime', 'video/x-flv',
        'video/webm', 'video/mpeg', 'video/3gpp'
    ]

    SUPPORTED_MIME_TYPES = IMAGE_MIME_TYPES + VIDEO_MIME_TYPES

    def __init__(self, google_drive_client: GoogleDriveClient, folder_id: str):
        """
        Initializes the GoogleDriveMediaFetcher.

        Args:
            google_drive_client (GoogleDriveClient): An authenticated instance of GoogleDriveClient.
            folder_id (str): The ID of the Google Drive folder to monitor for media files.
                             You can find this in the Google Drive URL:
                             e.g., https://drive.google.com/drive/folders/THIS_IS_YOUR_FOLDER_ID
        """
        if not isinstance(google_drive_client, GoogleDriveClient):
            raise TypeError("google_drive_client must be an instance of GoogleDriveClient.")
        if not google_drive_client.service:
            print("Warning: GoogleDriveClient is not authenticated. Media fetching may fail.")

        self.drive_client = google_drive_client
        self.folder_id = folder_id
        print(f"GoogleDriveMediaFetcher initialized for folder ID: {self.folder_id}")


    def _is_media_file(self, mime_type: str) -> bool:
        """Helper to check if a mime type is a supported image or video type."""
        return mime_type in self.SUPPORTED_MIME_TYPES

    def list_media_files(self, query_string: Optional[str] = None) -> List[Dict]:
        """
        Lists image and video files within the configured Google Drive folder.

        Args:
            query_string (str, optional): Additional Google Drive API search query string
                                          (e.g., "name contains 'vacation'").

        Returns:
            list: A list of dictionaries, each representing a media file
                  (e.g., {'id': 'file_id', 'name': 'File Name', 'mimeType': 'image/jpeg', 'modifiedTime': 'ISO-string'}).
                  Returns an empty list if no files or an error occurs.
        """
        print(f"Listing media files in folder '{self.folder_id}'...")

        # Build the MIME type query part
        mime_type_queries = []
        for mt in self.SUPPORTED_MIME_TYPES:
            mime_type_queries.append(f"mimeType = '{mt}'")

        # Combine with folder ID and trash filter
        base_query = f"'{self.folder_id}' in parents and trashed = false and ({' or '.join(mime_type_queries)})"

        if query_string:
            final_query = f"{base_query} and ({query_string})"
        else:
            final_query = base_query

        # The underlying list_files_in_folder handles the actual API call
        # It already filters by 'q' (query) and includes fields 'id, name, mimeType, modifiedTime'
        # We don't need to pass file_extensions explicitly if we construct the query like this.
        media_files = self.drive_client.list_files_in_folder(
            folder_id=self.folder_id,
            query_string=final_query # Pass the combined query
        )

        # A final filter to ensure only supported media types (redundant if query is perfect but safer)
        filtered_media = [file for file in media_files if self._is_media_file(file.get('mimeType', ''))]

        print(f"Found {len(filtered_media)} image/video files in folder '{self.folder_id}'.")
        return filtered_media

    def fetch_new_media_files(self,
                              destination_dir: str,
                              last_fetch_time: Optional[datetime] = None,
                              query_string: Optional[str] = None) -> List[Dict]:
        """
        Fetches new or updated media files from the configured Google Drive folder
        since the last fetch time. Downloads them to the specified directory.

        Args:
            destination_dir (str): The local directory to save downloaded files.
            last_fetch_time (datetime, optional): The datetime of the last successful fetch.
                                                  Only files modified after this time will be considered "new".
            query_string (str, optional): Additional Google Drive API search query string.

        Returns:
            list: A list of dictionaries for successfully downloaded new media files,
                  each including 'local_path' indicating where it was saved.
        """
        print(f"Fetching new media files to '{destination_dir}'...")
        os.makedirs(destination_dir, exist_ok=True)

        all_media_files = self.list_media_files(query_string=query_string)
        new_media_to_download = []

        for file in all_media_files:
            file_id = file['id']
            file_name = file['name']
            modified_time_str = file.get('modifiedTime')

            if modified_time_str:
                # Parse ISO 8601 string to datetime object
                # Google Drive's modifiedTime is typically in UTC and ends with 'Z' (Zulu time)
                modified_time = datetime.fromisoformat(modified_time_str.replace('Z', '+00:00'))

                # Check if file is new/modified since last fetch
                if last_fetch_time and modified_time <= last_fetch_time:
                    print(f"  Skipping '{file_name}' (ID: {file_id}) - not new or modified since last fetch.")
                    continue

            # Construct a safe local path for download
            local_file_path = os.path.join(destination_dir, file_name)

            # Check for name collisions and append a number if file already exists locally
            counter = 1
            original_local_file_path = local_file_path
            while os.path.exists(local_file_path):
                name_parts = os.path.splitext(original_local_file_path)
                local_file_path = f"{name_parts[0]}_{counter}{name_parts[1]}"
                counter += 1

            print(f"  Downloading '{file_name}' (ID: {file_id}) to '{local_file_path}'...")
            if self.drive_client.download_file(file_id, local_file_path):
                file['local_path'] = local_file_path
                new_media_to_download.append(file)
            else:
                print(f"  Failed to download '{file_name}' (ID: {file_id}).")

        print(f"Successfully fetched {len(new_media_to_download)} new media files.")
        return new_media_to_download

# --- Example Usage (for testing GoogleDriveMediaFetcher) ---
if __name__ == "__main__":
    # Ensure your .env and client_secrets.json are set up for Google Drive API.
    # The GOOGLE_DRIVE_SCOPES in your .env must include at least 'https://www.googleapis.com/auth/drive.readonly'
    # or 'https://www.googleapis.com/auth/drive'.

    # 1. Initialize GoogleDriveClient (this handles authentication)
    drive_client = GoogleDriveClient()

    if drive_client.service:
        # 2. IMPORTANT: REPLACE THIS WITH YOUR ACTUAL GOOGLE DRIVE FOLDER ID
        # Example: https://drive.google.com/drive/folders/1aBcDeFgHiJkLmNoPqRsTuVwXyZ <-- This part is the ID
        MEDIA_FOLDER_ID = os.getenv("GOOGLE_DRIVE_MEDIA_FOLDER_ID") # Get from .env for production

        if not MEDIA_FOLDER_ID or MEDIA_FOLDER_ID == "YOUR_GOOGLE_DRIVE_MEDIA_FOLDER_ID":
            print("\n!!! WARNING !!!")
            print("Please set the 'GOOGLE_DRIVE_MEDIA_FOLDER_ID' environment variable in your .env file.")
            print("You can find this in the URL when you open the folder in your browser.")
            print("Example: https://drive.google.com/drive/folders/1aBcDeFgHiJkLmNoPqRsTuVwXyZ")
            exit()

        # 3. Initialize GoogleDriveMediaFetcher
        media_fetcher = GoogleDriveMediaFetcher(drive_client, MEDIA_FOLDER_ID)

        # 4. Define a directory for downloads
        download_destination = "downloaded_media_files"
        os.makedirs(download_destination, exist_ok=True) # Ensure directory exists

        # --- Test Case 1: List all media files ---
        print("\n--- Listing ALL media files ---")
        all_media = media_fetcher.list_media_files(query_string="name contains 'image' or name contains 'video'")
        if all_media:
            for media in all_media:
                print(f"  Found: {media['name']} (ID: {media['id']}, Type: {media['mimeType']}, Modified: {media['modifiedTime']})")
        else:
            print("  No media files found in the folder.")

        # --- Test Case 2: Fetch new media files (simulate subsequent run) ---
        print("\n--- Fetching NEW media files (e.g., since yesterday) ---")
        # To test, upload a new image/video to your specified Google Drive folder,
        # then run this script.

        # Get current time (for simulation of 'last fetch time')
        # For a real application, you'd load this from a persistent store (e.g., a database, a file)
        # For demo, let's simulate fetching anything modified in the last 24 hours.
        one_day_ago = datetime.now() - timedelta(days=1)
        print(f"Looking for files modified after: {one_day_ago}")

        newly_downloaded_media = media_fetcher.fetch_new_media_files(
            destination_dir=download_destination,
            last_fetch_time=one_day_ago,
            query_string="name contains 'test'" # Optional additional filter
        )

        if newly_downloaded_media:
            print(f"\nDownloaded {len(newly_downloaded_media)} new media files:")
            for media in newly_downloaded_media:
                print(f"  - '{media['name']}' saved to '{media['local_path']}'")
        else:
            print("\nNo new media files to download.")

    else:
        print("GoogleDriveClient service is not available. Please check your authentication.")