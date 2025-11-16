import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
} from 'react-native';

type JournalTone = 'reflective' | 'factual' | 'coach-like' | 'poetic';

interface SettingsScreenProps {
  onBack: () => void;
  currentTone: JournalTone;
  onToneChange: (tone: JournalTone) => void;
  onPreviewJournal: (tone: JournalTone) => void;
  cloudSyncEnabled: boolean;
  onCloudSyncToggle: (enabled: boolean) => void;
}

const TONE_OPTIONS: Array<{
  value: JournalTone;
  label: string;
  description: string;
  example: string;
}> = [
  {
    value: 'reflective',
    label: 'Reflective',
    description: 'Personal & encouraging',
    example: '"You started the morning feeling good after solid sleep..."'
  },
  {
    value: 'factual',
    label: 'Factual',
    description: 'Data-focused & clinical',
    example: '"Sleep: 7.5h (Quality: 4/5). Activity: 8,234 steps..."'
  },
  {
    value: 'coach-like',
    label: 'Coach-Like',
    description: 'Motivational & action-oriented',
    example: '"Great job on that 7.5h sleep streak! Keep it going..."'
  },
  {
    value: 'poetic',
    label: 'Poetic',
    description: 'Literary & contemplative',
    example: '"October\'s amber light filtered through consciousness..."'
  }
];

