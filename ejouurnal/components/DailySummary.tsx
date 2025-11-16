import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { DailySummary as DailySummaryType, Suggestion } from '../types';

interface DailySummaryProps {
  summary: DailySummaryType;
  onSuggestionPress: (suggestion: Suggestion) => void;
}

export const DailySummary: React.FC<DailySummaryProps> = ({
  summary,
  onSuggestionPress,
}) => {
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return '#FF6B6B';
      case 'medium': return '#FFD93D';
      case 'low': return '#6BCF7F';
      default: return '#6BCF7F';
    }
  };

  const getTypeIcon = (type: string) => {
    return type === 'professional' ? '👨‍⚕️' : '👥';
  };

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <View style={styles.header}>
        <Text style={styles.date}>{summary.date}</Text>
        <View style={[styles.dominantEmotion, { backgroundColor: summary.dominantEmotion.color }]}>
          <Text style={styles.emotionEmoji}>{summary.dominantEmotion.emoji}</Text>
          <Text style={styles.emotionName}>{summary.dominantEmotion.name}</Text>
        </View>
      </View>

      <View style={styles.summarySection}>
        <Text style={styles.sectionTitle}>Daily Summary</Text>
        <Text style={styles.summaryText}>{summary.summary}</Text>
      </View>

      <View style={styles.entriesSection}>
        <Text style={styles.sectionTitle}>
          Entries ({summary.entries.length})
        </Text>
        {summary.entries.map((entry, index) => (
          <View key={entry.id || index} style={styles.entryCard}>
            <View style={styles.entryHeader}>
              <Text style={styles.entryTime}>
                {entry.timestamp.toLocaleTimeString([], { 
                  hour: '2-digit', 
                  minute: '2-digit' 
                })}
              </Text>
              <View style={[styles.entryEmotion, { backgroundColor: entry.emotion.color }]}>
                <Text style={styles.entryEmotionEmoji}>{entry.emotion.emoji}</Text>
              </View>
            </View>
            <Text style={styles.entryText}>
              <Text style={styles.entryLabel}>Who:</Text> {entry.who} • 
              <Text style={styles.entryLabel}> When:</Text> {entry.when} • 
              <Text style={styles.entryLabel}> Where:</Text> {entry.where}
            </Text>
            <Text style={styles.entryHow}>{entry.how}</Text>
            {entry.additionalNotes && (
              <Text style={styles.entryNotes}>{entry.additionalNotes}</Text>
            )}
          </View>
        ))}
      </View>

      {summary.suggestions.length > 0 && (
        <View style={styles.suggestionsSection}>
          <Text style={styles.sectionTitle}>Suggestions</Text>
          {summary.suggestions.map((suggestion) => (
            <TouchableOpacity
              key={suggestion.id}
              style={styles.suggestionCard}
              onPress={() => onSuggestionPress(suggestion)}
            >
              <View style={styles.suggestionHeader}>
                <Text style={styles.suggestionIcon}>
                  {getTypeIcon(suggestion.type)}
                </Text>
                <View style={styles.suggestionInfo}>
                  <Text style={styles.suggestionTitle}>{suggestion.title}</Text>
                  <Text style={styles.suggestionType}>
                    {suggestion.type === 'professional' ? 'Professional Support' : 'Community'}
                  </Text>
                </View>
                <View style={[
                  styles.priorityBadge,
                  { backgroundColor: getPriorityColor(suggestion.priority) }
                ]}>
                  <Text style={styles.priorityText}>
                    {suggestion.priority.toUpperCase()}
                  </Text>
                </View>
              </View>
              <Text style={styles.suggestionDescription}>
                {suggestion.description}
              </Text>
              <Text style={styles.suggestionAction}>
                💡 {suggestion.action}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  header: {
    backgroundColor: '#fff',
    padding: 20,
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  date: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 10,
  },
  dominantEmotion: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 25,
  },
  emotionEmoji: {
    fontSize: 24,
    marginRight: 10,
  },
  emotionName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
  },
  summarySection: {
    backgroundColor: '#fff',
    margin: 15,
    padding: 20,
    borderRadius: 15,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 10,
  },
  summaryText: {
    fontSize: 16,
    lineHeight: 24,
    color: '#555',
  },
  entriesSection: {
    margin: 15,
  },
  entryCard: {
    backgroundColor: '#fff',
    padding: 15,
    borderRadius: 10,
    marginBottom: 10,
    elevation: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
  },
  entryHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  entryTime: {
    fontSize: 14,
    color: '#666',
    fontWeight: '500',
  },
  entryEmotion: {
    width: 30,
    height: 30,
    borderRadius: 15,
    justifyContent: 'center',
    alignItems: 'center',
  },
  entryEmotionEmoji: {
    fontSize: 16,
  },
  entryText: {
    fontSize: 14,
    color: '#555',
    marginBottom: 5,
  },
  entryLabel: {
    fontWeight: '600',
    color: '#333',
  },
  entryHow: {
    fontSize: 14,
    color: '#333',
    fontStyle: 'italic',
  },
  entryNotes: {
    fontSize: 12,
    color: '#666',
    marginTop: 5,
    fontStyle: 'italic',
  },
  suggestionsSection: {
    margin: 15,
  },
  suggestionCard: {
    backgroundColor: '#fff',
    padding: 15,
    borderRadius: 10,
    marginBottom: 10,
    elevation: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
  },
  suggestionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  suggestionIcon: {
    fontSize: 20,
    marginRight: 10,
  },
  suggestionInfo: {
    flex: 1,
  },
  suggestionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  suggestionType: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  priorityBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  priorityText: {
    fontSize: 10,
    fontWeight: 'bold',
    color: '#fff',
  },
  suggestionDescription: {
    fontSize: 14,
    color: '#555',
    lineHeight: 20,
    marginBottom: 8,
  },
  suggestionAction: {
    fontSize: 14,
    color: '#007AFF',
    fontWeight: '500',
  },
});

