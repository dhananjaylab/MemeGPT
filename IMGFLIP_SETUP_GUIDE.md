# Imgflip Setup Guide

## Quick Setup Instructions

I've added the Imgflip configuration to your `.env` file. Here's what you need to do:

### Step 1: Get Imgflip Credentials

1. Go to **https://imgflip.com/signup**
2. Create a free account (it's quick and free!)
3. Note down your **username** and **password**

### Step 2: Add Credentials to .env

Open `backend/.env` and find these lines (around line 20):

```bash
# Imgflip (for meme template captioning)
IMGFLIP_USERNAME=
IMGFLIP_PASSWORD=
```

Replace them with your actual credentials:

```bash
# Imgflip (for meme template captioning)
IMGFLIP_USERNAME=your_actual_username
IMGFLIP_PASSWORD=your_actual_password
```

### Step 3: Restart Your Backend Server

After adding the credentials, restart your backend server for the changes to take effect:

```bash
# Stop the current server (Ctrl+C)
# Then restart it
cd backend
python main.py
```

## What This Does

### ✅ With Imgflip Credentials:
- Imgflip templates will use the **Imgflip Caption API**
- Text positioning will be **accurate and professional**
- Memes will be generated using **Imgflip's rendering engine**
- **No watermarks** on generated memes
- **Better quality** for popular meme templates

### ⚠️ Without Imgflip Credentials:
- Imgflip templates will **fall back to local compositor**
- Memes will still be generated (no errors!)
- Text positioning may be **less accurate**
- System will work but with **degraded quality** for Imgflip templates

## Testing

After adding credentials, test with an Imgflip template:

1. Go to your frontend
2. Try generating a meme with a popular template like "Two Buttons" or "Drake Hotline Bling"
3. Check the backend logs - you should see:
   ```
   Using Imgflip API for template X (imgflip_id=...)
   Imgflip API generated meme: https://...
   ```

## Troubleshooting

### "Username and password are required" error
- Make sure you've added both `IMGFLIP_USERNAME` and `IMGFLIP_PASSWORD`
- Make sure there are no extra spaces or quotes around the values
- Restart your backend server after making changes

### Memes still not generating correctly
- Check that your Imgflip credentials are correct
- Try logging into https://imgflip.com with the same credentials
- Check backend logs for specific error messages

### Templates showing 404 errors
- This is expected if Imgflip credentials are not configured
- The system will automatically fall back to local compositor
- Add credentials to fix this issue

## Current Status

✅ Configuration added to `.env` file  
⏳ **Action Required**: Add your Imgflip username and password  
⏳ **Action Required**: Restart backend server  

## Need Help?

If you encounter any issues:
1. Check the backend logs for error messages
2. Verify your Imgflip credentials are correct
3. Make sure you've restarted the backend server
4. Check that the `.env` file has no syntax errors

---

**Note**: Imgflip credentials are **optional** but **recommended** for best quality. The system will work without them, just with reduced quality for Imgflip templates.