# TECNOsense-tracker
For Codenection hardware track progress update

## Overview

TECNOSense is a real-time IoT dashboard for monitoring and analyzing campus room occupancy. It provides a comprehensive solution for power management, resource optimization, and safety monitoring. This platform uses a cloud-based architecture with Google Firebase for data storage and a Streamlit web application for visualization and analysis.

The system is designed to be highly efficient, minimizing cloud service costs by aggregating data and reducing unnecessary database writes.

## Key Features

*   **Real-Time Monitoring:** View live metrics for occupancy, person count, light intensity, and air quality.
*   **Historical Analysis:** Analyze trends over various time periods (12 hours, 24 hours, 7 days, 30 days) with interactive charts.
*   **AI-Powered Insights:** A simple machine learning model identifies and predicts hourly occupancy patterns to inform energy-saving strategies.
*   **Cost-Efficient Architecture:** The simulator intelligently aggregates data and only writes to the database when conditions change, dramatically reducing cloud costs.
*   **Scalable Cloud Backend:** Built on Google Firebase's Firestore for robust, secure, and scalable data management.

## Tech Stack

*   **Frontend:** Streamlit
*   **Backend / Database:** Google Firebase (Firestore)
*   **Data Simulation:** Python
*   **Data Analysis:** Pandas, Scikit-learn
*   **Visualization:** Plotly

---

## Prerequisites

Before you begin, ensure you have the following installed:

*   Python 3.11
*   Git

## Setup and Installation

Follow these steps to set up the project environment on your local machine.

### 1. Clone the Repository

First, clone the project repository to your local machine:

```bash
git clone https://github.com/Konigtitan/TECNOsense-tracker.git
cd TECNOsense-tracker
```

### 2. Set Up Firebase

This project requires a Google Firebase backend.

1.  Create a new project in the Firebase Console.
2.  Navigate to **Firestore Database** and create a new database. Start in **Test Mode**.
3.  Go to **Project settings > Service accounts**.
4.  Click **"Generate new private key"** and download the resulting JSON file.
5.  **Important:** Rename this file to `firebase_credentials.json` and place it in the root of the project folder (`TECNOsense-tracker/`). This file is included in `.gitignore` and should never be committed to version control.

### 3. Create and Activate the Python Virtual Environment

It is crucial to use a virtual environment to manage project dependencies.

```bash
# Create the virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows (Command Prompt):
venv\Scripts\activate.bat

# On Windows (PowerShell):
# You may need to run `Set-ExecutionPolicy RemoteSigned` in an admin PowerShell first.
.\venv\Scripts\Activate.ps1

# On macOS / Linux:
# source venv/bin/activate
```

### 4. Install Dependencies

Install all the required Python libraries using the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

---

## Run the Streamlit Dashboard

This command will start the web server and open the TECNOSense dashboard in your browser.

```bash
# Ensure your virtual environment is activated
# (venv) ... >

streamlit run dashboard.py
```

You can now interact with the dashboard. Click the "Refresh Now" button to see the latest data from the live simulator.

---

## Project Structure

```
.
├── dashboard.py              # The main Streamlit dashboard application.
├── ESP32 program.txt         # ESP32 program.
├── firebase_credentials.json # (Ignored by Git) Your secret Firebase key.
├── requirements.txt          # List of all Python dependencies.
└── README.md                 # This file.
```