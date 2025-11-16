# 📔 How to View User Journals (Sim4)

## 🎯 Quick Access Methods

### **1. Interactive Script (Easiest)**
```bash
cd /Users/manojgupta/ejouurnal
./view-journals.sh
```

**Features:**
- ✅ Browse recent journals
- ✅ Filter by nutrition analysis
- ✅ Search by user ID
- ✅ View statistics
- ✅ Export random samples

---

### **2. Direct SQLite Queries**

#### **View Recent Journals:**
```bash
cd /Users/manojgupta/ejouurnal/backend
sqlite3 fulfillment.db "
  SELECT 
    user_id, 
    SUBSTR(created_at, 1, 19) as created,
    tone,
    LENGTH(content) as chars,
    SUBSTR(content, 1, 100) || '...' as preview
  FROM journals 
  ORDER BY created_at DESC 
  LIMIT 10;
"
```

#### **View Full Journal:**
```bash
sqlite3 fulfillment.db "
  SELECT content 
  FROM journals 
  WHERE user_id = 'sim4_quick_001' 
  ORDER BY created_at DESC 
  LIMIT 1;
"
```

#### **Journals with Nutrition Analysis:**
```bash
sqlite3 fulfillment.db "
  SELECT user_id, content 
  FROM journals 
  WHERE content LIKE '%protein%' 
     OR content LIKE '%fiber%' 
     OR content LIKE '%vitamin%' 
     OR content LIKE '%carb%'
  LIMIT 5;
"
```

#### **User's Complete Journal History:**
```bash
sqlite3 fulfillment.db "
  SELECT 
    SUBSTR(created_at, 1, 19) as created,
    LENGTH(content) as chars,
    content
  FROM journals 
  WHERE user_id = 'sim4_quick_042'
  ORDER BY created_at ASC;
"
```

---

### **3. Export Journals to File**

#### **Export All Journals (JSON):**
```bash
sqlite3 fulfillment.db "
  SELECT json_group_array(
    json_object(
      'user_id', user_id,
      'created_at', created_at,
      'tone', tone,
      'content', content,
      'personal_notes', personal_notes
    )
  )
  FROM journals;
" > all_journals.json
```

#### **Export Nutrition Journals Only:**
```bash
sqlite3 fulfillment.db "
  SELECT 
    '=========================' || char(10) ||
    'USER: ' || user_id || char(10) ||
    'CREATED: ' || created_at || char(10) ||
    '=========================' || char(10) || char(10) ||
    content || char(10) || char(10)
  FROM journals 
  WHERE content LIKE '%protein%' 
     OR content LIKE '%fiber%' 
     OR content LIKE '%vitamin%'
  ORDER BY created_at DESC;
" > nutrition_journals.txt
```

#### **Export by User:**
```bash
USER_ID="sim4_quick_001"
sqlite3 fulfillment.db "
  SELECT content 
  FROM journals 
  WHERE user_id = '$USER_ID'
  ORDER BY created_at DESC;
" > user_${USER_ID}_journals.txt
```

---

### **4. Journal Statistics**

#### **Overall Stats:**
```bash
sqlite3 fulfillment.db "
  SELECT 
    COUNT(*) as total_journals,
    COUNT(DISTINCT user_id) as unique_users,
    ROUND(AVG(LENGTH(content)), 0) as avg_length,
    MIN(created_at) as first_journal,
    MAX(created_at) as latest_journal
  FROM journals;
"
```

#### **Nutrition Analysis Rate:**
```bash
sqlite3 fulfillment.db "
  SELECT 
    (SELECT COUNT(*) FROM journals) as total,
    (SELECT COUNT(*) FROM journals 
     WHERE content LIKE '%protein%' OR content LIKE '%fiber%' 
        OR content LIKE '%vitamin%' OR content LIKE '%carb%') as with_nutrition,
    ROUND(
      (SELECT COUNT(*) FROM journals WHERE content LIKE '%protein%' OR content LIKE '%fiber%') * 100.0 / 
      (SELECT COUNT(*) FROM journals), 2
    ) || '%' as nutrition_rate;
"
```

