import os
import re
from dotenv import load_dotenv
from src.clients.google.google_gmail_client import GmailClient
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

# --- Configuration ---
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_ATTACHMENTS_DIR = os.path.join(BASE_DIR, "downloaded_remarkable_attachments")
PROCESSED_EMAIL_IDS_LOG = os.path.join(BASE_DIR, "processed_emails.log")

REMARKABLE_SENDER_EMAIL = os.getenv("REMARKABLE_SENDER_EMAIL", "noreply@remarkable.com")
REMARKABLE_SUBJECT_KEYWORD = os.getenv("REMARKABLE_SUBJECT_KEYWORD", "reMarkable Note")

PYTESSERACT_CMD_PATH = os.getenv("PYTESSERACT_CMD_PATH", "/usr/bin/tesseract")
if not os.path.exists(PYTESSERACT_CMD_PATH):
    raise FileNotFoundError(f"Tesseract executable not found at {PYTESSERACT_CMD_PATH}. Please check your installation.")
pytesseract.pytesseract.tesseract_cmd = PYTESSERACT_CMD_PATH

def load_processed_email_ids():
    if not os.path.exists(PROCESSED_EMAIL_IDS_LOG):
        return set()
    with open(PROCESSED_EMAIL_IDS_LOG, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def save_processed_email_id(email_id):
    with open(PROCESSED_EMAIL_IDS_LOG, 'a') as f:
        f.write(email_id + '\n')

def extract_text_from_remarkable_pdf(pdf_path):
    print(f"  Attempting OCR on PDF: {os.path.basename(pdf_path)}")
    try:
        pages = convert_from_path(pdf_path, dpi=300)
        full_text_parts = []
        for i, page in enumerate(pages):
            print(f"    Processing page {i+1}/{len(pages)}...")
            text = pytesseract.image_to_string(page)
            full_text_parts.append(text)
        return "\n".join(full_text_parts)
    except Exception as e:
        print(f"  Error during PDF OCR for {os.path.basename(pdf_path)}: {e}")
        return None

def parse_tasks(text_content):
    print(f"  --- Parsing Tasks (Placeholder) ---")
    print(f"  Received text for parsing:\n{text_content[:300].strip()}...\n")
    tasks = []
    lines = text_content.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("todo:") or re.match(r'^\s*\[\s*\]\s*.+', line):
            task_desc = line.replace("TODO:", "").strip()
            priority = "Medium"
            if "urgent" in line.lower() or "asap" in line.lower():
                priority = "High"
            elif "low priority" in line.lower():
                priority = "Low"
            tasks.append({
                "task": task_desc,
                "priority": priority,
                "source_line": line
            })
    return tasks

def add_tasks_to_calendar(tasks):
    print(f"  --- Adding Tasks to Calendar (Placeholder) ---")
    if tasks:
        for task in tasks:
            print(f"  - Adding task to calendar: '{task.get('task')}' (Priority: {task.get('priority')})")

def main():
    print("--- Starting reMarkable List Prioritizer ---")
    os.makedirs(DOWNLOAD_ATTACHMENTS_DIR, exist_ok=True)
    gmail_client = GmailClient()
    if not gmail_client.service:
        print("Failed to initialize Gmail client. Ensure your OAuth credentials are correct and the file exists.")
        return
    processed_email_ids = load_processed_email_ids()
    print(f"Found {len(processed_email_ids)} previously processed emails.")
    query = f"from:{REMARKABLE_SENDER_EMAIL} has:attachment is:unread subject:\"{REMARKABLE_SUBJECT_KEYWORD}\""
    print(f"\nSearching for new emails with query: '{query}'")
    message_ids = gmail_client.search_messages(query=query)
    new_message_ids = [msg_id for msg_id in message_ids if msg_id not in processed_email_ids]
    print(f"Found {len(new_message_ids)} new unread reMarkable emails to process.")
    if not new_message_ids:
        print("No new reMarkable pages to process. Exiting.")
        return
    for msg_id in new_message_ids:
        print(f"\n--- Processing email ID: {msg_id} ---")
        message = gmail_client.get_message(msg_id)
        if message:
            downloaded_paths = []
            try:
                downloaded_paths = gmail_client.download_attachments(message, DOWNLOAD_ATTACHMENTS_DIR)
            except Exception as e:
                print(f"  Failed to download attachments for email {msg_id}: {e}")
                continue
            processed_any_pdf = False
            for attachment_path in downloaded_paths:
                if attachment_path.lower().endswith('.pdf'):
                    print(f"  Processing PDF attachment: {os.path.basename(attachment_path)}")
                    extracted_text = extract_text_from_remarkable_pdf(attachment_path)
                    if extracted_text and extracted_text.strip():
                        tasks = parse_tasks(extracted_text)
                        add_tasks_to_calendar(tasks)
                        processed_any_pdf = True
                    else:
                        print(f"  No text extracted or text was empty from {os.path.basename(attachment_path)}. Skipping task processing for this PDF.")
                    if os.path.exists(attachment_path):
                        os.remove(attachment_path)
                        print(f"  Cleaned up local attachment: {os.path.basename(attachment_path)}")
            if processed_any_pdf:
                if gmail_client.mark_message_as_read(msg_id):
                    save_processed_email_id(msg_id)
                else:
                    print(f"  WARNING: Could not mark email {msg_id} as read. It might be re-processed next time.")
            else:
                print(f"  No relevant PDFs processed for email {msg_id}. Not marking as read.")
        else:
            print(f"  Could not retrieve full message details for email ID: {msg_id}. Skipping.")
    print("\n--- ReMarkable List Prioritizer Run Complete ---")

if __name__ == "__main__":
    main()import os
    import re
    from dotenv import load_dotenv
    from src.clients.google.google_gmail_client import GmailClient
    from pdf2image import convert_from_path
    import pytesseract
    from PIL import Image
    
    # --- Configuration ---
    load_dotenv()
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DOWNLOAD_ATTACHMENTS_DIR = os.path.join(BASE_DIR, "downloaded_remarkable_attachments")
    PROCESSED_EMAIL_IDS_LOG = os.path.join(BASE_DIR, "processed_emails.log")
    
    REMARKABLE_SENDER_EMAIL = os.getenv("REMARKABLE_SENDER_EMAIL", "noreply@remarkable.com")
    REMARKABLE_SUBJECT_KEYWORD = os.getenv("REMARKABLE_SUBJECT_KEYWORD", "reMarkable Note")
    
    PYTESSERACT_CMD_PATH = os.getenv("PYTESSERACT_CMD_PATH", "/usr/bin/tesseract")
    if not os.path.exists(PYTESSERACT_CMD_PATH):
        raise FileNotFoundError(f"Tesseract executable not found at {PYTESSERACT_CMD_PATH}. Please check your installation.")
    pytesseract.pytesseract.tesseract_cmd = PYTESSERACT_CMD_PATH
    
    def load_processed_email_ids():
        if not os.path.exists(PROCESSED_EMAIL_IDS_LOG):
            return set()
        with open(PROCESSED_EMAIL_IDS_LOG, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    
    def save_processed_email_id(email_id):
        with open(PROCESSED_EMAIL_IDS_LOG, 'a') as f:
            f.write(email_id + '\n')
    
    def extract_text_from_remarkable_pdf(pdf_path):
        print(f"  Attempting OCR on PDF: {os.path.basename(pdf_path)}")
        try:
            pages = convert_from_path(pdf_path, dpi=300)
            full_text_parts = []
            for i, page in enumerate(pages):
                print(f"    Processing page {i+1}/{len(pages)}...")
                text = pytesseract.image_to_string(page)
                full_text_parts.append(text)
            return "\n".join(full_text_parts)
        except Exception as e:
            print(f"  Error during PDF OCR for {os.path.basename(pdf_path)}: {e}")
            return None
    
    def parse_tasks(text_content):
        print(f"  --- Parsing Tasks (Placeholder) ---")
        print(f"  Received text for parsing:\n{text_content[:300].strip()}...\n")
        tasks = []
        lines = text_content.splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.lower().startswith("todo:") or re.match(r'^\s*\[\s*\]\s*.+', line):
                task_desc = line.replace("TODO:", "").strip()
                priority = "Medium"
                if "urgent" in line.lower() or "asap" in line.lower():
                    priority = "High"
                elif "low priority" in line.lower():
                    priority = "Low"
                tasks.append({
                    "task": task_desc,
                    "priority": priority,
                    "source_line": line
                })
        return tasks
    
    def add_tasks_to_calendar(tasks):
        print(f"  --- Adding Tasks to Calendar (Placeholder) ---")
        if tasks:
            for task in tasks:
                print(f"  - Adding task to calendar: '{task.get('task')}' (Priority: {task.get('priority')})")
    
    def main():
        print("--- Starting reMarkable List Prioritizer ---")
        os.makedirs(DOWNLOAD_ATTACHMENTS_DIR, exist_ok=True)
        gmail_client = GmailClient()
        if not gmail_client.service:
            print("Failed to initialize Gmail client. Ensure your OAuth credentials are correct and the file exists.")
            return
        processed_email_ids = load_processed_email_ids()
        print(f"Found {len(processed_email_ids)} previously processed emails.")
        query = f"from:{REMARKABLE_SENDER_EMAIL} has:attachment is:unread subject:\"{REMARKABLE_SUBJECT_KEYWORD}\""
        print(f"\nSearching for new emails with query: '{query}'")
        message_ids = gmail_client.search_messages(query=query)
        new_message_ids = [msg_id for msg_id in message_ids if msg_id not in processed_email_ids]
        print(f"Found {len(new_message_ids)} new unread reMarkable emails to process.")
        if not new_message_ids:
            print("No new reMarkable pages to process. Exiting.")
            return
        for msg_id in new_message_ids:
            print(f"\n--- Processing email ID: {msg_id} ---")
            message = gmail_client.get_message(msg_id)
            if message:
                downloaded_paths = []
                try:
                    downloaded_paths = gmail_client.download_attachments(message, DOWNLOAD_ATTACHMENTS_DIR)
                except Exception as e:
                    print(f"  Failed to download attachments for email {msg_id}: {e}")
                    continue
                processed_any_pdf = False
                for attachment_path in downloaded_paths:
                    if attachment_path.lower().endswith('.pdf'):
                        print(f"  Processing PDF attachment: {os.path.basename(attachment_path)}")
                        extracted_text = extract_text_from_remarkable_pdf(attachment_path)
                        if extracted_text and extracted_text.strip():
                            tasks = parse_tasks(extracted_text)
                            add_tasks_to_calendar(tasks)
                            processed_any_pdf = True
                        else:
                            print(f"  No text extracted or text was empty from {os.path.basename(attachment_path)}. Skipping task processing for this PDF.")
                        if os.path.exists(attachment_path):
                            os.remove(attachment_path)
                            print(f"  Cleaned up local attachment: {os.path.basename(attachment_path)}")
                if processed_any_pdf:
                    if gmail_client.mark_message_as_read(msg_id):
                        save_processed_email_id(msg_id)
                    else:
                        print(f"  WARNING: Could not mark email {msg_id} as read. It might be re-processed next time.")
                else:
                    print(f"  No relevant PDFs processed for email {msg_id}. Not marking as read.")
            else:
                print(f"  Could not retrieve full message details for email ID: {msg_id}. Skipping.")
        print("\n--- ReMarkable List Prioritizer Run Complete ---")
    
    if __name__ == "__main__":
        main()# My reMarkable Task Prioritizer

## 📝 Project Overview

This project aims to automate the process of extracting to-do list items from reMarkable notes, prioritizing them using Artificial Intelligence (AI), and potentially integrating with other tools for scheduling or task management.

**Key Features:**
* Connects to reMarkable Cloud to retrieve notes.
* Extracts identifiable task items from selected notes.
* Uses a Language Model (LLM) to prioritize tasks based on custom criteria (e.g., urgency, importance, type).
* [*Optional: Add features here, e.g., "Integrates with Google Calendar for scheduling"*]

## 🚀 Getting Started

Follow these steps to set up and run the project locally.

### Prerequisites

Before you begin, ensure you have the following installed:

* **Python 3.8+**
* **pip** (Python package installer)
* **Git** (for cloning the repository)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/my-remarkable-project.git](https://github.com/your-username/my-remarkable-project.git)
    cd my-remarkable-project
    ```

2.  **Create and activate a virtual environment:**
    It's highly recommended to use a virtual environment to manage project dependencies.

    * **macOS/Linux:**
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
    * **Windows (Command Prompt):**
        ```cmd
        py -m venv venv
        venv\Scripts\activate.bat
        ```
    * **Windows (PowerShell):**
        ```powershell
        py -m venv venv
        venv\Scripts\Activate.ps1
        ```

3.  **Install dependencies:**
    Once your virtual environment is active, install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

### Configuration (API Key Setup)

This project requires access to the reMarkable Cloud API. **Do NOT hardcode your API key directly in the code.** We use environment variables for secure storage.

1.  **Generate a reMarkable One-Time Code:**
    Go to [https://my.remarkable.com/device/desktop/connect](https://my.remarkable.com/device/desktop/connect) in your web browser and generate a new one-time code.

2.  **Create a `.env` file:**
    In the root directory of your project (where `requirements.txt` and this `README.md` file are located), create a new file named `.env`.

    Add your reMarkable one-time code to this file. Replace `YOUR_ONE_TIME_CODE_HERE` with the actual code you generated.

    ```
    REMARKABLE_ONE_TIME_CODE="YOUR_ONE_TIME_CODE_HERE"
    # Or, if you're using a device token directly:
    # REMARKABLE_DEVICE_TOKEN="your_device_token_from_rmapy_config_file"
    # REMARKABLE_USER_TOKEN="your_user_token_from_rmapy_config_file"
    ```
    *Note: The `rmapy` library often handles token exchange internally after the one-time code, storing tokens in a config file (e.g., `~/.rmapi`). You might only need the `REMARKABLE_ONE_TIME_CODE` initially.*

3.  **Ensure `.env` is ignored by Git:**
    Make sure your `.gitignore` file includes `.env` to prevent accidentally committing your secrets. (See the previous explanation on `.gitignore`).

### Running the Application

Once everything is installed and configured, you can run the main script.

```bash
# Ensure your virtual environment is active
# source venv/bin/activate (macOS/Linux) or venv\Scripts\activate.bat (Windows)

python main.py # Or whatever your main script is named
