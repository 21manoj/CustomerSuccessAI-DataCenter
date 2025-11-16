import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  Platform,
} from 'react-native';
import { WeeklySummary, WeeklyIntention, MicroMove } from '../types/fulfillment';
import { suggestMicroMoves, rankByRelevance, groupByTier, MicroMove as LibraryMicroMove } from '../services/MicroMoveLibrary';

interface WeeklyRitualProps {
  weeklySummary: WeeklySummary;
  currentIntention?: WeeklyIntention;
  onSaveIntention: (intention: string, microMoves: string[], antiGlitter: string) => void;
  onBack: () => void;
}

const ANTI_GLITTER_EXPERIMENTS = [
  '30-min morning no-feed',
  'Grayscale home screen',
  'No phone first hour after waking',
  'Social apps only after 6pm',
  '10-min no-scroll before bed',
  'Leave phone outside bedroom',
  'One social app at a time',
];

export const WeeklyRitual: React.FC<WeeklyRitualProps> = ({
  weeklySummary,
  currentIntention,
  onSaveIntention,
  onBack,
}) => {
  const [intention, setIntention] = useState(currentIntention?.intention || '');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState<LibraryMicroMove[]>([]);
  const [selectedMoves, setSelectedMoves] = useState<string[]>([
    currentIntention?.microMoves[0]?.description || '',
    currentIntention?.microMoves[1]?.description || '',
    currentIntention?.microMoves[2]?.description || '',
  ]);
  const [customMove, setCustomMove] = useState('');
  const [selectedAntiGlitter, setSelectedAntiGlitter] = useState(
    currentIntention?.antiGlitterExperiment || ''
  );

  // Analyze intention and generate suggestions when user types
  useEffect(() => {
    console.log('📝 Intention changed:', intention, 'Length:', intention.length);
    
    if (intention.length > 15) {
      console.log('✅ Length > 15, generating suggestions...');
      const moves = suggestMicroMoves(intention);
      const ranked = rankByRelevance(moves, intention);
      setSuggestions(ranked.slice(0, 10));
      setShowSuggestions(true);
      console.log('💜 Suggestions set, showSuggestions:', true);
    } else {
      console.log('⏸️ Length <= 15, hiding suggestions');
      setShowSuggestions(false);
    }
  }, [intention]);

  const toggleMoveSelection = (moveText: string) => {
    const currentIndex = selectedMoves.findIndex(m => m === moveText);
    
    if (currentIndex >= 0) {
      // Already selected, remove it
      const newMoves = [...selectedMoves];
      newMoves[currentIndex] = '';
      setSelectedMoves(newMoves);
    } else {
      // Not selected, add to first empty slot
      const emptyIndex = selectedMoves.findIndex(m => !m);
      if (emptyIndex >= 0) {
        const newMoves = [...selectedMoves];
        newMoves[emptyIndex] = moveText;
        setSelectedMoves(newMoves);
      } else {
        // All slots full
        if (Platform.OS === 'web') {
          alert('You can only select 3 micro-moves. Deselect one first.');
        } else {
          Alert.alert('Limit Reached', 'You can only select 3 micro-moves. Deselect one first.');
        }
      }
    }
  };

  const addCustomMove = () => {
    if (!customMove.trim()) {
      return;
    }
    
    const emptyIndex = selectedMoves.findIndex(m => !m);
    if (emptyIndex >= 0) {
      const newMoves = [...selectedMoves];
      newMoves[emptyIndex] = customMove.trim();
      setSelectedMoves(newMoves);
      setCustomMove('');
    } else {
      if (Platform.OS === 'web') {
        alert('You can only select 3 micro-moves. Remove one first.');
      } else {
        Alert.alert('Limit Reached', 'You can only select 3 micro-moves. Remove one first.');
      }
    }
  };

  const handleSave = () => {
    if (!intention.trim()) {
      if (Platform.OS === 'web') {
        alert('Please set your weekly intention');
      } else {
        Alert.alert('Missing Intention', 'Please set your weekly intention');
      }
      return;
    }

    const filledMoves = selectedMoves.filter(m => m.trim());
    if (filledMoves.length < 3) {
      if (Platform.OS === 'web') {
        alert(`Please select ${3 - filledMoves.length} more micro-move${3 - filledMoves.length > 1 ? 's' : ''}`);
      } else {
        Alert.alert('Missing Micro-moves', `Please select ${3 - filledMoves.length} more micro-move${3 - filledMoves.length > 1 ? 's' : ''}`);
      }
      return;
    }

    onSaveIntention(
      intention,
      selectedMoves.filter(m => m.trim()),
      selectedAntiGlitter
    );
  };

  const getMDWTrend = () => {
    const current = weeklySummary.meaningfulDaysCount;
    // In a real app, compare to previous week
    return current >= 3 ? '📈' : current >= 2 ? '→' : '📉';
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} style={styles.backButton}>
          <Text style={styles.backText}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Weekly Ritual</Text>
        <TouchableOpacity onPress={handleSave} style={styles.saveButton}>
          <Text style={styles.saveText}>Save</Text>
        </TouchableOpacity>
      </View>

      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Last Week Review */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Last Week's Fulfillment</Text>
          
          <View style={styles.reviewCard}>
            <View style={styles.mdwDisplay}>
              <View style={styles.mdwRow}>
                <Text style={styles.mdwNumber}>
                  {weeklySummary.meaningfulDaysCount}
                </Text>
                <Text style={styles.mdwTrend}>{getMDWTrend()}</Text>
              </View>
              <Text style={styles.mdwLabel}>Meaningful Days</Text>
            </View>

            <View style={styles.scoreRow}>
              <ScoreItem
                label="Body"
                value={Math.round(weeklySummary.avgBodyScore)}
                color="#FF6B6B"
              />
              <ScoreItem
                label="Mind"
                value={Math.round(weeklySummary.avgMindScore)}
                color="#4ECDC4"
              />
              <ScoreItem
                label="Soul"
                value={Math.round(weeklySummary.avgSoulScore)}
                color="#95E1D3"
              />
              <ScoreItem
                label="Purpose"
                value={Math.round(weeklySummary.avgPurposeScore)}
                color="#FFD93D"
              />
            </View>
          </View>

          {/* Top Insights */}
          {weeklySummary.topInsights.length > 0 && (
            <View style={styles.insightsContainer}>
              <Text style={styles.subsectionTitle}>Key Insights</Text>
              {weeklySummary.topInsights.slice(0, 2).map((insight) => (
                <View key={insight.id} style={styles.miniInsight}>
                  <Text style={styles.insightIcon}>💡</Text>
                  <Text style={styles.insightText}>{insight.title}</Text>
                </View>
              ))}
            </View>
          )}
        </View>

        {/* Set This Week's Intention */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>This Week's Intention</Text>
          <Text style={styles.sectionHint}>
            One sentence. What matters most this week?
          </Text>

          <TextInput
            style={styles.intentionInput}
            value={intention}
            onChangeText={setIntention}
            placeholder="e.g., Show up with more presence for my family"
            placeholderTextColor="#999"
            multiline
            maxLength={120}
          />
          <Text style={styles.charCount}>{intention.length}/120</Text>
        </View>

        {/* Define 3 Micro-Moves with AI Suggestions */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>3 Micro-Moves</Text>
          <Text style={styles.sectionHint}>
            Small, specific actions tied to your intention
          </Text>

          {/* Debug Info (Remove after testing) */}
          <View style={{ backgroundColor: '#FFF', padding: 8, marginBottom: 8, borderRadius: 8 }}>
            <Text style={{ fontSize: 11, color: '#666' }}>
              Debug: showSuggestions={showSuggestions ? 'true' : 'false'}, suggestions={suggestions.length}, intentionLength={intention.length}
            </Text>
          </View>

          {/* AI Suggestions */}
          {showSuggestions && suggestions.length > 0 && (
            <>
              {/* AI Analysis Banner */}
              <View style={styles.aiBanner}>
                <Text style={styles.aiIcon}>🤖</Text>
                <View style={styles.aiBannerContent}>
                  <Text style={styles.aiBannerTitle}>AI Analyzed Your Intention</Text>
                  <Text style={styles.aiBannerSubtitle}>
                    Suggesting {suggestions.length} proven micro-moves
                  </Text>
                </View>
              </View>

              {/* Educational Tooltip */}
              <View style={styles.educationalBox}>
                <Text style={styles.educationalTitle}>💡 What makes a good micro-move?</Text>
                <Text style={styles.educationalText}>
                  ✅ GOOD: "10-min morning walk" (Specific, measurable)
                </Text>
                <Text style={styles.educationalText}>
                  ❌ BAD: "Exercise more" (Vague, hard to track)
                </Text>
              </View>

              {/* Top Tier Suggestions */}
              {groupByTier(suggestions).topTier.length > 0 && (
                <>
                  <View style={styles.tierHeader}>
                    <Text style={styles.tierStars}>⭐⭐⭐</Text>
                    <Text style={styles.tierTitle}>MOST EFFECTIVE</Text>
                  </View>
                  {groupByTier(suggestions).topTier.map((move) => (
                    <TouchableOpacity
                      key={move.id}
                      style={[
                        styles.suggestionCard,
                        selectedMoves.includes(move.move) && styles.suggestionCardSelected,
                      ]}
                      onPress={() => toggleMoveSelection(move.move)}
                      activeOpacity={0.7}
                    >
                      <View style={styles.suggestionHeader}>
                        <View
                          style={[
                            styles.checkbox,
                            selectedMoves.includes(move.move) && styles.checkboxSelected,
                          ]}
                        >
                          {selectedMoves.includes(move.move) && (
                            <Text style={styles.checkmark}>✓</Text>
                          )}
                        </View>
                        <Text style={styles.moveName}>{move.move}</Text>
                      </View>
                      <Text style={styles.moveReasoning}>{move.reasoning}</Text>
                      <View style={styles.moveBadges}>
                        <View style={styles.impactBadge}>
                          <Text style={styles.impactText}>
                            +{move.impact} {move.dimension}
                          </Text>
                        </View>
                        <Text style={styles.successRate}>
                          {move.successRate}% success rate
                        </Text>
                      </View>
                    </TouchableOpacity>
                  ))}
                </>
              )}

              {/* Recommended Tier */}
              {groupByTier(suggestions).recommended.length > 0 && (
                <>
                  <View style={styles.tierHeader}>
                    <Text style={styles.tierStars}>⭐⭐</Text>
                    <Text style={styles.tierTitle}>ALSO RECOMMENDED</Text>
                  </View>
                  {groupByTier(suggestions).recommended.slice(0, 3).map((move) => (
                    <TouchableOpacity
                      key={move.id}
                      style={[
                        styles.suggestionCardCompact,
                        selectedMoves.includes(move.move) && styles.suggestionCardSelected,
                      ]}
                      onPress={() => toggleMoveSelection(move.move)}
                      activeOpacity={0.7}
                    >
                      <View
                        style={[
                          styles.checkboxSmall,
                          selectedMoves.includes(move.move) && styles.checkboxSelected,
                        ]}
                      >
                        {selectedMoves.includes(move.move) && (
                          <Text style={styles.checkmarkSmall}>✓</Text>
                        )}
                      </View>
                      <View style={styles.moveCompactContent}>
                        <Text style={styles.moveNameCompact}>{move.move}</Text>
                        <View style={styles.moveBadges}>
                          <View style={styles.impactBadgeSmall}>
                            <Text style={styles.impactTextSmall}>
                              +{move.impact} {move.dimension}
                            </Text>
                          </View>
                          <Text style={styles.successRateSmall}>
                            {move.successRate}% success
                          </Text>
                        </View>
                      </View>
                    </TouchableOpacity>
                  ))}
                </>
              )}
            </>
          )}

          {/* Add Your Own */}
          <View style={styles.customSection}>
            <Text style={styles.customTitle}>➕ Or Add Your Own</Text>
            <View style={styles.customInputRow}>
              <TextInput
                style={styles.customInput}
                value={customMove}
                onChangeText={setCustomMove}
                placeholder="e.g., Evening walk with kids..."
                placeholderTextColor="#999"
              />
              <TouchableOpacity
                style={[styles.addButton, !customMove.trim() && styles.addButtonDisabled]}
                onPress={addCustomMove}
                disabled={!customMove.trim()}
              >
                <Text style={styles.addButtonText}>Add</Text>
              </TouchableOpacity>
            </View>
          </View>

          {/* Selection Summary */}
          <View style={styles.selectionSummary}>
            <Text style={styles.summaryTitle}>
              📊 SELECTED ({selectedMoves.filter((m) => m).length}/3)
            </Text>
            {selectedMoves.map(
              (move, index) =>
                move && (
                  <View key={index} style={styles.selectedMoveItem}>
                    <Text style={styles.selectedMoveNumber}>{index + 1}.</Text>
                    <Text style={styles.selectedMoveText}>{move}</Text>
                    <TouchableOpacity
                      onPress={() => {
                        const newMoves = [...selectedMoves];
                        newMoves[index] = '';
                        setSelectedMoves(newMoves);
                      }}
                    >
                      <Text style={styles.removeButton}>✕</Text>
                    </TouchableOpacity>
                  </View>
                )
            )}
            {selectedMoves.filter((m) => m).length < 3 && (
              <Text style={styles.summaryHint}>
                Select {3 - selectedMoves.filter((m) => m).length} more micro-move
                {3 - selectedMoves.filter((m) => m).length > 1 ? 's' : ''} to continue
              </Text>
            )}
          </View>
        </View>

        {/* Anti-Glitter Experiment */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Anti-Glitter Experiment</Text>
          <Text style={styles.sectionHint}>
            Optional: Try one boundary with comparison-triggering content
          </Text>

          <View style={styles.experimentGrid}>
            {ANTI_GLITTER_EXPERIMENTS.map((experiment) => (
              <TouchableOpacity
                key={experiment}
                style={[
                  styles.experimentChip,
                  selectedAntiGlitter === experiment && styles.experimentChipSelected,
                ]}
                onPress={() =>
                  setSelectedAntiGlitter(
                    selectedAntiGlitter === experiment ? '' : experiment
                  )
                }
                activeOpacity={0.7}
              >
                <Text
                  style={[
                    styles.experimentText,
                    selectedAntiGlitter === experiment && styles.experimentTextSelected,
                  ]}
                >
                  {experiment}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Commitment */}
        <View style={styles.commitmentBox}>
          <Text style={styles.commitmentEmoji}>✨</Text>
          <Text style={styles.commitmentText}>
            This week, I'll check in 4× daily and focus on these intentions.
          </Text>
        </View>

        <View style={styles.bottomPadding} />
      </ScrollView>
    </View>
  );
};

const ScoreItem: React.FC<{ label: string; value: number; color: string }> = ({
  label,
  value,
  color,
}) => (
  <View style={styles.scoreItem}>
    <View style={[styles.scoreDot, { backgroundColor: color }]} />
    <Text style={styles.scoreValue}>{value}</Text>
    <Text style={styles.scoreLabel}>{label}</Text>
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
    paddingVertical: 8,
  },
  backText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#8B5CF6',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1A1A1A',
  },
  saveButton: {
    paddingVertical: 10,
    paddingHorizontal: 18,
    backgroundColor: '#8B5CF6',
    borderRadius: 10,
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 3,
  },
  saveText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  section: {
    paddingHorizontal: 20,
    paddingTop: 24,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1A1A1A',
    marginBottom: 6,
  },
  sectionHint: {
    fontSize: 14,
    color: '#999',
    marginBottom: 16,
  },
  subsectionTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#666',
    marginBottom: 12,
  },
  reviewCard: {
    backgroundColor: '#FFF',
    borderRadius: 20,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  mdwDisplay: {
    alignItems: 'center',
    paddingBottom: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
    marginBottom: 20,
  },
  mdwRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  mdwNumber: {
    fontSize: 56,
    fontWeight: '800',
    color: '#34C759',
  },
  mdwTrend: {
    fontSize: 32,
  },
  mdwLabel: {
    fontSize: 16,
    color: '#666',
    marginTop: 4,
  },
  scoreRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  scoreItem: {
    alignItems: 'center',
  },
  scoreDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginBottom: 6,
  },
  scoreValue: {
    fontSize: 24,
    fontWeight: '700',
    color: '#333',
  },
  scoreLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  insightsContainer: {
    marginTop: 20,
  },
  miniInsight: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: '#FFF',
    padding: 12,
    borderRadius: 12,
    marginBottom: 8,
    gap: 10,
  },
  insightIcon: {
    fontSize: 18,
  },
  insightText: {
    flex: 1,
    fontSize: 14,
    color: '#555',
    lineHeight: 20,
  },
  intentionInput: {
    backgroundColor: '#FAF5FF',
    borderRadius: 16,
    padding: 18,
    fontSize: 16,
    color: '#6B21A8',
    fontWeight: '600',
    fontStyle: 'italic',
    borderWidth: 2,
    borderColor: '#C4B5FD',
    minHeight: 90,
    textAlignVertical: 'top',
  },
  charCount: {
    fontSize: 12,
    color: '#999',
    textAlign: 'right',
    marginTop: 4,
  },
  microMoveContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    gap: 12,
  },
  microMoveNumber: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#007AFF',
    color: '#FFF',
    fontSize: 14,
    fontWeight: '700',
    textAlign: 'center',
    lineHeight: 28,
  },
  microMoveInput: {
    flex: 1,
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 14,
    fontSize: 15,
    color: '#333',
    borderWidth: 1,
    borderColor: '#E8E8E8',
  },
  experimentGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  experimentChip: {
    backgroundColor: '#FFF',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: '#E8E8E8',
  },
  experimentChipSelected: {
    backgroundColor: '#E5F1FF',
    borderColor: '#007AFF',
  },
  experimentText: {
    fontSize: 13,
    fontWeight: '500',
    color: '#666',
  },
  experimentTextSelected: {
    color: '#007AFF',
  },
  commitmentBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F0F9F6',
    marginHorizontal: 20,
    marginTop: 32,
    padding: 20,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#D0F0E4',
    gap: 12,
  },
  commitmentEmoji: {
    fontSize: 32,
  },
  commitmentText: {
    flex: 1,
    fontSize: 15,
    color: '#1A5A3A',
    lineHeight: 22,
  },
  bottomPadding: {
    height: 40,
  },
  // AI Suggestions Styles (V2 Design)
  aiBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#6366F1', // Gradient effect with solid indigo
    borderRadius: 16,
    padding: 14,
    marginBottom: 16,
    shadowColor: '#6366F1',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
    gap: 10,
  },
  aiIcon: {
    fontSize: 28,
  },
  aiBannerContent: {
    flex: 1,
  },
  aiBannerTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  aiBannerSubtitle: {
    fontSize: 13,
    color: '#E0E7FF',
    marginTop: 4,
  },
  educationalBox: {
    backgroundColor: '#DBEAFE',
    borderRadius: 12,
    padding: 14,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#93C5FD',
  },
  educationalTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#1E40AF',
    marginBottom: 8,
  },
  educationalText: {
    fontSize: 12,
    color: '#1E3A8A',
    marginBottom: 4,
    lineHeight: 18,
  },
  tierHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 16,
    marginBottom: 12,
    gap: 8,
  },
  tierStars: {
    fontSize: 16,
  },
  tierTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#666',
  },
  suggestionCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 2,
    borderColor: '#E5E7EB',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  suggestionCardSelected: {
    borderColor: '#A78BFA',
    backgroundColor: '#F5F3FF',
    shadowColor: '#A78BFA',
    shadowOpacity: 0.2,
  },
  suggestionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    gap: 12,
  },
  checkbox: {
    width: 26,
    height: 26,
    borderRadius: 13,
    borderWidth: 2,
    borderColor: '#D1D5DB',
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkboxSelected: {
    backgroundColor: '#8B5CF6',
    borderColor: '#8B5CF6',
  },
  checkmark: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '700',
  },
  moveName: {
    flex: 1,
    fontSize: 15,
    fontWeight: '700',
    color: '#1A1A1A',
  },
  moveReasoning: {
    fontSize: 13,
    color: '#666',
    lineHeight: 18,
    marginBottom: 10,
  },
  moveBadges: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  impactBadge: {
    backgroundColor: '#D1FAE5',
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  impactText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#065F46',
  },
  successRate: {
    fontSize: 11,
    color: '#6B7280',
  },
  // Compact suggestion styles
  suggestionCardCompact: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 12,
    marginBottom: 8,
    borderWidth: 2,
    borderColor: '#E8E8E8',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  checkboxSmall: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: '#CCC',
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkmarkSmall: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: '700',
  },
  moveCompactContent: {
    flex: 1,
  },
  moveNameCompact: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1A1A1A',
    marginBottom: 4,
  },
  impactBadgeSmall: {
    backgroundColor: '#D4EDDA',
    borderRadius: 10,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  impactTextSmall: {
    fontSize: 10,
    fontWeight: '700',
    color: '#155724',
  },
  successRateSmall: {
    fontSize: 10,
    color: '#999',
  },
  // Custom move section
  customSection: {
    marginTop: 20,
    paddingTop: 20,
    borderTopWidth: 1,
    borderTopColor: '#E8E8E8',
  },
  customTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#666',
    marginBottom: 10,
  },
  customInputRow: {
    flexDirection: 'row',
    gap: 10,
  },
  customInput: {
    flex: 1,
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 14,
    fontSize: 15,
    color: '#333',
    borderWidth: 1,
    borderColor: '#E8E8E8',
  },
  addButton: {
    backgroundColor: '#8B5CF6',
    borderRadius: 12,
    paddingHorizontal: 22,
    paddingVertical: 12,
    justifyContent: 'center',
  },
  addButtonDisabled: {
    backgroundColor: '#D1D5DB',
  },
  addButtonText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '700',
  },
  // Selection summary (V2 Design)
  selectionSummary: {
    backgroundColor: '#F5F3FF',
    borderRadius: 16,
    padding: 18,
    marginTop: 20,
    borderWidth: 2,
    borderColor: '#C4B5FD',
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  summaryTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#7C3AED',
    marginBottom: 14,
  },
  selectedMoveItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF',
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
    gap: 10,
  },
  selectedMoveNumber: {
    fontSize: 14,
    fontWeight: '700',
    color: '#007AFF',
  },
  selectedMoveText: {
    flex: 1,
    fontSize: 13,
    color: '#333',
  },
  removeButton: {
    fontSize: 18,
    color: '#FF3B30',
    fontWeight: '700',
    paddingHorizontal: 8,
  },
  summaryHint: {
    fontSize: 12,
    color: '#999',
    textAlign: 'center',
    marginTop: 4,
  },
});

