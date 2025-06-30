import os
from dotenv import load_dotenv
from rmapy.api import Client
from rmapy.document import Document
from rmapy.folder import Folder

# --- Configuration ---
# Load environment variables from .env file
load_dotenv()

# Get the reMarkable one-time code from environment variable
REMARKABLE_ONE_TIME_CODE = os.getenv("REMARKABLE_ONE_TIME_CODE")

# --- Initialize rmapy Client ---
rmapi = Client()

def authenticate_remarkable():
    """
    Authenticates with the reMarkable Cloud API.
    If not already authenticated, it uses the one-time code to register a device.
    It also ensures the user token is renewed.
    """
    if not rmapi.is_auth():
        if not REMARKABLE_ONE_TIME_CODE:
            print("Error: REMARKABLE_ONE_TIME_CODE not found in your .env file or environment variables.")
            print("Please generate a code from https://my.remarkable.com/device/desktop/connect and add it to your .env file.")
            exit(1) # Exit if no code is provided for initial auth
        
        print(f"Attempting to register device with one-time code...")
        try:
            rmapi.register_device('hmivjxcv')
            print("Device registered successfully! Authentication tokens saved.")
        except Exception as e:
            print(f"Error registering device: {e}")
            # print("Please double-check your one-time code and ensure it hasn't expired or been used.")
            exit(1) # Exit on authentication failure
    else:
        print("Already authenticated with reMarkable Cloud.")
    
    # Always renew the user token for the session to ensure it's fresh
    try:
        rmapi.renew_token()
        print("reMarkable user token renewed.")
    except Exception as e:
        print(f"Error renewing user token: {e}")
        print("You might need to re-authenticate by deleting your rmapi config (~/.rmapi) or updating your one-time code.")
        exit(1) # Exit if token renewal fails

def list_remarkable_items():
    """
    Lists all documents and folders from the reMarkable Cloud.
    """
    print("\n--- Listing reMarkable Cloud Items ---")
    try:
        # Get all metadata items (documents and folders)
        meta_items = rmapi.get_meta_items()

        if not meta_items:
            print("No items found in your reMarkable Cloud.")
            return

        folders = [item for item in meta_items if isinstance(item, Folder)]
        documents = [item for item in meta_items if isinstance(item, Document)]

        print("\nFolders:")
        if folders:
            for folder in folders:
                print(f"- [Folder] Name: {folder.VisibleName} (ID: {folder.ID})")
        else:
            print("  No folders found.")

        print("\nDocuments:")
        if documents:
            for doc in documents:
                # You might want to filter by type later if you only care about notebooks
                print(f"- [Document] Name: {doc.VisibleName} (ID: {doc.ID})")
        else:
            print("  No documents found.")

        return meta_items

    except Exception as e:
        print(f"Error listing reMarkable items: {e}")
        return None

# --- Main execution ---
if __name__ == "__main__":
    authenticate_remarkable()
    # all_items = list_remarkable_items()
    # if all_items:
    #     print(f"\nSuccessfully retrieved {len(all_items)} items from reMarkable Cloud.")
    # else:
    #     print("\nFailed to retrieve items.")

