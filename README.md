### 📝 Project Overview

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
