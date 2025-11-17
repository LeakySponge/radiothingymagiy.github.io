# GitHub Pages Radio Sync Setup

## For GitHub Pages Deployment (Firebase Sync)

### Step 1: Create a Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Create a new project" or select an existing one
3. Enable Google Analytics (optional but recommended)
4. Create the project

### Step 2: Set Up Realtime Database

1. In Firebase Console, go to **Realtime Database**
2. Click **Create Database**
3. Choose **Start in test mode** (allows read/write without authentication)
4. Select a region close to you
5. Click **Enable**

### Step 3: Get Your Firebase Config

1. In Firebase Console, go to **Project Settings** (gear icon)
2. Under **Your apps**, click on the web app (or add one if needed)
3. Copy the Firebase config object
4. Create a `firebase-config.json` file in your repo root with this content:

```json
{
  "apiKey": "YOUR_API_KEY",
  "authDomain": "YOUR_PROJECT.firebaseapp.com",
  "databaseURL": "https://YOUR_PROJECT.firebaseio.com",
  "projectId": "YOUR_PROJECT",
  "storageBucket": "YOUR_PROJECT.appspot.com",
  "messagingSenderId": "YOUR_SENDER_ID",
  "appId": "YOUR_APP_ID"
}
```

⚠️ **Note**: Add `firebase-config.json` to your `.gitignore` to keep credentials private, OR use only the public Firebase credentials (the API key can be public).

### Step 4: Deploy to GitHub Pages

Push your changes to the `main` branch. GitHub Actions will automatically build and deploy.

### How It Works

- **Firebase Realtime Database** stores the current track index and playback state
- **All clients** subscribe to the same database path (`radio/state`)
- When one user's song ends, it updates Firebase
- **All other clients** instantly get the update and sync to the same track
- Each client calculates **elapsed time** from the server timestamp to stay synchronized

## Local Development

For local testing:

```powershell
npm install
npm start
```

Visit `http://localhost:3000` - the sync will work locally via Firebase (if configured).

If Firebase is not configured, the radio works in **local mode** (each user plays independently).

## Firestore Rules (Test Mode)

By default, "test mode" allows unlimited read/write. For production, set these rules in **Realtime Database → Rules**:

```json
{
  "rules": {
    "radio": {
      ".read": true,
      ".write": true
    }
  }
}
```
