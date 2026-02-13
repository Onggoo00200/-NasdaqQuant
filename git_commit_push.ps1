# Set encoding for output
$OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'

Write-Host "--- Starting Git Commit and Push ---" -ForegroundColor Green

# Change to the script's directory (project root)
Set-Location -LiteralPath (Split-Path -Parent $MyInvocation.MyCommand.Definition)
Write-Host "Current directory: $(Get-Location)" -ForegroundColor Cyan

$githubRepoUrl = "https://github.com/Onggoo00200/CHOICE-STOCK"
Write-Host "Target GitHub Repo: $githubRepoUrl" -ForegroundColor Cyan

# Initialize Git repository if not already initialized
if (-not (Test-Path ".git")) {
    Write-Host "Initializing new Git repository..." -ForegroundColor Yellow
    git init
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Error: git init failed."
        exit 1
    }
    Write-Host "Git initialized." -ForegroundColor Green
} else {
    Write-Host "Git repository already initialized." -ForegroundColor DarkGray
}

# Add the remote origin if it's not already set
Write-Host "Checking remote origin..." -ForegroundColor Yellow
$remoteCheck = git remote -v | Select-String "$githubRepoUrl" -Quiet
if (-not $remoteCheck) {
    Write-Host "Remote origin not set to $githubRepoUrl. Attempting to set or modify." -ForegroundColor Yellow
    $originExists = git remote -v | Select-String "origin" -Quiet
    if ($originExists) {
        Write-Host "Existing 'origin' remote found. Removing it." -ForegroundColor Yellow
        git remote remove origin
    }
    Write-Host "Adding remote origin: $githubRepoUrl" -ForegroundColor Yellow
    git remote add origin $githubRepoUrl
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Error: git remote add origin failed."
        exit 1
    }
    Write-Host "Remote origin added." -ForegroundColor Green
} else {
    Write-Host "Remote origin already set to $githubRepoUrl." -ForegroundColor DarkGray
}

# Add all current files to staging
Write-Host "Adding all files to staging..." -ForegroundColor Yellow
git add .
if ($LASTEXITCODE -ne 0) {
    Write-Error "Error: git add failed."
    exit 1
}
Write-Host "Files added to staging." -ForegroundColor Green

# Get current date and time for commit message
$currentDate = Get-Date -Format "yyyy-MM-dd"
$currentTime = Get-Date -Format "HH-mm-ss"
$commitMessage = "Automated commit - $currentDate $currentTime"
Write-Host "Committing changes with message: '$commitMessage'" -ForegroundColor Yellow
git commit -m "$commitMessage"
if ($LASTEXITCODE -ne 0) {
    $gitStatus = git status
    if ($gitStatus | Select-String "nothing to commit, working tree clean" -Quiet) {
        Write-Host "No changes to commit. Skipping commit step." -ForegroundColor DarkYellow
    } else {
        Write-Error "Error: git commit failed."
        exit 1
    }
} else {
    Write-Host "Changes committed." -ForegroundColor Green
}

# Push changes to GitHub
Write-Host "Pushing changes to GitHub... You might be prompted for credentials." -ForegroundColor Yellow
git push -u origin main
if ($LASTEXITCODE -ne 0) {
    Write-Error "Error: git push failed. Please check your network and GitHub credentials."
} else {
    Write-Host "Successfully pushed to GitHub." -ForegroundColor Green
}

Write-Host "`nGit operation complete. Press Enter to exit..." -ForegroundColor Green
Read-Host
