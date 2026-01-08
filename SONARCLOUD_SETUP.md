# SonarCloud Setup Guide

## Issues Fixed

### 1. Deprecated Action
- **Problem**: `SonarSource/sonarcloud-github-action@master` is deprecated
- **Solution**: Updated to `SonarSource/sonarqube-scan-action@v5.0.0`

### 2. Missing Authentication
- **Problem**: `SONAR_TOKEN` environment variable not configured
- **Solution**: Made SonarCloud scan conditional on token availability

### 3. Project Configuration
- **Problem**: SonarCloud project doesn't exist or isn't properly configured
- **Solution**: Added `sonar-project.properties` configuration file

## Setup Instructions

### Step 1: Create SonarCloud Account and Project

1. **Go to SonarCloud**: Visit [sonarcloud.io](https://sonarcloud.io)
2. **Sign in with GitHub**: Use your GitHub account to sign in
3. **Create Organization**: 
   - Click "+" → "Create new organization"
   - Choose "Create a free organization"
   - Organization key: `stock-analysis` (must match the config)
4. **Create Project**:
   - Click "+" → "Analyze new project"
   - Select your repository: `StockAnalysis`
   - Project key: `stock-analysis-tool` (must match the config)

### Step 2: Configure GitHub Secrets

1. **Get SonarCloud Token**:
   - In SonarCloud, go to "My Account" → "Security"
   - Generate a new token with a descriptive name
   - Copy the token value

2. **Add GitHub Secret**:
   - Go to your GitHub repository
   - Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `SONAR_TOKEN`
   - Value: Paste the token from SonarCloud

### Step 3: Configure Project Settings (Optional)

In SonarCloud project settings, you can configure:
- **Quality Gate**: Set custom quality criteria
- **New Code Definition**: Define what constitutes "new code"
- **Branch Analysis**: Configure main branch and PR analysis
- **Notifications**: Set up email/Slack notifications

## Configuration Files

### sonar-project.properties
This file has been created in the repository root with the following configuration:
- Project identification (key, organization, name)
- Source and test directories
- Coverage report paths
- File exclusions
- Language-specific settings

### GitHub Workflow Updates
- Updated to use `sonarqube-scan-action@v5.0.0`
- Made SonarCloud scan conditional on `SONAR_TOKEN` availability
- Removed code-quality job dependency from deployment jobs
- Added proper exclusions and source paths

## Benefits of SonarCloud Integration

1. **Code Quality Metrics**: Track technical debt, code smells, and maintainability
2. **Security Analysis**: Identify security vulnerabilities and hotspots
3. **Coverage Tracking**: Monitor test coverage trends over time
4. **Pull Request Analysis**: Get quality feedback on every PR
5. **Quality Gates**: Prevent merging code that doesn't meet quality standards

## Troubleshooting

### Common Issues:

1. **"Project not found"**:
   - Verify project key matches in SonarCloud and `sonar-project.properties`
   - Ensure organization name is correct
   - Check that SONAR_TOKEN has access to the project

2. **"No coverage reports found"**:
   - Ensure tests are running before SonarCloud scan
   - Verify coverage report paths in configuration
   - Check that coverage files are generated in the expected locations

3. **"Analysis failed"**:
   - Check SonarCloud logs for specific error messages
   - Verify source paths exist and contain analyzable files
   - Ensure no syntax errors in source code

### Testing the Setup:

1. **Create a Pull Request**: This will trigger the workflow
2. **Check Actions Tab**: Monitor the "Code Quality Analysis" job
3. **View SonarCloud**: Check the project dashboard for analysis results
4. **PR Decoration**: SonarCloud should add comments to your PR with quality feedback

## Next Steps

1. **Set up Quality Gates**: Define quality criteria that must be met
2. **Configure Notifications**: Get alerts for quality issues
3. **Review Metrics**: Regularly check code quality trends
4. **Team Training**: Ensure team understands quality metrics and how to improve them

## Optional: Advanced Configuration

### Custom Quality Gate
Create custom quality conditions in SonarCloud:
- Coverage > 80%
- Duplicated lines < 3%
- Maintainability rating = A
- Reliability rating = A
- Security rating = A

### Branch Protection Rules
In GitHub, add branch protection rules that require:
- SonarCloud quality gate to pass
- All conversations resolved
- Up-to-date branches before merging