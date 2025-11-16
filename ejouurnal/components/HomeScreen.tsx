import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Dimensions,
} from 'react-native';
import { DayPart, DailyScores, WeeklySummary, WeeklyIntention } from '../types/fulfillment';

const { width } = Dimensions.get('window');

interface HomeScreenProps {
  onCheckInStart: (dayPart: DayPart) => void;
  onViewLineage: () => void;
  onWeeklyRitual: () => void;
  onViewAddDetails?: () => void;
  onViewJournal?: () => void;
  onViewSettings?: () => void;
  dailyScores?: DailyScores;
  weeklySummary?: WeeklySummary;
  completedDayParts: DayPart[];
  hasJournal?: boolean;
  isPremium?: boolean;
  userId?: string;
  currentIntention?: WeeklyIntention;
}

const DAYPART_INFO = [
  { part: 'morning' as DayPart, emoji: '🌅', label: 'Morning', time: '6-10am' },
  { part: 'day' as DayPart, emoji: '☀️', label: 'Day', time: '10am-4pm' },
  { part: 'evening' as DayPart, emoji: '🌆', label: 'Evening', time: '4-8pm' },
  { part: 'night' as DayPart, emoji: '🌙', label: 'Night', time: '8pm+' },
];

export const HomeScreen: React.FC<HomeScreenProps> = ({
  onCheckInStart,
  onViewLineage,
  onWeeklyRitual,
  onViewAddDetails,
  onViewJournal,
  onViewSettings,
  dailyScores,
  weeklySummary,
  completedDayParts,
  hasJournal,
  isPremium,
  userId,
  currentIntention,
}) => {
  console.log('🏠 HomeScreen V2 rendering with purple theme!');
  console.log('🎯 Current intention:', currentIntention?.intention);
  
  const [insights, setInsights] = useState<any[]>([]);
  const [loadingInsights, setLoadingInsights] = useState(false);

  useEffect(() => {
    if (userId && completedDayParts.length >= 2) {
      loadInsights();
    }
  }, [userId, completedDayParts.length]);

  const loadInsights = async () => {
    if (!userId) return;
    
    try {
      setLoadingInsights(true);
      const response = await fetch(`http://localhost:3005/api/insights/${userId}?limit=3`);
      const data = await response.json();
      if (data.success) {
        setInsights(data.insights);
      }
    } catch (error) {
      console.error('Error loading insights:', error);
    } finally {
      setLoadingInsights(false);
    }
  };

  const getCurrentDayPart = (): DayPart => {
    const hour = new Date().getHours();
    if (hour >= 6 && hour < 10) return 'morning';
    if (hour >= 10 && hour < 16) return 'day';
    if (hour >= 16 && hour < 20) return 'evening';
    return 'night';
  };

  const suggestedDayPart = getCurrentDayPart();

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Text style={styles.greeting}>How's your day unfolding?</Text>
          <Text style={styles.subtitle}>Living your intention today</Text>
        </View>
        {onViewSettings && (
          <TouchableOpacity 
            style={styles.settingsButton} 
            onPress={onViewSettings}
            activeOpacity={0.7}
          >
            <Text style={styles.settingsIcon}>⚙️</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* Weekly Intention Card */}
      {currentIntention && (
        <TouchableOpacity 
          style={styles.intentionCard}
          onPress={onWeeklyRitual}
          activeOpacity={0.8}
        >
          <View style={styles.intentionHeader}>
            <Text style={styles.intentionLabel}>🎯 This Week's Intention</Text>
            <Text style={styles.intentionEdit}>Edit →</Text>
          </View>
          <Text style={styles.intentionText}>"{currentIntention.intention}"</Text>
          
          {/* Micro-Moves Progress */}
          <View style={styles.microMovesProgress}>
            <Text style={styles.microMovesLabel}>Micro-Moves Today:</Text>
            <View style={styles.microMovesList}>
              {currentIntention.microMoves.map((move, index) => (
                <View key={move.id} style={styles.microMoveItem}>
                  <Text style={styles.microMoveNumber}>{index + 1}.</Text>
                  <Text style={styles.microMoveText} numberOfLines={1}>{move.description}</Text>
                  <View style={[styles.microMoveCheck, move.completed && styles.microMoveCheckCompleted]}>
                    <Text style={styles.microMoveCheckText}>{move.completed ? '✓' : '○'}</Text>
                  </View>
                </View>
              ))}
            </View>
          </View>
        </TouchableOpacity>
      )}

      {/* Day Part Chips */}
      <View style={styles.dayPartsContainer}>
        {DAYPART_INFO.map((dp) => {
          const isCompleted = completedDayParts.includes(dp.part);
          const isSuggested = dp.part === suggestedDayPart && !isCompleted;
          
          return (
            <TouchableOpacity
              key={dp.part}
              style={[
                styles.dayPartChip,
                isCompleted && styles.dayPartChipCompleted,
                isSuggested && styles.dayPartChipSuggested,
              ]}
              onPress={() => onCheckInStart(dp.part)}
              activeOpacity={0.7}
            >
              <Text style={styles.dayPartEmoji}>{dp.emoji}</Text>
              <Text style={[
                styles.dayPartLabel,
                isCompleted && styles.dayPartLabelCompleted,
              ]}>
                {dp.label}
              </Text>
              <Text style={styles.dayPartTime}>{dp.time}</Text>
              {isCompleted && (
                <View style={styles.checkmark}>
                  <Text style={styles.checkmarkText}>✓</Text>
                </View>
              )}
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Today's Scores */}
      {dailyScores && (
        <View style={styles.scoresCard}>
          <Text style={styles.cardTitle}>Today's Fulfillment</Text>
          
          <View style={styles.mainScore}>
            <Text style={styles.mainScoreValue}>
              {Math.round(dailyScores.fulfillmentScore)}
            </Text>
            <Text style={styles.mainScoreLabel}>Overall</Text>
          </View>

          <View style={styles.scoreGrid}>
            <ScorePill label="Body" score={dailyScores.bodyScore} color="#FF6B6B" />
            <ScorePill label="Mind" score={dailyScores.mindScore} color="#4ECDC4" />
            <ScorePill label="Soul" score={dailyScores.soulScore} color="#95E1D3" />
            <ScorePill label="Purpose" score={dailyScores.purposeScore} color="#FFD93D" />
          </View>

          {dailyScores.isMeaningfulDay && (
            <View style={styles.meaningfulBadge}>
              <Text style={styles.meaningfulText}>✨ Meaningful Day</Text>
            </View>
          )}
        </View>
      )}

      {/* Insights Section */}
      {insights.length > 0 && (
        <View style={styles.insightsCard}>
          <View style={styles.insightsHeader}>
            <Text style={styles.cardTitle}>💡 Your Insights</Text>
            <TouchableOpacity onPress={onViewLineage}>
              <Text style={styles.linkText}>See All →</Text>
            </TouchableOpacity>
          </View>

          {insights.slice(0, 2).map((insight, index) => (
            <View key={insight.id || index} style={styles.insightItem}>
              <View style={styles.insightHeader}>
                <Text style={styles.insightType}>
                  {insight.insight_type === 'same-day' && '⚡'}
                  {insight.insight_type === 'lag' && '📅'}
                  {insight.insight_type === 'breakpoint' && '🎯'}
                  {insight.insight_type === 'purpose-path' && '🔮'}
                  {insight.insight_type === 'premium_gate' && '🔒'}
                </Text>
                <View 
                  style={[
                    styles.confidenceBadge,
                    { backgroundColor: insight.confidence === 'high' ? '#34C75920' : '#FFD93D20' }
                  ]}
                >
                  <Text style={[
                    styles.confidenceText,
                    { color: insight.confidence === 'high' ? '#34C759' : '#FFD93D' }
                  ]}>
                    {insight.confidence}
                  </Text>
                </View>
              </View>
              <Text style={styles.insightTitle}>{insight.title}</Text>
              <Text style={styles.insightDescription} numberOfLines={2}>
                {insight.description}
              </Text>
              {insight.impact > 0 && (
                <Text style={styles.insightImpact}>Impact: +{insight.impact} points</Text>
              )}
            </View>
          ))}

          {insights.length > 2 && (
            <TouchableOpacity onPress={onViewLineage} style={styles.viewMoreInsights}>
              <Text style={styles.viewMoreText}>
                +{insights.length - 2} more insights
              </Text>
            </TouchableOpacity>
          )}
        </View>
      )}

      {/* Weekly Summary */}
      {weeklySummary && (
        <View style={styles.weeklyCard}>
          <View style={styles.weeklyHeader}>
            <Text style={styles.cardTitle}>This Week</Text>
            <TouchableOpacity onPress={onWeeklyRitual}>
              <Text style={styles.linkText}>Review →</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.mdwContainer}>
            <Text style={styles.mdwNumber}>
              {weeklySummary.meaningfulDaysCount}
            </Text>
            <Text style={styles.mdwLabel}>Meaningful Days</Text>
          </View>

          <View style={styles.weeklyStats}>
            <StatItem
              label="Purpose"
              value={`${Math.round(weeklySummary.purposeAdherence)}%`}
              subtext="micro-moves"
            />
            <StatItem
              label="Social"
              value={weeklySummary.socialMinutesDelta > 0 ? '+' : ''}
              valueExtra={`${Math.round(weeklySummary.socialMinutesDelta)}m`}
              subtext="vs baseline"
            />
          </View>
        </View>
      )}

      {/* Quick Actions */}
      {onViewAddDetails && completedDayParts.length > 0 && (
        <TouchableOpacity style={styles.addDetailsButton} onPress={onViewAddDetails}>
          <View style={styles.addDetailsContent}>
            <Text style={styles.addDetailsEmoji}>📊</Text>
            <View style={styles.addDetailsText}>
              <Text style={styles.addDetailsTitle}>Add Details (Optional)</Text>
              <Text style={styles.addDetailsSubtitle}>
                Sleep, food, exercise for richer insights
              </Text>
            </View>
          </View>
          <Text style={styles.arrow}>→</Text>
        </TouchableOpacity>
      )}

      <TouchableOpacity style={styles.lineageButton} onPress={onViewLineage}>
        <View style={styles.lineageButtonContent}>
          <Text style={styles.lineageButtonEmoji}>🔗</Text>
          <View style={styles.lineageButtonText}>
            <Text style={styles.lineageButtonTitle}>View Fulfillment Lineage</Text>
            <Text style={styles.lineageButtonSubtitle}>
              See how your choices connect
            </Text>
          </View>
        </View>
        <Text style={styles.arrow}>→</Text>
      </TouchableOpacity>

      <View style={styles.bottomPadding} />
    </ScrollView>
  );
};

const ScorePill: React.FC<{ label: string; score: number; color: string }> = ({
  label,
  score,
  color,
}) => (
  <View style={styles.scorePill}>
    <Text style={styles.scorePillLabel}>{label}</Text>
    <View style={[styles.scorePillBar, { backgroundColor: color + '20' }]}>
      <View
        style={[
          styles.scorePillFill,
          { width: `${score}%`, backgroundColor: color },
        ]}
      />
    </View>
    <Text style={styles.scorePillValue}>{Math.round(score)}</Text>
  </View>
);

const StatItem: React.FC<{
  label: string;
  value: string;
  valueExtra?: string;
  subtext: string;
}> = ({ label, value, valueExtra, subtext }) => (
  <View style={styles.statItem}>
    <Text style={styles.statValue}>
      {value}
      {valueExtra && <Text style={styles.statValueExtra}>{valueExtra}</Text>}
    </Text>
    <Text style={styles.statLabel}>{label}</Text>
    <Text style={styles.statSubtext}>{subtext}</Text>
  </View>
);

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F3FF', // V2: Light purple background
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingHorizontal: 24,
    paddingTop: 24,
    paddingBottom: 20,
  },
  headerLeft: {
    flex: 1,
  },
  settingsButton: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: '#FFFFFF',
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 12,
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 4,
    elevation: 3,
  },
  settingsIcon: {
    fontSize: 24,
  },
  greeting: {
    fontSize: 30,
    fontWeight: '800',
    color: '#1F2937',
    marginBottom: 6,
  },
  subtitle: {
    fontSize: 16,
    color: '#6B7280',
    fontWeight: '500',
  },
  dayPartsContainer: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    marginBottom: 20,
  },
  dayPartChip: {
    flex: 1,
    marginHorizontal: 4,
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 14,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#E5E7EB',
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.08,
    shadowRadius: 6,
    elevation: 3,
  },
  dayPartChipCompleted: {
    backgroundColor: '#D1FAE5',
    borderColor: '#10B981',
    shadowColor: '#10B981',
    shadowOpacity: 0.2,
  },
  dayPartChipSuggested: {
    borderColor: '#A78BFA',
    borderWidth: 3,
    shadowColor: '#A78BFA',
    shadowOpacity: 0.25,
  },
  dayPartEmoji: {
    fontSize: 28,
    marginBottom: 6,
  },
  dayPartLabel: {
    fontSize: 13,
    fontWeight: '700',
    color: '#374151',
    marginBottom: 3,
  },
  dayPartLabelCompleted: {
    color: '#059669',
  },
  dayPartTime: {
    fontSize: 10,
    color: '#9CA3AF',
    fontWeight: '500',
  },
  checkmark: {
    position: 'absolute',
    top: 6,
    right: 6,
    backgroundColor: '#10B981',
    width: 20,
    height: 20,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#10B981',
    shadowOpacity: 0.4,
    shadowRadius: 3,
    elevation: 2,
  },
  checkmarkText: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '800',
  },
  scoresCard: {
    backgroundColor: '#FFFFFF',
    marginHorizontal: 16,
    marginBottom: 20,
    borderRadius: 24,
    padding: 24,
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.12,
    shadowRadius: 12,
    elevation: 4,
    borderWidth: 1,
    borderColor: '#E9D5FF',
  },
  cardTitle: {
    fontSize: 19,
    fontWeight: '800',
    color: '#1F2937',
    marginBottom: 18,
  },
  mainScore: {
    alignItems: 'center',
    marginBottom: 24,
    paddingVertical: 12,
  },
  mainScoreValue: {
    fontSize: 64,
    fontWeight: '900',
    color: '#8B5CF6',
  },
  mainScoreLabel: {
    fontSize: 15,
    color: '#6B7280',
    marginTop: 6,
    fontWeight: '600',
  },
  scoreGrid: {
    gap: 12,
  },
  scorePill: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  scorePillLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    width: 70,
  },
  scorePillBar: {
    flex: 1,
    height: 24,
    borderRadius: 12,
    overflow: 'hidden',
    marginRight: 10,
  },
  scorePillFill: {
    height: '100%',
    borderRadius: 12,
  },
  scorePillValue: {
    fontSize: 14,
    fontWeight: '700',
    color: '#333',
    width: 35,
    textAlign: 'right',
  },
  meaningfulBadge: {
    marginTop: 18,
    backgroundColor: '#FEF3C7',
    paddingVertical: 12,
    paddingHorizontal: 18,
    borderRadius: 16,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#FCD34D',
    shadowColor: '#F59E0B',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 2,
  },
  meaningfulText: {
    fontSize: 17,
    fontWeight: '700',
    color: '#D97706',
  },
  weeklyCard: {
    backgroundColor: '#FFFFFF',
    marginHorizontal: 16,
    marginBottom: 20,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: '#E9D5FF',
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
  },
  weeklyHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  linkText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#007AFF',
  },
  mdwContainer: {
    alignItems: 'center',
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
    marginBottom: 16,
  },
  mdwNumber: {
    fontSize: 48,
    fontWeight: '800',
    color: '#34C759',
  },
  mdwLabel: {
    fontSize: 16,
    color: '#666',
    marginTop: 4,
  },
  weeklyStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: 28,
    fontWeight: '700',
    color: '#333',
  },
  statValueExtra: {
    fontSize: 20,
  },
  statLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
    marginTop: 4,
  },
  statSubtext: {
    fontSize: 11,
    color: '#999',
  },
  addDetailsButton: {
    backgroundColor: '#EDE9FE',
    marginHorizontal: 16,
    marginBottom: 16,
    borderRadius: 20,
    padding: 20,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderWidth: 2,
    borderColor: '#C4B5FD',
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
    elevation: 3,
  },
  addDetailsContent: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  addDetailsEmoji: {
    fontSize: 36,
    marginRight: 16,
  },
  addDetailsText: {
    flex: 1,
  },
  addDetailsTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2E7D32',
    marginBottom: 2,
  },
  addDetailsSubtitle: {
    fontSize: 13,
    color: '#4CAF50',
  },
  lineageButton: {
    backgroundColor: '#F5F5F7',
    marginHorizontal: 16,
    marginBottom: 16,
    borderRadius: 16,
    padding: 20,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  lineageButtonContent: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  lineageButtonEmoji: {
    fontSize: 32,
    marginRight: 16,
  },
  lineageButtonText: {
    flex: 1,
  },
  lineageButtonTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1A1A1A',
    marginBottom: 2,
  },
  lineageButtonSubtitle: {
    fontSize: 13,
    color: '#666',
  },
  arrow: {
    fontSize: 20,
    color: '#999',
  },
  insightsCard: {
    backgroundColor: '#FFFFFF',
    marginHorizontal: 16,
    marginBottom: 20,
    borderRadius: 24,
    padding: 24,
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.12,
    shadowRadius: 12,
    elevation: 4,
    borderWidth: 1,
    borderColor: '#E9D5FF',
  },
  insightsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  insightItem: {
    backgroundColor: '#F9F9FB',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderLeftWidth: 4,
    borderLeftColor: '#4ECDC4',
  },
  insightHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  insightType: {
    fontSize: 20,
    marginRight: 8,
  },
  confidenceBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  confidenceText: {
    fontSize: 11,
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  insightTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#1A1A1A',
    marginBottom: 6,
  },
  insightDescription: {
    fontSize: 13,
    color: '#666',
    lineHeight: 18,
  },
  insightImpact: {
    fontSize: 12,
    fontWeight: '600',
    color: '#34C759',
    marginTop: 8,
  },
  viewMoreInsights: {
    alignItems: 'center',
    paddingVertical: 8,
  },
  viewMoreText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#007AFF',
  },
  bottomPadding: {
    height: 40,
  },
  // Intention Card Styles
  intentionCard: {
    backgroundColor: '#FFFFFF',
    marginHorizontal: 16,
    marginBottom: 20,
    borderRadius: 24,
    padding: 20,
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 12,
    elevation: 4,
    borderWidth: 2,
    borderColor: '#C4B5FD',
  },
  intentionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  intentionLabel: {
    fontSize: 14,
    fontWeight: '700',
    color: '#7C3AED',
  },
  intentionEdit: {
    fontSize: 14,
    fontWeight: '700',
    color: '#8B5CF6',
  },
  intentionText: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1F2937',
    fontStyle: 'italic',
    lineHeight: 26,
    marginBottom: 16,
  },
  microMovesProgress: {
    backgroundColor: '#F5F3FF',
    borderRadius: 12,
    padding: 12,
  },
  microMovesLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: '#6B7280',
    marginBottom: 10,
  },
  microMovesList: {
    gap: 8,
  },
  microMoveItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  microMoveNumber: {
    fontSize: 13,
    fontWeight: '700',
    color: '#8B5CF6',
    width: 18,
  },
  microMoveText: {
    flex: 1,
    fontSize: 13,
    color: '#374151',
    fontWeight: '500',
  },
  microMoveCheck: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: '#D1D5DB',
    justifyContent: 'center',
    alignItems: 'center',
  },
  microMoveCheckCompleted: {
    backgroundColor: '#10B981',
    borderColor: '#10B981',
  },
  microMoveCheckText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#6B7280',
  },
});

