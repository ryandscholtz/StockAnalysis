# Deploying the frontend with AWS Amplify (GitHub branch)

This repo is set up so that **only the backend is deployed to AWS via GitHub Actions** (Lambda + API Gateway + DynamoDB + Cognito, etc.). The **frontend is intended to be deployed via AWS Amplify** by connecting this repository and building from a branch.

## Current setup

| Component | How it’s deployed |
|-----------|--------------------|
| **Backend** | GitHub Actions → package Lambda → CDK deploy (staging on `develop`, production on `main`). No CloudFront in CDK. |
| **Frontend** | Not deployed by GitHub Actions. Use **Amplify Hosting** with a GitHub branch. |

## Amplify build configuration

The repo already contains Amplify build specs that match the Next.js **static export**:

- **Build**: `cd frontend` → `npm ci` → `npm run build`
- **Artifacts**: `frontend/out` (static export from `next.config.js`: `output: 'export'`, `distDir: 'out'`)

Use **one** of these at the repo root:

- **Single-app**: `amplify.yml` (default when Amplify detects it)
- **Monorepo**: `amplify-monorepo.yml` (if you configure Amplify as a monorepo with `appRoot: frontend`)

No `amplify/` folder or Amplify appId in the repo is required; the Amplify app is created and linked in the AWS Amplify Console.

## Steps to use Amplify for the frontend

### 1. Create the Amplify app and connect GitHub

1. In **AWS Amplify Console** → **New app** → **Host web app**.
2. Choose **GitHub** and authorize.
3. Select this repository and the branch you want (e.g. `main` for production, `develop` for staging).
4. Amplify will detect the build spec (e.g. `amplify.yml`). Ensure the build uses `frontend/out` as the artifact directory (already configured).

### 2. Environment variables in Amplify

In Amplify: **App settings** → **Environment variables**, set (per branch if needed):

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL (e.g. from CDK output: `https://xxx.execute-api.<region>.amazonaws.com/staging` or `/production`) |
| `NEXT_PUBLIC_USER_POOL_ID` | Cognito User Pool ID (from CDK / AWS Console) |
| `NEXT_PUBLIC_USER_POOL_CLIENT_ID` | Cognito User Pool Client ID |
| `NEXT_PUBLIC_IDENTITY_POOL_ID` | Cognito Identity Pool ID |
| `NEXT_PUBLIC_AWS_REGION` | AWS region (e.g. `eu-west-1` or `us-east-1`) |

You can copy these from the CDK deployment outputs or from the Cognito and API Gateway resources in the AWS Console.

### 3. Allow Cognito to redirect back to Amplify

Cognito must allow your Amplify app URLs as callback and logout URLs.

**Option A – CDK context (recommended)**  
When deploying the backend, pass the Amplify app base URLs. For each branch you use (e.g. `main`, `develop`), add that branch’s URL without a trailing slash, e.g.:

- `https://main.xxxxxxxx.amplifyapp.com`
- `https://develop.xxxxxxxx.amplifyapp.com`

In `infrastructure/cdk.json`, under `context`, add:

```json
"frontendCallbackBaseUrls": [
  "https://main.xxxxxxxx.amplifyapp.com",
  "https://develop.xxxxxxxx.amplifyapp.com"
]
```

Replace `xxxxxxxx` with your Amplify app ID (from the Amplify Console URL or app settings).

**Option B – Environment variable**  
When running `cdk deploy` (e.g. in CI or locally):

```bash
export FRONTEND_CALLBACK_BASE_URLS="https://main.xxxxxxxx.amplifyapp.com,https://develop.xxxxxxxx.amplifyapp.com"
npx cdk deploy --all --context environment=production
```

After adding these and redeploying the backend, Cognito will allow redirects to `https://<branch>.xxxxxxxx.amplifyapp.com/auth/callback` and `.../auth/logout`.

### 4. Branch-based behavior (optional)

- **main** → point `NEXT_PUBLIC_API_URL` (and other env vars) to the **production** API.
- **develop** → point them to the **staging** API.

Configure different environment variables per branch in Amplify so each branch talks to the right backend.

## Summary

- **Backend**: Deploy only via GitHub Actions (no change); backend stays on AWS (Lambda + API Gateway + DynamoDB + Cognito, etc.).
- **Frontend**: Deploy only via Amplify by connecting this repo and building from the desired branch; build spec uses `frontend/out`.
- **Cognito**: Add Amplify base URLs via `frontendCallbackBaseUrls` (context or env) and redeploy the backend so login/logout redirects work from Amplify-hosted URLs.

No CloudFront or Amplify resources need to be defined in CDK for this flow; Amplify Hosting provides the frontend hosting and CDN.