export const SettingsScreen: React.FC<SettingsScreenProps> = ({
  onBack,
  currentTone,
  onToneChange,
  onPreviewJournal,
  cloudSyncEnabled,
  onCloudSyncToggle
}) => {
  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack}>
          <Text style={styles.backButton}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Settings</Text>
        <View style={styles.spacer} />
      </View>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Journal Tone Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>AI Journal Tone</Text>
          <Text style={styles.sectionSubtitle}>
            Choose how your daily journal sounds
          </Text>

          <View style={styles.toneList}>
            {TONE_OPTIONS.map(tone => (
              <TouchableOpacity
                key={tone.value}
                style={[
                  styles.toneCard,
                  currentTone === tone.value && styles.toneCardSelected
                ]}
                onPress={() => onToneChange(tone.value)}
              >
                <View style={styles.toneHeader}>
                  <View style={styles.toneInfo}>
                    <Text style={[
                      styles.toneLabel,
                      currentTone === tone.value && styles.toneLabelSelected
                    ]}>
                      {tone.label}
                    </Text>
                    <Text style={styles.toneDescription}>{tone.description}</Text>
                  </View>
                  {currentTone === tone.value && (
                    <View style={styles.checkmark}>
                      <Text style={styles.checkmarkText}>✓</Text>
                    </View>
                  )}
                </View>
                <Text style={styles.toneExample}>{tone.example}</Text>
              </TouchableOpacity>
            ))}
          </View>

          <TouchableOpacity
            style={styles.previewButton}
            onPress={() => onPreviewJournal(currentTone)}
          >
            <Text style={styles.previewButtonText}>
              Preview with {TONE_OPTIONS.find(t => t.value === currentTone)?.label} Tone
            </Text>
          </TouchableOpacity>
        </View>

        {/* Privacy & Sync Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Privacy & Data</Text>

          <View style={styles.settingRow}>
            <View style={styles.settingInfo}>
              <Text style={styles.settingLabel}>Cloud Sync</Text>
              <Text style={styles.settingDescription}>
                End-to-end encrypted backup
              </Text>
            </View>
            <Switch
              value={cloudSyncEnabled}
              onValueChange={onCloudSyncToggle}
              trackColor={{ false: '#E0E0E0', true: '#34C759' }}
              thumbColor="#FFF"
            />
          </View>

          <View style={styles.infoBox}>
            <Text style={styles.infoIcon}>🔒</Text>
            <Text style={styles.infoText}>
              All data is encrypted on your device. Even we can't read it. Cloud sync uses zero-knowledge encryption.
            </Text>
          </View>
        </View>

        {/* Notifications Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Reminders</Text>
          
          <View style={styles.reminderList}>
            <ReminderRow dayPart="🌅 Morning" time="8:00 AM" enabled={true} />
            <ReminderRow dayPart="☀️ Day" time="1:00 PM" enabled={true} />
            <ReminderRow dayPart="🌆 Evening" time="6:00 PM" enabled={true} />
            <ReminderRow dayPart="🌙 Night" time="9:00 PM" enabled={true} />
          </View>
        </View>

        {/* About Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>About</Text>
          
          <View style={styles.aboutRow}>
            <Text style={styles.aboutLabel}>Version</Text>
            <Text style={styles.aboutValue}>1.0.0</Text>
          </View>
          
          <View style={styles.aboutRow}>
            <Text style={styles.aboutLabel}>Account</Text>
            <Text style={styles.aboutValue}>Premium 💎</Text>
          </View>
        </View>

        <View style={styles.bottomPadding} />
      </ScrollView>
    </View>
  );
};

const ReminderRow: React.FC<{
  dayPart: string;
  time: string;
  enabled: boolean;
}> = ({ dayPart, time, enabled }) => (
  <View style={styles.reminderRow}>
    <Text style={styles.reminderDayPart}>{dayPart}</Text>
    <Text style={styles.reminderTime}>{time}</Text>
  </View>
);

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FAFBFC',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 20,
    backgroundColor: '#FFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E8E8E8',
  },
  backButton: {
    fontSize: 16,
    fontWeight: '600',
    color: '#007AFF',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1A1A1A',
  },
  spacer: {
    width: 50,
  },
  content: {
    flex: 1,
  },
  section: {
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginTop: 20,
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1A1A1A',
    marginBottom: 6,
  },
  sectionSubtitle: {
    fontSize: 14,
    color: '#999',
    marginBottom: 16,
  },
  toneList: {
    gap: 12,
  },
  toneCard: {
    backgroundColor: '#F9F9F9',
    borderRadius: 12,
    padding: 16,
    borderWidth: 2,
    borderColor: '#E8E8E8',
  },
  toneCardSelected: {
    backgroundColor: '#E5F1FF',
    borderColor: '#007AFF',
  },
  toneHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  toneInfo: {
    flex: 1,
  },
  toneLabel: {
    fontSize: 16,
    fontWeight: '700',
    color: '#333',
    marginBottom: 4,
  },
  toneLabelSelected: {
    color: '#007AFF',
  },
  toneDescription: {
    fontSize: 13,
    color: '#666',
  },
  checkmark: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkmarkText: {
    color: '#FFF',
    fontSize: 14,
    fontWeight: '700',
  },
  toneExample: {
    fontSize: 12,
    fontStyle: 'italic',
    color: '#999',
    lineHeight: 18,
  },
  previewButton: {
    marginTop: 16,
    backgroundColor: '#007AFF',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  previewButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FFF',
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
  },
  settingInfo: {
    flex: 1,
  },
  settingLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  settingDescription: {
    fontSize: 13,
    color: '#666',
  },
  infoBox: {
    flexDirection: 'row',
    backgroundColor: '#F5F8FF',
    borderRadius: 12,
    padding: 16,
    marginTop: 16,
    borderWidth: 1,
    borderColor: '#D0E4FF',
    gap: 12,
  },
  infoIcon: {
    fontSize: 20,
  },
  infoText: {
    flex: 1,
    fontSize: 13,
    color: '#0066CC',
    lineHeight: 19,
  },
  reminderList: {
    gap: 12,
  },
  reminderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#F9F9F9',
    borderRadius: 12,
    padding: 16,
  },
  reminderDayPart: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  reminderTime: {
    fontSize: 14,
    color: '#007AFF',
  },
  aboutRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  aboutLabel: {
    fontSize: 14,
    color: '#666',
  },
  aboutValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  bottomPadding: {
    height: 40,
  },
});

