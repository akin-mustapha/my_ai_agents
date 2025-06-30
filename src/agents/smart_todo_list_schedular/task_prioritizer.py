import os
import mimetypes
from dotenv import load_dotenv
from datetime import datetime, timedelta, date, time
from typing import List, Optional

# Import clients
from src.clients.google.google_gmail_client import GmailClient
from src.clients.google.google_calendar_client import GoogleCalendarClient

# Import services
from src.services.ocr_service import OCRService
from src.services.llm_task_parser_service import LLMTaskParserService

# Import models
from src.models.task_model import Task
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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables. Please set it in your .env file.")

CALENDAR_TIMEZONE = os.getenv("CALENDAR_TIMEZONE", "Europe/Dublin")

# --- Helper Functions ---
def load_processed_email_ids():
    if not os.path.exists(PROCESSED_EMAIL_IDS_LOG):
        return set()
    with open(PROCESSED_EMAIL_IDS_LOG, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def save_processed_email_id(email_id):
    with open(PROCESSED_EMAIL_IDS_LOG, 'a') as f:
        f.write(email_id + '\n')

def process_content_for_tasks(extracted_text: str, llm_parser_service: LLMTaskParserService, source_type: str = "unknown") -> List[Task]:
    """
    Takes extracted text content and processes it for tasks using the LLM parser service.
    Returns a list of Task objects.
    """
    if extracted_text and extracted_text.strip():
        print(f"  Extracted text from {source_type}. Processing for tasks...")
        # Now llm_parser_service.parse_text_for_tasks fetches calendar itself
        tasks = llm_parser_service.parse_text_for_tasks(extracted_text)
        if not tasks:
            print(f"  No tasks found in content from {source_type}.")
        return tasks
    else:
        print(f"  No text extracted or text was empty from {source_type}. Skipping task processing.")
        return []

def parse_duration_string(duration_str: Optional[str]) -> timedelta:
    """
    Parses a natural language duration string into a timedelta object.
    """
    if not duration_str:
        return timedelta(hours=1) # Default

    duration_str = duration_str.lower()
    match = re.match(r'(\d+)\s*(min(?:ute)?s?|h(?:our)?s?)', duration_str)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        if 'min' in unit:
            return timedelta(minutes=value)
        elif 'h' in unit:
            return timedelta(hours=value)
    elif "flexible" in duration_str:
        return timedelta(hours=1) # Default for flexible
    return timedelta(hours=1) # Default if parsing fails


def create_calendar_events_from_tasks(tasks: List[Task], calendar_client: GoogleCalendarClient, timezone: str):
    """
    Integrates the identified tasks into your Google Calendar.
    """
    print(f"  --- Adding Tasks to Calendar ---")
    if not tasks:
        print("  No tasks to add to calendar.")
        return

    if not calendar_client.service:
        print("  Google Calendar client not initialized. Cannot add tasks.")
        return

    print(f"  Using timezone: {timezone}")

    for task in tasks:
        summary = task.task
        priority = task.priority
        explicit_due_date = task.dueDate # This can be datetime.date, datetime.datetime, or None
        # This will now hold an ISO string from LLM if a suggested time was provided
        llm_suggested_datetime_str = task.suggestedTimeOfDay
        llm_suggested_duration_str = task.suggestedDuration

        description = (
            f"Priority: {priority}\n"
            f"Source: '{task.source_line}'\n"
            f"(Line {task.line_number})\n"
            f"Processed by reMarkable Task Prioritizer on {date.today().isoformat()}"
        )

        print(f"  Attempting to add task: '{summary}' (Priority: {priority})")

        start_datetime_for_event = None
        end_datetime_for_event = None

        if explicit_due_date:
            # If an explicit due date/time was found by dateparser
            if isinstance(explicit_due_date, datetime): # Specific date AND time
                start_datetime_for_event = explicit_due_date
                duration_td = parse_duration_string(llm_suggested_duration_str) # Use LLM duration if present, else default
                end_datetime_for_event = start_datetime_for_event + duration_td
            elif isinstance(explicit_due_date, date): # Date only, convert to datetime with a default time
                # If LLM suggested a precise time, use it with the explicit date
                if llm_suggested_datetime_str:
                    try:
                        # Attempt to parse the LLM's full ISO datetime string
                        llm_dt = datetime.fromisoformat(llm_suggested_datetime_str)
                        # We must combine the *date part* from explicit_due_date with the *time part* from LLM_dt
                        start_datetime_for_event = datetime.combine(explicit_due_date, llm_dt.time())
                        duration_td = parse_duration_string(llm_suggested_duration_str)
                        end_datetime_for_event = start_datetime_for_event + duration_td
                    except ValueError:
                        print(f"    WARNING: LLM suggested datetime '{llm_suggested_datetime_str}' for task '{summary}' is not valid ISO format. Defaulting to all-day.")
                        start_datetime_for_event = explicit_due_date
                        end_datetime_for_event = explicit_due_date + timedelta(days=1)
                else:
                    # No LLM suggested time for an explicit date, default to all-day
                    start_datetime_for_event = explicit_due_date
                    end_datetime_for_event = explicit_due_date + timedelta(days=1) # All-day event end is exclusive
        elif llm_suggested_datetime_str:
            # No explicit due date, but LLM suggested a precise date and time
            try:
                start_datetime_for_event = datetime.fromisoformat(llm_suggested_datetime_str)
                duration_td = parse_duration_string(llm_suggested_duration_str)
                end_datetime_for_event = start_datetime_for_event + duration_td
            except ValueError:
                print(f"    WARNING: LLM suggested datetime '{llm_suggested_datetime_str}' for task '{summary}' is not valid ISO format. Defaulting to today/tomorrow morning.")
                # Fallback if LLM's ISO format is bad
                event_date = date.today()
                if datetime.now().hour >= 17:
                    event_date = date.today() + timedelta(days=1)
                start_datetime_for_event = datetime.combine(event_date, time(9, 0)) # Default 9 AM
                end_datetime_for_event = start_datetime_for_event + timedelta(hours=1)
        else:
            # Neither explicit due date nor LLM suggested a precise time, fallback to general default
            print(f"  Task '{summary}' has no explicit due date or LLM suggested time. Defaulting to today/tomorrow morning.")
            event_date = date.today()
            if datetime.now().hour >= 17:
                event_date = date.today() + timedelta(days=1)
            start_datetime_for_event = datetime.combine(event_date, time(9, 0)) # Default 9 AM
            end_datetime_for_event = start_datetime_for_event + timedelta(hours=1)


        if start_datetime_for_event:
            calendar_client.create_event(
                summary=summary,
                description=description,
                start_datetime=start_datetime_for_event,
                end_datetime=end_datetime_for_event,
                timezone=timezone
            )
        else:
            print(f"  Could not determine a valid start time for task '{summary}'. Skipping calendar event.")


# --- Main Orchestration Logic ---
def main():
    print("--- Starting reMarkable List Prioritizer ---")

    os.makedirs(DOWNLOAD_ATTACHMENTS_DIR, exist_ok=True)

    # Initialize Clients
    gmail_client = GmailClient()
    calendar_client = GoogleCalendarClient()

    # Initialize Services
    ocr_service = OCRService(tesseract_cmd_path=PYTESSERACT_CMD_PATH)
    # Pass the calendar_client to the LLMTaskParserService so it can query availability
    llm_parser_service = LLMTaskParserService(openai_api_key=OPENAI_API_KEY, calendar_client=calendar_client)

    if not gmail_client.service:
        print("Failed to initialize Gmail client. Please check your setup and try again.")
        return
    if not calendar_client.service:
        print("Failed to initialize Calendar client. Please check your setup and try again.")
        return # Exit if calendar is critical for scheduling

    processed_email_ids = load_processed_email_ids()
    print(f"Found {len(processed_email_ids)} previously processed emails.")

    query = (
        f"(from:{REMARKABLE_SENDER_EMAIL} has:attachment is:unread subject:\"{REMARKABLE_SUBJECT_KEYWORD}\") OR "
        f"(from:{REMARKABLE_SENDER_EMAIL} is:unread subject:\"{REMARKABLE_SUBJECT_KEYWORD}\" -has:attachment)"
    )
    print(f"\nSearching for new emails with query: '{query}'")

    message_ids = gmail_client.search_messages(query=query)
    new_message_ids = [msg_id for msg_id in message_ids if msg_id not in processed_email_ids]
    print(f"Found {len(new_message_ids)} new reMarkable emails to process.")

    if not new_message_ids:
        print("No new reMarkable pages or notes to process. Exiting.")
        return

    for msg_id in new_message_ids:
        print(f"\n--- Processing email ID: {msg_id} ---")
        message = gmail_client.get_message(msg_id)

        if not message:
            print(f"  Could not retrieve full message details for email ID: {msg_id}. Skipping.")
            continue

        all_tasks_from_email: List[Task] = []
        downloaded_paths = []

        try:
            downloaded_paths = gmail_client.download_attachments(message, DOWNLOAD_ATTACHMENTS_DIR)
        except Exception as e:
            print(f"  Failed to download attachments for email {msg_id}: {e}")
            continue

        if downloaded_paths:
            print(f"  Found {len(downloaded_paths)} attachments.")
            for attachment_path in downloaded_paths:
                file_ext = os.path.splitext(attachment_path)[1].lower()
                mime_type = mimetypes.guess_type(attachment_path)[0]

                extracted_text = None
                if file_ext == '.pdf':
                    extracted_text = ocr_service.extract_text_from_pdf(attachment_path)
                elif mime_type and mime_type.startswith('image/'):
                    extracted_text = ocr_service.extract_text_from_image(attachment_path)
                else:
                    print(f"  Skipping unsupported attachment type: {os.path.basename(attachment_path)} (MIME: {mime_type})")

                if extracted_text:
                    tasks_from_attachment = process_content_for_tasks(extracted_text, llm_parser_service, source_type=f"attachment: {os.path.basename(attachment_path)}")
                    all_tasks_from_email.extend(tasks_from_attachment)

                if os.path.exists(attachment_path):
                    os.remove(attachment_path)
                    print(f"  Cleaned up local attachment: {os.path.basename(attachment_path)}")
        else:
            print("  No attachments found. Checking email body for content.")
            email_body_text = GmailClient.get_email_body_text(message.get('payload', {}))
            if email_body_text and email_body_text.strip():
                print("  Processing email body text.")
                tasks_from_body = process_content_for_tasks(email_body_text, llm_parser_service, source_type="email body")
                all_tasks_from_email.extend(tasks_from_body)
            else:
                print("  No processable content found in email body.")

        if all_tasks_from_email:
            create_calendar_events_from_tasks(all_tasks_from_email, calendar_client, CALENDAR_TIMEZONE)
            if gmail_client.mark_message_as_read(msg_id):
                save_processed_email_id(msg_id)
                print(f"  Email {msg_id} marked as read and processed.")
            else:
                print(f"  WARNING: Could not mark email {msg_id} as read. It might be re-processed next time.")
        else:
            print(f"  No tasks found for email {msg_id}. Not marking as read.")

    print("\n--- ReMarkable List Prioritizer Run Complete ---")

if __name__ == "__main__":
    main()