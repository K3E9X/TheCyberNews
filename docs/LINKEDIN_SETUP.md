# LinkedIn Auto-Sharing Setup Guide

This guide explains how to configure automatic daily LinkedIn posts for TheCyberNews.

## 🎯 What This Does

- **Selects** the best cybersecurity article from TOP 12 daily
- **Generates** a personalized message in English using AI
- **Posts** automatically to your LinkedIn at 19:00 UTC every day
- **Tracks** shared articles to avoid duplicates

## 📋 Prerequisites

1. A LinkedIn account
2. GitHub repository with Actions enabled
3. (Optional) OpenAI API key for AI-generated messages

## 🔧 Step-by-Step Setup

### 1. Create a LinkedIn App

1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/apps)
2. Click **"Create app"**
3. Fill in the details:
   - **App name**: TheCyberNews Auto-Poster
   - **LinkedIn Page**: Your personal profile or company page
   - **App logo**: (optional)
4. Accept the API Terms of Use
5. Click **"Create app"**

### 2. Configure App Permissions

1. Go to the **"Products"** tab
2. Request access to **"Share on LinkedIn"** product
3. Wait for approval (usually instant for personal use)

### 3. Get Your Access Token

#### Option A: Using OAuth 2.0 (Recommended for long-term use)

1. Go to the **"Auth"** tab
2. Copy your **Client ID** and **Client Secret**
3. Add redirect URL: `https://localhost/`
4. Generate authorization URL:
   ```
   https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=https://localhost/&scope=w_member_social
   ```
5. Visit the URL in browser, authorize the app
6. Copy the `code` from the redirect URL
7. Exchange code for access token:
   ```bash
   curl -X POST https://www.linkedin.com/oauth/v2/accessToken \
     -H 'Content-Type: application/x-www-form-urlencoded' \
     -d 'grant_type=authorization_code' \
     -d 'code=YOUR_CODE' \
     -d 'client_id=YOUR_CLIENT_ID' \
     -d 'client_secret=YOUR_CLIENT_SECRET' \
     -d 'redirect_uri=https://localhost/'
   ```

#### Option B: Developer Token (Quick setup, expires in 60 days)

1. Go to **"Auth"** tab
2. Scroll to **"OAuth 2.0 tools"**
3. Click **"Generate token"** under "Access token"
4. Copy the token

### 4. Get Your LinkedIn User ID (URN)

Run this command with your access token:

```bash
curl -X GET 'https://api.linkedin.com/v2/me' \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN'
```

Look for the `id` field in the response. It will be something like `urn:li:person:XXXXXXXXX`

### 5. Add Secrets to GitHub

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**
4. Add these secrets:

   | Secret Name | Value | Example |
   |------------|-------|---------|
   | `LINKEDIN_ACCESS_TOKEN` | Your access token from Step 3 | `AQV...` |
   | `LINKEDIN_USER_ID` | Your URN from Step 4 | `urn:li:person:12345` |
   | `OPENAI_API_KEY` | (Optional) Your OpenAI key | `sk-...` |

### 6. Test the Workflow

1. Go to **Actions** tab in GitHub
2. Select **"Share to LinkedIn"** workflow
3. Click **"Run workflow"** → **"Run workflow"**
4. Check the logs to verify it works

## 🎨 Message Customization

### With OpenAI (AI-Generated Messages)

If `OPENAI_API_KEY` is set, messages will be:
- ✅ Personalized to each article
- ✅ Adapted to severity level
- ✅ Professional and engaging
- ✅ Include relevant hashtags

### Without OpenAI (Fallback Messages)

Simple templates based on severity:
- 🚨 **CRITICAL**: Urgent alerts
- ⚠️ **HIGH**: Important updates
- 📊 **MEDIUM**: Security insights
- ℹ️ **LOW**: General news

## 🔄 How It Works

1. **Daily at 19:00 UTC**, GitHub Actions runs
2. Script loads the latest articles from cache
3. Selects the best article (prioritizes CRITICAL > HIGH > MEDIUM > LOW)
4. Generates a personalized message
5. Posts to LinkedIn with article link
6. Saves article URL to avoid re-sharing

## 📊 Article Selection Logic

- Prioritizes higher severity threats
- Avoids sharing the same article twice
- Resets when all articles have been shared
- Random selection within same severity level

## 🔐 Security Notes

- ✅ Access tokens are stored as GitHub Secrets (encrypted)
- ✅ Never commit tokens to the repository
- ⚠️ LinkedIn tokens expire after 60 days (use OAuth refresh for long-term)
- ⚠️ Monitor API rate limits (LinkedIn: 100 posts/day)

## 🛠️ Troubleshooting

### "Missing LinkedIn credentials" error
- Verify secrets are set correctly in GitHub Settings
- Check secret names match exactly

### "Failed to post" error
- Check if access token is expired
- Verify LinkedIn app has "Share on LinkedIn" permission
- Check LinkedIn URN format: `urn:li:person:XXXXXX`

### No articles to share
- Ensure `update-news.yml` workflow has run
- Check `data/news_cache.json` exists and has content

### Message not personalized
- Verify `OPENAI_API_KEY` is set in GitHub Secrets
- Check OpenAI API credits/quota

## 📅 Changing Schedule

Edit `.github/workflows/share-linkedin.yml`:

```yaml
schedule:
  - cron: "0 19 * * *"  # 19:00 UTC
```

Cron format: `minute hour day month weekday`
- `"0 18 * * *"` = 18:00 UTC
- `"0 12 * * 1-5"` = 12:00 UTC, Monday-Friday only

**Note**: GitHub Actions uses UTC timezone!

## 📞 Support

For issues or questions:
1. Check workflow logs in Actions tab
2. Review LinkedIn API documentation
3. Verify all secrets are set correctly

---

🚀 **Ready to go!** Your TheCyberNews updates will now be shared automatically on LinkedIn every day at 19:00 UTC.
