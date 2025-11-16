import React, { useState, useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import { StyleSheet, View, SafeAreaView, Alert, TouchableOpacity, Text } from 'react-native';
import { EmotionSelector } from './components/EmotionSelector';
import { JournalEntryForm } from './components/JournalEntryForm';
import { DailySummary } from './components/DailySummary';
import { JournalService } from './services/JournalService';
import { Emotion, JournalEntry, DailySummary as DailySummaryType, Suggestion } from './types';

export default function App() {
  const [emotions, setEmotions] = useState<Emotion[]>([]);
  const [selectedEmotion, setSelectedEmotion] = useState<Emotion | null>(null);
  const [showEntryForm, setShowEntryForm] = useState(false);
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [dailySummary, setDailySummary] = useState<DailySummaryType | null>(null);
  const [currentView, setCurrentView] = useState<'emotion' | 'form' | 'summary'>('emotion');

  const journalService = JournalService.getInstance();

  useEffect(() => {
    initializeApp();
  }, []);

  const initializeApp = async () => {
    try {
      const loadedEmotions = await journalService.getEmotions();
      const loadedEntries = await journalService.getEntries();
      const todaySummary = await journalService.generateDailySummary(new Date());
      
      setEmotions(loadedEmotions);
      setEntries(loadedEntries);
      setDailySummary(todaySummary);
    } catch (error) {
      console.error('Error initializing app:', error);
      Alert.alert('Error', 'Failed to load app data');
    }
  };

  const handleEmotionSelect = (emotion: Emotion) => {
    setSelectedEmotion(emotion);
    setShowEntryForm(true);
    setCurrentView('form');
  };

  const handleSaveEntry = async (entryData: Omit<JournalEntry, 'id' | 'timestamp'>) => {
    try {
      const newEntry: JournalEntry = {
        ...entryData,
        id: Date.now().toString(),
        timestamp: new Date(),
      };

      await journalService.saveEntry(newEntry);
      
      // Update local state
      const updatedEntries = [...entries, newEntry];
      setEntries(updatedEntries);
      
      // Generate new summary
      const newSummary = await journalService.generateDailySummary(new Date());
      setDailySummary(newSummary);

      // Reset form and go to summary
      setSelectedEmotion(null);
      setShowEntryForm(false);
      setCurrentView('summary');

      Alert.alert('Success', 'Journal entry saved!');
    } catch (error) {
      console.error('Error saving entry:', error);
      Alert.alert('Error', 'Failed to save entry');
    }
  };

  const handleCancelEntry = () => {
    setSelectedEmotion(null);
    setShowEntryForm(false);
    setCurrentView('emotion');
  };

  const handleSuggestionPress = (suggestion: Suggestion) => {
    Alert.alert(
      suggestion.title,
      `${suggestion.description}\n\nAction: ${suggestion.action}`,
      [
        { text: 'OK', style: 'default' },
        { text: 'Learn More', style: 'default' }
      ]
    );
  };

  const handleViewSummary = () => {
    setCurrentView('summary');
  };

  const handleNewEntry = () => {
    setCurrentView('emotion');
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="dark" />
      
      {currentView === 'emotion' && (
        <View style={styles.content}>
          <EmotionSelector
            emotions={emotions}
            selectedEmotion={selectedEmotion}
            onEmotionSelect={handleEmotionSelect}
          />
          {dailySummary && dailySummary.entries.length > 0 && (
            <View style={styles.summaryButton}>
              <TouchableOpacity
                onPress={handleViewSummary}
                style={styles.summaryButtonStyle}
              >
                <Text style={styles.buttonText}>View Today's Summary</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      )}

      {currentView === 'form' && showEntryForm && (
        <JournalEntryForm
          selectedEmotion={selectedEmotion}
          onSave={handleSaveEntry}
          onCancel={handleCancelEntry}
        />
      )}

      {currentView === 'summary' && dailySummary && (
        <View style={styles.content}>
          <DailySummary
            summary={dailySummary}
            onSuggestionPress={handleSuggestionPress}
          />
          <View style={styles.actionButtons}>
            <TouchableOpacity
              onPress={handleNewEntry}
              style={styles.actionButton}
            >
              <Text style={styles.buttonText}>New Entry</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  content: {
    flex: 1,
  },
  summaryButton: {
    padding: 20,
    alignItems: 'center',
  },
  summaryButtonStyle: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 30,
    paddingVertical: 15,
    borderRadius: 25,
  },
  actionButtons: {
    padding: 20,
    alignItems: 'center',
  },
  actionButton: {
    backgroundColor: '#34C759',
    paddingHorizontal: 30,
    paddingVertical: 15,
    borderRadius: 25,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
