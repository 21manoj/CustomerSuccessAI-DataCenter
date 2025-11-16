import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Dimensions,
} from 'react-native';

const { width } = Dimensions.get('window');

interface WeeklyReviewProps {
  onBack: () => void;
  onSetIntention: () => void;  // Navigate to WeeklyRitual
  onViewInsights: () => void;   // Navigate to Lineage
  weeklySummary: {
    meaningfulDaysCount: number;
    avgBodyScore: number;
    avgMindScore: number;
    avgSoulScore: number;
    avgPurposeScore: number;
    avgFulfillment: number;
    purposeAdherence: number;
    totalCheckIns: number;
    topInsights: Array<{
      id: string;
      type: string;
      title: string;
      description: string;
      impact: number;
      confidence: string;
    }>;
    previousWeekMDW?: number;
  };
  dailyBreakdown: Array<{
    date: Date;
    dayName: string;
    scores: { body: number; mind: number; soul: number; purpose: number };
    checkInsCompleted: number;
    isMeaningfulDay: boolean;
    highlight?: string;
  }>;
}

export const WeeklyReviewScreen: React.FC<WeeklyReviewProps> = ({
  onBack,
  onSetIntention,
  onViewInsights,
  weeklySummary,
  dailyBreakdown,
}) => {
  const mdwTrend = weeklySummary.previousWeekMDW 
    ? weeklySummary.meaningfulDaysCount - weeklySummary.previousWeekMDW
    : 0;

  const getTrendEmoji = (trend: number) => {
    if (trend > 0) return '📈';
    if (trend < 0) return '📉';
    return '→';
  };

  const getTrendText = (trend: number) => {
    if (trend > 0) return `+${trend} vs last week`;
    if (trend < 0) return `${trend} vs last week`;
    return 'Same as last week';
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack}>
          <Text style={styles.backButton}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Weekly Review</Text>
        <View style={styles.spacer} />
      </View>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Hero Card - Meaningful Days */}
        <View style={styles.heroCard}>
          <Text style={styles.heroLabel}>This Week's Meaningful Days</Text>
          <View style={styles.heroContent}>
            <Text style={styles.heroNumber}>{weeklySummary.meaningfulDaysCount}</Text>
            <Text style={styles.heroDenominator}>/7</Text>
          </View>
          {mdwTrend !== 0 && (
            <View style={styles.trendBadge}>
              <Text style={styles.trendEmoji}>{getTrendEmoji(mdwTrend)}</Text>
              <Text style={[
                styles.trendText,
                mdwTrend > 0 ? styles.trendPositive : styles.trendNegative
              ]}>
                {getTrendText(mdwTrend)}
              </Text>
            </View>
          )}
        </View>

        {/* Average Scores */}
        <View style={styles.scoresCard}>
          <Text style={styles.sectionTitle}>Average Scores</Text>
          <View style={styles.scoreGrid}>
            <ScoreBar label="Body" score={weeklySummary.avgBodyScore} color="#FF6B6B" />
            <ScoreBar label="Mind" score={weeklySummary.avgMindScore} color="#4ECDC4" />
            <ScoreBar label="Soul" score={weeklySummary.avgSoulScore} color="#95E1D3" />
            <ScoreBar label="Purpose" score={weeklySummary.avgPurposeScore} color="#FFD93D" />
          </View>
          <View style={styles.overallScore}>
            <Text style={styles.overallLabel}>Overall Fulfillment</Text>
            <Text style={styles.overallValue}>{Math.round(weeklySummary.avgFulfillment)}</Text>
          </View>
        </View>

        {/* Daily Breakdown */}
        <View style={styles.dailyCard}>
          <Text style={styles.sectionTitle}>Day by Day</Text>
          {dailyBreakdown.map((day, index) => (
            <DayRow key={index} {...day} />
          ))}
        </View>

        {/* Top Insights */}
        {weeklySummary.topInsights && weeklySummary.topInsights.length > 0 && (
          <View style={styles.insightsCard}>
            <View style={styles.insightsHeader}>
              <Text style={styles.sectionTitle}>💡 Key Insights This Week</Text>
              <TouchableOpacity onPress={onViewInsights}>
                <Text style={styles.linkText}>See All →</Text>
              </TouchableOpacity>
            </View>
            
            {weeklySummary.topInsights.slice(0, 3).map((insight, index) => (
              <View key={insight.id || index} style={styles.insightItem}>
                <View style={styles.insightHeader}>
                  <Text style={styles.insightType}>
                    {insight.type === 'same-day' && '⚡'}
                    {insight.type === 'lag' && '📅'}
                    {insight.type === 'breakpoint' && '🎯'}
                    {insight.type === 'purpose-path' && '🔮'}
                  </Text>
                  <Text style={styles.insightTitle}>{insight.title}</Text>
                </View>
                <Text style={styles.insightDescription} numberOfLines={2}>
                  {insight.description}
                </Text>
                {insight.impact > 0 && (
                  <Text style={styles.insightImpact}>Impact: +{insight.impact} points</Text>
                )}
              </View>
            ))}
          </View>
        )}

        {/* What Worked / What Didn't */}
        <View style={styles.reflectionCard}>
          <View style={styles.reflectionSection}>
            <Text style={styles.reflectionTitle}>✨ What Worked</Text>
            <ReflectionPoint text={`${weeklySummary.totalCheckIns} check-ins completed`} positive />
            <ReflectionPoint text={`${Math.round(weeklySummary.purposeAdherence)}% purpose adherence`} positive />
            {weeklySummary.meaningfulDaysCount >= 3 && (
              <ReflectionPoint text={`${weeklySummary.meaningfulDaysCount} meaningful days - great consistency!`} positive />
            )}
          </View>

          <View style={styles.reflectionSection}>
            <Text style={styles.reflectionTitle}>⚠️ Opportunities</Text>
            {weeklySummary.avgBodyScore < 70 && (
              <ReflectionPoint text="Body score below target - focus on sleep/exercise" />
            )}
            {weeklySummary.avgMindScore < 65 && (
              <ReflectionPoint text="Mind clarity could improve - try meditation" />
            )}
            {weeklySummary.meaningfulDaysCount < 3 && (
              <ReflectionPoint text="Aim for 3+ meaningful days this week" />
            )}
          </View>
        </View>

        {/* Action Buttons */}
        <View style={styles.actionsCard}>
          <TouchableOpacity style={styles.primaryButton} onPress={onSetIntention}>
            <Text style={styles.primaryButtonText}>Set This Week's Intention →</Text>
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.secondaryButton} onPress={onViewInsights}>
            <Text style={styles.secondaryButtonText}>View All Insights →</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.bottomPadding} />
      </ScrollView>
    </View>
  );
};

