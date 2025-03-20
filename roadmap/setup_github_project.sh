#!/bin/bash

# Replace with your project number
PROJECT_NUMBER=2

# Replace with your GitHub username if needed
# OWNER="That-Lady-Dev"

# Skip the header line and process each row
tail -n +2 roadmap_items.csv | while IFS=, read -r title assignees status priority area timeline description
do
    # Remove quotes from fields
    title=$(echo $title | sed 's/^"//;s/"$//')
    description=$(echo $description | sed 's/^"//;s/"$//')
    priority=$(echo $priority | sed 's/^"//;s/"$//')
    area=$(echo $area | sed 's/^"//;s/"$//')
    timeline=$(echo $timeline | sed 's/^"//;s/"$//')
    
    # Create body with metadata
    body="**Priority:** $priority
**Area:** $area
**Timeline:** $timeline

$description"
    
    echo "Creating item: $title"
    
    # Uncomment the line below if you need to specify the owner
    # gh project item-create $PROJECT_NUMBER --owner $OWNER --title "$title" --body "$body"
    
    # Or use this if you're the owner
    gh project item-create $PROJECT_NUMBER --title "$title" --body "$body" --owner OliverAdams
    
    # Optional: Add a small delay to avoid rate limiting
    sleep 1
done

echo "All items have been added to your project."