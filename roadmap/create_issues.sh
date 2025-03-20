#!/bin/bash
# Script to create GitHub issues for roadmap items instead of using Projects API

# Configuration - update these variables
REPO="OliverAdams/sworn-backend"
CSV_FILE="roadmap_items.csv"

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo "GitHub CLI not found. Please install it first: https://cli.github.com/"
    exit 1
fi

# Check if logged in to GitHub CLI
if ! gh auth status &> /dev/null; then
    echo "You need to log in to GitHub CLI first."
    echo "Run: gh auth login"
    exit 1
fi

# Create labels for areas, timeline, and priorities
echo "Creating labels..."

# Area labels (blue)
gh label create "Area: AI Systems" --color "0366d6" --repo "$REPO" || true
gh label create "Area: World Simulation" --color "0366d6" --repo "$REPO" || true
gh label create "Area: Player Progression" --color "0366d6" --repo "$REPO" || true
gh label create "Area: Economic Systems" --color "0366d6" --repo "$REPO" || true
gh label create "Area: Combat & Encounters" --color "0366d6" --repo "$REPO" || true
gh label create "Area: Technical Infrastructure" --color "0366d6" --repo "$REPO" || true
gh label create "Area: Frontend Improvements" --color "0366d6" --repo "$REPO" || true

# Timeline labels (purple)
gh label create "Timeline: Short-term" --color "6f42c1" --repo "$REPO" || true
gh label create "Timeline: Mid-term" --color "6f42c1" --repo "$REPO" || true
gh label create "Timeline: Long-term" --color "6f42c1" --repo "$REPO" || true

# Priority labels (red/orange/yellow)
gh label create "Priority: High" --color "d73a4a" --repo "$REPO" || true
gh label create "Priority: Medium" --color "ff9800" --repo "$REPO" || true
gh label create "Priority: Low" --color "ffeb3b" --repo "$REPO" || true

echo "Labels created."

# Now, read from CSV and create issues
echo "Creating issues from $CSV_FILE..."

# Skip header line and process each row
tail -n +2 "$CSV_FILE" | while IFS=, read -r title assignees status priority area timeline description
{
    # Remove quotes
    title=$(echo "$title" | tr -d '"')
    description=$(echo "$description" | tr -d '"')
    area=$(echo "$area" | tr -d '"')
    timeline=$(echo "$timeline" | tr -d '"')
    priority=$(echo "$priority" | tr -d '"')
    
    echo "Creating issue: $title"
    
    # Create labels for the issue
    LABELS="\"Area: $area\", \"Timeline: $timeline\", \"Priority: $priority\", \"Roadmap\""
    
    # Create issue
    gh issue create --repo "$REPO" --title "$title" --body "$description" --label $LABELS
}

echo "Done! Issues created for all roadmap items."
echo "You can now add these to a project board in the GitHub web interface."