import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Share,
  Alert,
} from 'react-native';

interface JournalViewerProps {
  journal: {
    id: string;
    date: Date;
    aiText: string;
    userEditedText?: string;
    userNotes?: string;
    tone: 'reflective' | 'factual' | 'coach-like' | 'poetic';
    scores: {
      overall: number;
      body: number;
      mind: number;
      soul: number;
      purpose: number;
    };
    isMeaningfulDay: boolean;
  };
  onBack: () => void;
  onSave?: (editedText: string, userNotes: string) => void;
  onRegenerate?: (newTone?: string) => void;
  onExport?: () => void;
}

export const JournalViewer: React.FC<JournalViewerProps> = ({
  journal,
  onBack,
  onSave,
  onRegenerate,
  onExport
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState(journal.userEditedText || journal.aiText);
  const [userNotes, setUserNotes] = useState(journal.userNotes || '');

  const formattedDate = journal.date.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric'
  });

  const handleSave = () => {
    if (onSave) {
      onSave(editedText, userNotes);
      setIsEditing(false);
      Alert.alert('Saved', 'Your journal has been updated');
    }
  };

  const handleShare = async () => {
    try {
      await Share.share({
        message: `My Journal - ${formattedDate}\n\n${editedText}${userNotes ? '\n\nPersonal Notes:\n' + userNotes : ''}`,
        title: 'My Fulfillment Journal'
      });
    } catch (error) {
      console.error('Error sharing:', error);
    }
  };

  const handleExport = () => {
    if (onExport) {
      onExport();
    } else {
      Alert.alert('Export', 'Exporting as PDF...');
    }
  };

  const handleRegenerate = () => {
    Alert.alert(
      'Regenerate Journal',
      'Generate a new version with different insights?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Regenerate',
          onPress: () => onRegenerate && onRegenerate()
        }
      ]
    );
  };

  if (isEditing) {
    return (
      <View style={styles.container}>
        {/* Edit Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => setIsEditing(false)}>
            <Text style={styles.cancelButton}>Cancel</Text>
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Edit Journal</Text>
          <TouchableOpacity onPress={handleSave}>
            <Text style={styles.saveButton}>Save</Text>
          </TouchableOpacity>
        </View>

        <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
          <View style={styles.editSection}>
            <Text style={styles.editLabel}>AI-Generated Text</Text>
            <TextInput
              style={styles.editTextArea}
              value={editedText}
              onChangeText={setEditedText}
              multiline
              textAlignVertical="top"
            />
          </View>

          <View style={styles.editSection}>
            <Text style={styles.editLabel}>Your Personal Notes</Text>
            <TextInput
              style={[styles.editTextArea, styles.notesTextArea]}
              value={userNotes}
              onChangeText={setUserNotes}
              placeholder="Add your own thoughts, feelings, or reflections..."
              placeholderTextColor="#999"
              multiline
              textAlignVertical="top"
            />
          </View>
        </ScrollView>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack}>
          <Text style={styles.backButton}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Today's Journal</Text>
        <TouchableOpacity onPress={() => setIsEditing(true)}>
          <Text style={styles.editButton}>Edit</Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Date & Metadata */}
        <View style={styles.dateHeader}>
          <Text style={styles.date}>{formattedDate}</Text>
          <View style={styles.toneBadge}>
            <Text style={styles.toneBadgeText}>{journal.tone}</Text>
          </View>
        </View>

        {/* Journal Text */}
        <View style={styles.journalContent}>
          <Text style={styles.journalText}>{editedText}</Text>
        </View>

        {/* Scores Summary */}
        <View style={styles.scoresCard}>
          <Text style={styles.scoresTitle}>Day Summary</Text>
          <View style={styles.scoresGrid}>
            <ScoreBadge label="Overall" value={journal.scores.overall} />
            <ScoreBadge label="Body" value={journal.scores.body} color="#FF6B6B" />
            <ScoreBadge label="Mind" value={journal.scores.mind} color="#4ECDC4" />
            <ScoreBadge label="Soul" value={journal.scores.soul} color="#95E1D3" />
            <ScoreBadge label="Purpose" value={journal.scores.purpose} color="#FFD93D" />
          </View>
          {journal.isMeaningfulDay && (
            <View style={styles.meaningfulBadge}>
              <Text style={styles.meaningfulText}>✨ Meaningful Day</Text>
            </View>
          )}
        </View>

        {/* Personal Notes Section */}
        <View style={styles.notesSection}>
          <Text style={styles.notesTitle}>💭 Your Personal Notes</Text>
          {userNotes ? (
            <Text style={styles.notesText}>{userNotes}</Text>
          ) : (
            <TouchableOpacity
              style={styles.addNotesButton}
              onPress={() => setIsEditing(true)}
            >
              <Text style={styles.addNotesText}>+ Add your thoughts...</Text>
            </TouchableOpacity>
          )}
        </View>

        {/* Actions */}
        <View style={styles.actions}>
          <TouchableOpacity style={styles.actionButton} onPress={handleRegenerate}>
            <Text style={styles.actionButtonText}>🔄 Regenerate</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionButton} onPress={handleShare}>
            <Text style={styles.actionButtonText}>📤 Share</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionButton} onPress={handleExport}>
            <Text style={styles.actionButtonText}>📄 Export PDF</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.bottomPadding} />
      </ScrollView>
    </View>
  );
};

