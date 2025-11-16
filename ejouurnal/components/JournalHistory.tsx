import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
} from 'react-native';

interface Journal {
  id: string;
  date: Date;
  aiText: string;
  tone: string;
  scores: {
    overall: number;
  };
  isMeaningfulDay: boolean;
}

interface JournalHistoryProps {
  journals: Journal[];
  onBack: () => void;
  onSelectJournal: (journal: Journal) => void;
}

export const JournalHistory: React.FC<JournalHistoryProps> = ({
  journals,
  onBack,
  onSelectJournal
}) => {
  const sortedJournals = [...journals].sort((a, b) => b.date.getTime() - a.date.getTime());

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack}>
          <Text style={styles.backButton}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Journal History</Text>
        <View style={styles.spacer} />
      </View>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={styles.subtitle}>
          {journals.length} {journals.length === 1 ? 'journal' : 'journals'} • This week
        </Text>

        {sortedJournals.length === 0 ? (
          <View style={styles.emptyState}>
            <Text style={styles.emptyEmoji}>📔</Text>
            <Text style={styles.emptyTitle}>No Journals Yet</Text>
            <Text style={styles.emptyText}>
              Complete all 4 check-ins in a day to generate your first AI journal
            </Text>
          </View>
        ) : (
          <View style={styles.journalList}>
            {sortedJournals.map(journal => (
              <TouchableOpacity
                key={journal.id}
                style={styles.journalCard}
                onPress={() => onSelectJournal(journal)}
                activeOpacity={0.7}
              >
                <View style={styles.journalHeader}>
                  <Text style={styles.journalDate}>
                    {journal.date.toLocaleDateString('en-US', {
                      weekday: 'long',
                      month: 'long',
                      day: 'numeric'
                    })}
                  </Text>
                  {journal.isMeaningfulDay && (
                    <Text style={styles.meaningfulStar}>✨</Text>
                  )}
                </View>

                <Text style={styles.journalPreview} numberOfLines={2}>
                  {journal.aiText.substring(0, 120)}...
                </Text>

                <View style={styles.journalFooter}>
                  <View style={styles.scoreInfo}>
                    <Text style={styles.scoreLabel}>Fulfillment:</Text>
                    <Text style={styles.scoreValue}>{journal.scores.overall}</Text>
                  </View>
                  <Text style={styles.readMore}>Read →</Text>
                </View>
              </TouchableOpacity>
            ))}
          </View>
        )}

        <View style={styles.bottomPadding} />
      </ScrollView>
    </View>
  );
};

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
  subtitle: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
    paddingVertical: 16,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 80,
    paddingHorizontal: 40,
  },
  emptyEmoji: {
    fontSize: 64,
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#333',
    marginBottom: 8,
  },
  emptyText: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
    lineHeight: 22,
  },
  journalList: {
    paddingHorizontal: 16,
    gap: 12,
  },
  journalCard: {
    backgroundColor: '#FFF',
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  journalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  journalDate: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1A1A1A',
  },
  meaningfulStar: {
    fontSize: 20,
  },
  journalPreview: {
    fontSize: 14,
    lineHeight: 22,
    color: '#666',
    marginBottom: 16,
  },
  journalFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#F0F0F0',
  },
  scoreInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  scoreLabel: {
    fontSize: 12,
    color: '#999',
  },
  scoreValue: {
    fontSize: 14,
    fontWeight: '700',
    color: '#007AFF',
  },
  readMore: {
    fontSize: 14,
    fontWeight: '600',
    color: '#007AFF',
  },
  bottomPadding: {
    height: 40,
  },
});

