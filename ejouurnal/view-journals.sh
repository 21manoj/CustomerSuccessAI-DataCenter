#!/bin/bash
# View Journals from Sim4 Database

echo "═══════════════════════════════════════════════════"
echo "  📔 JOURNAL VIEWER - SIM4 DATABASE"
echo "═══════════════════════════════════════════════════"
echo ""

DB_PATH="/Users/manojgupta/ejouurnal/backend/fulfillment.db"

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "❌ Database not found at $DB_PATH"
    exit 1
fi

# Function to display menu
show_menu() {
    echo ""
    echo "Choose an option:"
    echo "  1. Show recent journals (last 5)"
    echo "  2. Show journals with nutrition analysis"
    echo "  3. Show journals by specific user"
    echo "  4. Show all journal statistics"
    echo "  5. Export a random journal"
    echo "  6. Exit"
    echo ""
    read -p "Enter choice [1-6]: " choice
    
    case $choice in
        1) show_recent_journals ;;
        2) show_nutrition_journals ;;
        3) show_user_journals ;;
        4) show_statistics ;;
        5) export_random_journal ;;
        6) echo "👋 Goodbye!"; exit 0 ;;
        *) echo "❌ Invalid choice"; show_menu ;;
    esac
}

# Function to show recent journals
show_recent_journals() {
    echo ""
    echo "📋 LAST 5 JOURNALS:"
    echo "─────────────────────────────────────────────────"
    sqlite3 "$DB_PATH" <<EOF
.mode column
.headers on
SELECT 
    SUBSTR(user_id, -3) as usr,
    SUBSTR(created_at, 12, 8) as time,
    tone,
    LENGTH(content) as chars,
    SUBSTR(content, 1, 80) || '...' as preview
FROM journals 
ORDER BY created_at DESC 
LIMIT 5;
EOF
    show_menu
}

# Function to show nutrition journals
show_nutrition_journals() {
    echo ""
    echo "🥗 JOURNALS WITH NUTRITION ANALYSIS:"
    echo "─────────────────────────────────────────────────"
    
    COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM journals WHERE content LIKE '%protein%' OR content LIKE '%fiber%' OR content LIKE '%vitamin%' OR content LIKE '%carb%';")
    echo "Found: $COUNT journals with nutrition keywords"
    echo ""
    
    read -p "View full journal? [y/n]: " view
    if [ "$view" = "y" ]; then
        echo ""
        echo "═══════════════════════════════════════════════════"
        sqlite3 "$DB_PATH" "SELECT content FROM journals WHERE content LIKE '%protein%' OR content LIKE '%fiber%' OR content LIKE '%vitamin%' LIMIT 1;"
        echo "═══════════════════════════════════════════════════"
    fi
    show_menu
}

# Function to show journals by user
show_user_journals() {
    echo ""
    read -p "Enter user ID (e.g., sim4_quick_001): " user_id
    
    COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM journals WHERE user_id = '$user_id';")
    echo ""
    echo "Found: $COUNT journals for $user_id"
    
    if [ "$COUNT" -gt 0 ]; then
        echo ""
        read -p "View journals? [y/n]: " view
        if [ "$view" = "y" ]; then
            sqlite3 "$DB_PATH" <<EOF
.mode column
.headers on
SELECT 
    SUBSTR(created_at, 1, 19) as created,
    tone,
    LENGTH(content) as chars
FROM journals 
WHERE user_id = '$user_id'
ORDER BY created_at DESC;
EOF
            echo ""
            read -p "View full text of latest journal? [y/n]: " view_full
            if [ "$view_full" = "y" ]; then
                echo ""
                echo "═══════════════════════════════════════════════════"
                sqlite3 "$DB_PATH" "SELECT content FROM journals WHERE user_id = '$user_id' ORDER BY created_at DESC LIMIT 1;"
                echo "═══════════════════════════════════════════════════"
            fi
        fi
    fi
    show_menu
}

# Function to show statistics
show_statistics() {
    echo ""
    echo "📊 JOURNAL STATISTICS:"
    echo "─────────────────────────────────────────────────"
    
    TOTAL=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM journals;")
    WITH_NUTRITION=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM journals WHERE content LIKE '%protein%' OR content LIKE '%fiber%' OR content LIKE '%vitamin%' OR content LIKE '%carb%';")
    UNIQUE_USERS=$(sqlite3 "$DB_PATH" "SELECT COUNT(DISTINCT user_id) FROM journals;")
    AVG_LENGTH=$(sqlite3 "$DB_PATH" "SELECT AVG(LENGTH(content)) FROM journals;")
    
    echo "Total Journals: $TOTAL"
    echo "Unique Users: $UNIQUE_USERS"
    echo "Avg per User: $(echo "scale=2; $TOTAL / $UNIQUE_USERS" | bc)"
    echo "With Nutrition: $WITH_NUTRITION ($(echo "scale=1; $WITH_NUTRITION * 100 / $TOTAL" | bc)%)"
    echo "Avg Length: ${AVG_LENGTH%.*} characters"
    echo ""
    
    echo "Top 5 Most Active Journal Writers:"
    sqlite3 "$DB_PATH" <<EOF
.mode column
.headers on
SELECT 
    user_id,
    COUNT(*) as journal_count,
    AVG(LENGTH(content)) as avg_chars
FROM journals 
GROUP BY user_id
ORDER BY journal_count DESC
LIMIT 5;
EOF
    show_menu
}

# Function to export random journal
export_random_journal() {
    echo ""
    echo "📝 RANDOM JOURNAL:"
    echo "═══════════════════════════════════════════════════"
    
    sqlite3 "$DB_PATH" <<EOF
SELECT 
    '👤 User: ' || user_id || '
🎨 Tone: ' || tone || '
📅 Created: ' || created_at || '
──────────────────────────────────────────────────────

' || content || '

═══════════════════════════════════════════════════'
FROM journals 
ORDER BY RANDOM() 
LIMIT 1;
EOF
    show_menu
}

# Start the menu
show_menu