const ScoreBar: React.FC<{ label: string; score: number; color: string }> = ({ label, score, color }) => (
  <View style={styles.scoreBarContainer}>
    <View style={styles.scoreBarHeader}>
      <Text style={styles.scoreBarLabel}>{label}</Text>
      <Text style={styles.scoreBarValue}>{Math.round(score)}</Text>
    </View>
    <View style={styles.scoreBarTrack}>
      <View 
        style={[
          styles.scoreBarFill, 
          { width: `${score}%`, backgroundColor: color }
        ]} 
      />
    </View>
  </View>
);

const DayRow: React.FC<{
  dayName: string;
  date: Date;
  scores: { body: number; mind: number; soul: number; purpose: number };
  checkInsCompleted: number;
  isMeaningfulDay: boolean;
  highlight?: string;
}> = ({ dayName, date, scores, checkInsCompleted, isMeaningfulDay, highlight }) => (
  <View style={styles.dayRow}>
    <View style={styles.dayInfo}>
      <View style={styles.dayNameRow}>
        <Text style={styles.dayName}>{dayName}</Text>
        {isMeaningfulDay && <Text style={styles.dayMDW}>✨</Text>}
      </View>
      <Text style={styles.dayDate}>
        {date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
      </Text>
    </View>
    
    <View style={styles.miniScores}>
      <MiniScore color="#FF6B6B" height={scores.body} />
      <MiniScore color="#4ECDC4" height={scores.mind} />
      <MiniScore color="#95E1D3" height={scores.soul} />
      <MiniScore color="#FFD93D" height={scores.purpose} />
    </View>
    
    <Text style={styles.checkInsCount}>{checkInsCompleted}/4</Text>
    
    {highlight && (
      <View style={styles.highlightBadge}>
        <Text style={styles.highlightText}>{highlight}</Text>
      </View>
    )}
  </View>
);

const MiniScore: React.FC<{ color: string; height: number }> = ({ color, height }) => (
  <View style={styles.miniScoreBar}>
    <View style={[styles.miniScoreFill, { height: `${height}%`, backgroundColor: color }]} />
  </View>
);

const ReflectionPoint: React.FC<{ text: string; positive?: boolean }> = ({ text, positive }) => (
  <View style={styles.reflectionPoint}>
    <Text style={styles.reflectionBullet}>{positive ? '✓' : '•'}</Text>
    <Text style={[styles.reflectionText, positive && styles.reflectionTextPositive]}>
      {text}
    </Text>
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
  heroCard: {
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginTop: 20,
    borderRadius: 24,
    padding: 32,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 16,
    elevation: 4,
  },
  heroLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
    marginBottom: 12,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  heroContent: {
    flexDirection: 'row',
    alignItems: 'baseline',
    marginBottom: 8,
  },
  heroNumber: {
    fontSize: 64,
    fontWeight: '800',
    color: '#34C759',
  },
  heroDenominator: {
    fontSize: 32,
    fontWeight: '600',
    color: '#999',
    marginLeft: 4,
  },
  trendBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F0F9FF',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    gap: 6,
  },
  trendEmoji: {
    fontSize: 16,
  },
  trendText: {
    fontSize: 13,
    fontWeight: '600',
  },
  trendPositive: {
    color: '#34C759',
  },
  trendNegative: {
    color: '#FF6B6B',
  },
  scoresCard: {
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginTop: 16,
    borderRadius: 20,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1A1A1A',
    marginBottom: 16,
  },
  scoreGrid: {
    gap: 12,
  },
  scoreBarContainer: {
    marginBottom: 8,
  },
  scoreBarHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  scoreBarLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  scoreBarValue: {
    fontSize: 14,
    fontWeight: '700',
    color: '#007AFF',
  },
  scoreBarTrack: {
    height: 8,
    backgroundColor: '#F0F0F0',
    borderRadius: 4,
    overflow: 'hidden',
  },
  scoreBarFill: {
    height: '100%',
    borderRadius: 4,
  },
  overallScore: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 16,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#F0F0F0',
  },
  overallLabel: {
    fontSize: 15,
    fontWeight: '700',
    color: '#333',
  },
  overallValue: {
    fontSize: 28,
    fontWeight: '800',
    color: '#007AFF',
  },
  dailyCard: {
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginTop: 16,
    borderRadius: 20,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  dayRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F5F5F5',
  },
  dayInfo: {
    width: 80,
  },
  dayNameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  dayName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  dayMDW: {
    fontSize: 14,
  },
  dayDate: {
    fontSize: 11,
    color: '#999',
    marginTop: 2,
  },
  miniScores: {
    flexDirection: 'row',
    gap: 4,
    flex: 1,
    height: 40,
    alignItems: 'flex-end',
  },
  miniScoreBar: {
    width: 8,
    height: 40,
    backgroundColor: '#F0F0F0',
    borderRadius: 4,
    overflow: 'hidden',
    justifyContent: 'flex-end',
  },
  miniScoreFill: {
    width: '100%',
    borderRadius: 4,
  },
  checkInsCount: {
    fontSize: 13,
    fontWeight: '600',
    color: '#007AFF',
    marginLeft: 12,
    width: 30,
    textAlign: 'right',
  },
  highlightBadge: {
    marginLeft: 8,
    backgroundColor: '#FFF9E6',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  highlightText: {
    fontSize: 10,
    fontWeight: '600',
    color: '#FFB800',
  },
  insightsCard: {
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginTop: 16,
    borderRadius: 20,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  insightsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  linkText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#007AFF',
  },
  insightItem: {
    backgroundColor: '#F9F9FB',
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    borderLeftWidth: 4,
    borderLeftColor: '#4ECDC4',
  },
  insightHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
    gap: 8,
  },
  insightType: {
    fontSize: 18,
  },
  insightTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#1A1A1A',
    flex: 1,
  },
  insightDescription: {
    fontSize: 12,
    color: '#666',
    lineHeight: 17,
    marginBottom: 6,
  },
  insightImpact: {
    fontSize: 11,
    fontWeight: '600',
    color: '#34C759',
  },
  reflectionCard: {
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginTop: 16,
    borderRadius: 20,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  reflectionSection: {
    marginBottom: 16,
  },
  reflectionTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#1A1A1A',
    marginBottom: 12,
  },
  reflectionPoint: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 8,
    gap: 10,
  },
  reflectionBullet: {
    fontSize: 14,
    color: '#999',
    width: 16,
  },
  reflectionText: {
    flex: 1,
    fontSize: 13,
    color: '#666',
    lineHeight: 19,
  },
  reflectionTextPositive: {
    color: '#34C759',
    fontWeight: '500',
  },
  actionsCard: {
    marginHorizontal: 16,
    marginTop: 16,
    gap: 12,
  },
  primaryButton: {
    backgroundColor: '#007AFF',
    borderRadius: 16,
    paddingVertical: 16,
    alignItems: 'center',
    shadowColor: '#007AFF',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  primaryButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFF',
  },
  secondaryButton: {
    backgroundColor: '#F5F5F7',
    borderRadius: 16,
    paddingVertical: 16,
    alignItems: 'center',
  },
  secondaryButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#007AFF',
  },
  bottomPadding: {
    height: 40,
  },
});

export default WeeklyReviewScreen;