const ScoreBadge: React.FC<{
  label: string;
  value: number;
  color?: string;
}> = ({ label, value, color }) => (
  <View style={styles.scoreBadge}>
    <Text style={[styles.scoreBadgeValue, color && { color }]}>{value}</Text>
    <Text style={styles.scoreBadgeLabel}>{label}</Text>
  </View>
);

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F3FF', // V2: Light purple
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 24,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E9D5FF',
  },
  backButton: {
    fontSize: 17,
    fontWeight: '700',
    color: '#8B5CF6',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: '#1F2937',
  },
  editButton: {
    fontSize: 17,
    fontWeight: '700',
    color: '#8B5CF6',
  },
  cancelButton: {
    fontSize: 17,
    fontWeight: '600',
    color: '#6B7280',
  },
  saveButton: {
    fontSize: 17,
    fontWeight: '800',
    color: '#8B5CF6',
  },
  content: {
    flex: 1,
  },
  dateHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 18,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E9D5FF',
  },
  date: {
    fontSize: 15,
    fontWeight: '700',
    color: '#6B7280',
  },
  toneBadge: {
    backgroundColor: '#EDE9FE',
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#C4B5FD',
  },
  toneBadgeText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#7C3AED',
    textTransform: 'capitalize',
  },
  journalContent: {
    backgroundColor: '#FFFFFF',
    marginHorizontal: 16,
    marginTop: 16,
    borderRadius: 24,
    paddingHorizontal: 24,
    paddingVertical: 28,
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 3,
    borderWidth: 1,
    borderColor: '#E9D5FF',
  },
  journalText: {
    fontSize: 16,
    lineHeight: 26,
    color: '#374151',
    fontWeight: '400',
  },
  scoresCard: {
    marginHorizontal: 16,
    marginBottom: 20,
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#E9D5FF',
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 2,
    padding: 20,
  },
  scoresTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#666',
    marginBottom: 12,
    textAlign: 'center',
  },
  scoresGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    justifyContent: 'center',
  },
  scoreBadge: {
    alignItems: 'center',
  },
  scoreBadgeValue: {
    fontSize: 24,
    fontWeight: '800',
    color: '#007AFF',
  },
  scoreBadgeLabel: {
    fontSize: 11,
    color: '#999',
    marginTop: 4,
  },
  meaningfulBadge: {
    marginTop: 16,
    backgroundColor: '#FFF5E6',
    borderRadius: 12,
    padding: 12,
    alignItems: 'center',
  },
  meaningfulText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FF9500',
  },
  notesSection: {
    marginHorizontal: 20,
    marginBottom: 20,
    paddingTop: 20,
    borderTopWidth: 1,
    borderTopColor: '#F0F0F0',
  },
  notesTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#333',
    marginBottom: 12,
  },
  notesText: {
    fontSize: 14,
    lineHeight: 22,
    color: '#555',
    backgroundColor: '#F5F8FF',
    padding: 16,
    borderRadius: 12,
  },
  addNotesButton: {
    backgroundColor: '#F5F8FF',
    borderWidth: 2,
    borderStyle: 'dashed',
    borderColor: '#007AFF',
    borderRadius: 12,
    padding: 20,
    alignItems: 'center',
  },
  addNotesText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#007AFF',
  },
  actions: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    gap: 12,
  },
  actionButton: {
    flex: 1,
    backgroundColor: '#F5F5F7',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  actionButtonText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#333',
  },
  editSection: {
    paddingHorizontal: 20,
    marginBottom: 20,
  },
  editLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: '#666',
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  editTextArea: {
    backgroundColor: '#F9F9F9',
    borderRadius: 12,
    padding: 16,
    fontSize: 14,
    color: '#333',
    borderWidth: 1,
    borderColor: '#E8E8E8',
    minHeight: 200,
  },
  notesTextArea: {
    backgroundColor: '#F5F8FF',
    borderColor: '#007AFF',
    minHeight: 150,
  },
  bottomPadding: {
    height: 40,
  },
});

