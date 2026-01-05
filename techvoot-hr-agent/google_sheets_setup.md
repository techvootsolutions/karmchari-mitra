# Google Sheets Integration Setup

To enable the HR Agent to save candidates and call logs to Google Sheets, follow these steps:

## 1. Get Credentials
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or select an existing one).
3. Enable the **Google Sheets API** and **Google Drive API**.
4. Go to **APIs & Services > Credentials**.
5. Click **Create Credentials > Service Account**.
6. Give it a name (e.g., "hr-agent").
7. Once created, go to the **Keys** tab of that service account.
8. Click **Add Key > Create new key > JSON**.
9. A file will download to your computer.

## 2. Install Credentials
1. Rename the downloaded file to `credentials.json`.
2. Move this file into the root folder of your project:
   `/var/www/html/techvoot-hr-agent/credentials.json`

## 3. Setup the Sheet
1. Create a new Google Sheet at [sheets.google.com](https://docs.google.com/spreadsheets).
2. Name it exactly: **Techvoot HR Data** (or tell me if you want a different name).
3. Open your `credentials.json` file and copy the `client_email` address.
4. Go to your Google Sheet, click **Share**, and paste that email. Give it **Editor** access.

## 4. Notify Me
Once you have done this, type **"Ready"** in the chat, and I will write the code to sync the data.
