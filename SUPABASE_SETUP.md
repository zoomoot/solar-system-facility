# Supabase Configuration Guide

## 1. Create a Supabase Project

1. Go to https://supabase.com and sign in
2. Create a new project (choose EU region for GDPR)
3. Note your **Project URL** and **anon/public API key** from Settings > API

## 2. Run the Schema

In Dashboard > SQL Editor, paste and run the contents of `supabase_schema.sql`.

## 3. Enable Email Confirmation

1. Go to **Authentication > Settings > Email**
2. Toggle **Enable email confirmations** ON
3. Set **Site URL** to `https://solarsystem.zoomoot.com`
4. Under **Redirect URLs**, add:
   - `https://solarsystem.zoomoot.com`
   - `http://localhost:8501` (for local dev)

## 4. Configure Custom SMTP (Resend)

Using Resend (free tier: 100 emails/day, 3000/month):

1. Sign up at https://resend.com
2. Add and verify domain `zoomoot.com` (add DNS records they provide)
3. Create an API key
4. In Supabase Dashboard > Authentication > Settings > SMTP Settings:
   - **Enable Custom SMTP**: ON
   - **Sender email**: `noreply@zoomoot.com`
   - **Sender name**: `Solar System Facility`
   - **Host**: `smtp.resend.com`
   - **Port**: `465`
   - **Username**: `resend`
   - **Password**: your Resend API key (`re_...`)

## 5. Email Templates

In Authentication > Email Templates, customise:

- **Confirm signup**: "Welcome to the Solar System Facility! Confirm your account..."
- **Reset password**: "Reset your Solar System Facility password..."

## 6. Database Webhook for Email Notifications

1. Go to **Database > Webhooks > Create**
2. Name: `notify-new-contribution`
3. Table: `contributions`
4. Events: `INSERT`
5. Type: **Supabase Edge Function**
6. Function: `notify-contribution`

## 7. Edge Function Deployment

```bash
supabase functions deploy notify-contribution
```

Set the secrets:
```bash
supabase secrets set RESEND_API_KEY=re_your_key
supabase secrets set NOTIFICATION_EMAIL=info@zoomoot.com
supabase secrets set SITE_URL=https://solarsystem.zoomoot.com
```

## 8. Update App Config

Add to `.env` or `.streamlit/secrets.toml`:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-public-key
```