#### **Top Journal Writers:**
```bash
sqlite3 fulfillment.db "
  SELECT 
    user_id,
    COUNT(*) as journal_count,
    ROUND(AVG(LENGTH(content)), 0) as avg_length
  FROM journals 
  GROUP BY user_id
  ORDER BY journal_count DESC
  LIMIT 10;
"
```

---

## 📊 **Current Database Summary**

**As of Day 8 (~15 min into simulation):**
```
Total Journals: 304+
Users with Journals: 85+
Journals with Nutrition: 14+ (73.7% of those with meals)
Avg Journal Length: ~1,350 characters
```

---

## 🔍 **Search Examples**

### **Find Weight Loss Journals:**
```bash
sqlite3 fulfillment.db "
  SELECT user_id, SUBSTR(content, 1, 200) 
  FROM journals 
  WHERE content LIKE '%weight%' OR content LIKE '%lose%'
  LIMIT 3;
"
```

### **Find Exercise-Related Journals:**
```bash
sqlite3 fulfillment.db "
  SELECT user_id, SUBSTR(content, 1, 200) 
  FROM journals 
  WHERE content LIKE '%exercise%' OR content LIKE '%walk%' OR content LIKE '%run%'
  LIMIT 3;
"
```

### **Find Sleep-Related Journals:**
```bash
sqlite3 fulfillment.db "
  SELECT user_id, SUBSTR(content, 1, 200) 
  FROM journals 
  WHERE content LIKE '%sleep%' OR content LIKE '%rest%'
  LIMIT 3;
"
```

---

## 🎨 **Sample Journal Output**

Here's what a journal with nutrition analysis looks like:

```
**Reflective Journal for Sunday, October 19, 2025**

Today feels like a gentle reminder of balance, with all four of 
your check-ins completed. While your average mood remains 
uncalculated, the act of checking in with yourself is a powerful 
step towards understanding your emotional landscape. It's 
commendable that you took the time for meditation, allowing 
moments of stillness to seep into your busy day.

You enjoyed a nourishing breakfast of oatmeal with berries, 
which is a wonderful choice. This meal provided you with FIBER 
and ANTIOXIDANTS, essential for digestive health and overall 
well-being. Oatmeal is rich in COMPLEX CARBOHYDRATES, offering 
sustained energy, while the berries contribute VITAMINS and a 
burst of natural sweetness.

As you continue on your journey towards losing weight and 
feeling healthier, consider how such mindful eating contributes 
to your goals. It's a step in the right direction, even if you 
haven't yet completed all your micro-moves this week.

Your sleep quality was quite good, and a 30-minute walk is a 
lovely way to integrate movement into your day. Reflecting on 
your intention, think about how each positive choice supports 
your overarching goal of health.

As you prepare for the week ahead, carry with you the insight 
that every small act contributes to the larger picture of your 
health. What micro-move will you consciously choose to engage 
with tomorrow?
```

✅ **Notice:**
- Personalized to intention ("losing weight and feeling healthier")
- Nutrition analysis (fiber, antioxidants, complex carbs, vitamins)
- Connects meals to health goals
- Reflective and coaching tone
- References micro-moves and progress

---

## 💡 **Tips**

1. **For formatted output:** Add `.mode column` and `.headers on` before your query
2. **For large journals:** Use `LIMIT` to avoid overwhelming output
3. **For readability:** Export to file instead of viewing in terminal
4. **For analysis:** Use `LIKE` or `GLOB` for pattern matching

---

## 🚀 **Next Steps**

**Want to test the UI yourself?**

Open your browser and test the actual app:
```
http://localhost:8081
```

1. Set intention: "I want to lose weight"
2. Do check-ins (Morning, Day, Evening, Night)
3. Add details → Food: "Oatmeal with berries"
4. Generate journal
5. See nutrition analysis in real-time!

---

**The simulation is still running and generating more journals every 2 minutes! 📊**

