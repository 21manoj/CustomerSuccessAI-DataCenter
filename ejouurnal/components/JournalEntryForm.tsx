import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
} from 'react-native';
import { Emotion, JournalEntry } from '../types';

interface JournalEntryFormProps {
  selectedEmotion: Emotion | null;
  onSave: (entry: Omit<JournalEntry, 'id' | 'timestamp'>) => void;
  onCancel: () => void;
}

export const JournalEntryForm: React.FC<JournalEntryFormProps> = ({
  selectedEmotion,
  onSave,
  onCancel,
}) => {
  const [who, setWho] = useState('');
  const [when, setWhen] = useState('');
  const [where, setWhere] = useState('');
  const [how, setHow] = useState('');
  const [additionalNotes, setAdditionalNotes] = useState('');

  const handleSave = () => {
    if (!selectedEmotion) {
      Alert.alert('Error', 'Please select an emotion first');
      return;
    }

    if (!who.trim() || !when.trim() || !where.trim() || !how.trim()) {
      Alert.alert('Error', 'Please fill in all required fields');
      return;
    }

    onSave({
      emotion: selectedEmotion,
      who: who.trim(),
      when: when.trim(),
      where: where.trim(),
      how: how.trim(),
      additionalNotes: additionalNotes.trim() || undefined,
    });

    // Reset form
    setWho('');
    setWhen('');
    setWhere('');
    setHow('');
    setAdditionalNotes('');
  };

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <View style={styles.header}>
        <Text style={styles.title}>Journal Entry</Text>
        {selectedEmotion && (
          <View style={[styles.emotionDisplay, { backgroundColor: selectedEmotion.color }]}>
            <Text style={styles.emotionEmoji}>{selectedEmotion.emoji}</Text>
            <Text style={styles.emotionName}>{selectedEmotion.name}</Text>
          </View>
        )}
      </View>

      <View style={styles.form}>
        <View style={styles.inputGroup}>
          <Text style={styles.label}>Who were you with? *</Text>
          <TextInput
            style={styles.input}
            value={who}
            onChangeText={setWho}
            placeholder="e.g., Family, Friends, Alone, Colleagues"
            placeholderTextColor="#999"
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>When did this happen? *</Text>
          <TextInput
            style={styles.input}
            value={when}
            onChangeText={setWhen}
            placeholder="e.g., This morning, After lunch, Evening"
            placeholderTextColor="#999"
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>Where were you? *</Text>
          <TextInput
            style={styles.input}
            value={where}
            onChangeText={setWhere}
            placeholder="e.g., Home, Office, Park, Restaurant"
            placeholderTextColor="#999"
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>How did it make you feel? *</Text>
          <TextInput
            style={styles.input}
            value={how}
            onChangeText={setHow}
            placeholder="Describe what happened and how it affected you"
            placeholderTextColor="#999"
            multiline
            numberOfLines={3}
            textAlignVertical="top"
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>Additional Notes (Optional)</Text>
          <TextInput
            style={styles.input}
            value={additionalNotes}
            onChangeText={setAdditionalNotes}
            placeholder="Any other thoughts or details you'd like to remember"
            placeholderTextColor="#999"
            multiline
            numberOfLines={3}
            textAlignVertical="top"
          />
        </View>
      </View>

      <View style={styles.buttonContainer}>
        <TouchableOpacity style={styles.cancelButton} onPress={onCancel}>
          <Text style={styles.cancelButtonText}>Cancel</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.saveButton} onPress={handleSave}>
          <Text style={styles.saveButtonText}>Save Entry</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  header: {
    padding: 20,
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 10,
  },
  emotionDisplay: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 20,
  },
  emotionEmoji: {
    fontSize: 20,
    marginRight: 8,
  },
  emotionName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  form: {
    padding: 20,
  },
  inputGroup: {
    marginBottom: 20,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 10,
    padding: 12,
    fontSize: 16,
    backgroundColor: '#f9f9f9',
    minHeight: 50,
  },
  buttonContainer: {
    flexDirection: 'row',
    padding: 20,
    gap: 15,
  },
  cancelButton: {
    flex: 1,
    backgroundColor: '#f0f0f0',
    paddingVertical: 15,
    borderRadius: 10,
    alignItems: 'center',
  },
  cancelButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#666',
  },
  saveButton: {
    flex: 1,
    backgroundColor: '#007AFF',
    paddingVertical: 15,
    borderRadius: 10,
    alignItems: 'center',
  },
  saveButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
});

