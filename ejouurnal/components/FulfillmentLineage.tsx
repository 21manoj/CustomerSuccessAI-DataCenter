import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Dimensions,
} from 'react-native';
import { DailyScores, LineageInsight } from '../types/fulfillment';

const { width } = Dimensions.get('window');

interface FulfillmentLineageProps {
  dailyScores: DailyScores[];
  insights: LineageInsight[];
  onBack: () => void;
}

export const FulfillmentLineage: React.FC<FulfillmentLineageProps> = ({
  dailyScores,
  insights,
  onBack,
}) => {
  const [selectedInsight, setSelectedInsight] = useState<LineageInsight | null>(null);
  const [timeRange, setTimeRange] = useState<'week' | 'month'>('week');

  // Get recent scores for display
  const recentScores = dailyScores.slice(-7);

  const getInsightColor = (type: string) => {
    switch (type) {
      case 'same-day': return '#4ECDC4';
      case 'lag': return '#FFD93D';
      case 'breakpoint': return '#FF6B6B';
      case 'purpose-path': return '#95E1D3';
      default: return '#999';
    }
  };

  const getConfidenceBadge = (confidence: string) => {
    const colors = {
      high: '#34C759',
      medium: '#FFD93D',
      low: '#FF9500',
    };
    return colors[confidence as keyof typeof colors] || '#999';
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} style={styles.backButton}>
          <Text style={styles.backText}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Fulfillment Lineage</Text>
        <View style={styles.spacer} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Subtitle */}
        <Text style={styles.subtitle}>
          See how your choices connect and ripple into calm, strength, and purpose
        </Text>

        {/* Score Timeline */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Your Journey</Text>
            <View style={styles.toggleContainer}>
              <TouchableOpacity
                style={[styles.toggleButton, timeRange === 'week' && styles.toggleButtonActive]}
                onPress={() => setTimeRange('week')}
              >
                <Text style={[styles.toggleText, timeRange === 'week' && styles.toggleTextActive]}>
                  Week
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.toggleButton, timeRange === 'month' && styles.toggleButtonActive]}
                onPress={() => setTimeRange('month')}
              >
                <Text style={[styles.toggleText, timeRange === 'month' && styles.toggleTextActive]}>
                  Month
                </Text>
              </TouchableOpacity>
            </View>
          </View>

          {/* Timeline visualization */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.timeline}>
            {recentScores.map((score, index) => (
              <View key={index} style={styles.timelineDay}>
                <View style={styles.scoreColumns}>
                  <ScoreBar value={score.bodyScore} color="#FF6B6B" />
                  <ScoreBar value={score.mindScore} color="#4ECDC4" />
                  <ScoreBar value={score.soulScore} color="#95E1D3" />
                  <ScoreBar value={score.purposeScore} color="#FFD93D" />
                </View>
                <Text style={styles.timelineDate}>
                  {new Date(score.date).toLocaleDateString('en', { month: 'short', day: 'numeric' })}
                </Text>
                {score.isMeaningfulDay && (
                  <Text style={styles.meaningfulStar}>⭐</Text>
                )}
              </View>
            ))}
          </ScrollView>

          {/* Legend */}
          <View style={styles.legend}>
            <LegendItem color="#FF6B6B" label="Body" />
            <LegendItem color="#4ECDC4" label="Mind" />
            <LegendItem color="#95E1D3" label="Soul" />
            <LegendItem color="#FFD93D" label="Purpose" />
          </View>
        </View>

        {/* Insights */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Key Connections</Text>
          <Text style={styles.sectionSubtitle}>
            Patterns we're seeing in your data
          </Text>

          {insights.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyEmoji}>📊</Text>
              <Text style={styles.emptyText}>
                Keep checking in! We'll show personalized insights after a few days.
              </Text>
            </View>
          ) : (
            insights.map((insight) => (
              <TouchableOpacity
                key={insight.id}
                style={[
                  styles.insightCard,
                  { borderLeftColor: getInsightColor(insight.type), borderLeftWidth: 4 },
                ]}
                onPress={() => setSelectedInsight(insight)}
                activeOpacity={0.7}
              >
                <View style={styles.insightHeader}>
                  <View style={styles.insightTitleRow}>
                    <Text style={styles.insightTitle}>{insight.title}</Text>
                    <View
                      style={[
                        styles.confidenceBadge,
                        { backgroundColor: getConfidenceBadge(insight.confidence) },
                      ]}
                    >
                      <Text style={styles.confidenceText}>
                        {insight.confidence}
                      </Text>
                    </View>
                  </View>
                  <Text style={styles.insightType}>
                    {insight.type.replace('-', ' ').toUpperCase()}
                    {insight.lagDays ? ` • ${insight.lagDays}d lag` : ''}
                  </Text>
                </View>

                <Text style={styles.insightDescription}>{insight.description}</Text>

                <View style={styles.insightMetrics}>
                  <View style={styles.metricFlow}>
                    <Text style={styles.metricText}>{insight.sourceMetric}</Text>
                    <Text style={styles.arrow}>→</Text>
                    <Text style={styles.metricText}>{insight.targetMetric}</Text>
                  </View>
                  <Text style={[
                    styles.impactText,
                    { color: insight.impact > 0 ? '#34C759' : '#FF6B6B' },
                  ]}>
                    {insight.impact > 0 ? '+' : ''}{Math.round(insight.impact)} pts
                  </Text>
                </View>
              </TouchableOpacity>
            ))
          )}
        </View>

        {/* What to try next */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>What to try</Text>
          <View style={styles.suggestionCard}>
            <Text style={styles.suggestionEmoji}>💡</Text>
            <View style={styles.suggestionContent}>
              <Text style={styles.suggestionTitle}>
                Your most impactful pattern
              </Text>
              <Text style={styles.suggestionText}>
                Days with ≥45 active minutes typically show +12 MindScore the next day.
                Try a morning walk tomorrow.
              </Text>
            </View>
          </View>
        </View>

        <View style={styles.bottomPadding} />
      </ScrollView>
    </View>
  );
};

const ScoreBar: React.FC<{ value: number; color: string }> = ({ value, color }) => (
  <View style={styles.scoreBarContainer}>
    <View
      style={[
        styles.scoreBarFill,
        { height: `${value}%`, backgroundColor: color },
      ]}
    />
  </View>
);

const LegendItem: React.FC<{ color: string; label: string }> = ({ color, label }) => (
  <View style={styles.legendItem}>
    <View style={[styles.legendDot, { backgroundColor: color }]} />
    <Text style={styles.legendLabel}>{label}</Text>
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
  subtitle: {
    fontSize: 15,
    color: '#666',
    textAlign: 'center',
    paddingHorizontal: 32,
    paddingVertical: 20,
    lineHeight: 22,
  },
  section: {
    marginBottom: 24,
    paddingHorizontal: 16,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1A1A1A',
  },
  sectionSubtitle: {
    fontSize: 14,
    color: '#999',
    marginTop: 8,
    marginBottom: 16,
  },
  toggleContainer: {
    flexDirection: 'row',
    backgroundColor: '#F0F0F0',
    borderRadius: 8,
    padding: 2,
  },
  toggleButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  toggleButtonActive: {
    backgroundColor: '#FFF',
  },
  toggleText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#666',
  },
  toggleTextActive: {
    color: '#007AFF',
  },
  timeline: {
    marginBottom: 16,
  },
  timelineDay: {
    alignItems: 'center',
    marginRight: 16,
  },
  scoreColumns: {
    flexDirection: 'row',
    height: 120,
    alignItems: 'flex-end',
    gap: 4,
    marginBottom: 8,
  },
  scoreBarContainer: {
    width: 10,
    height: '100%',
    backgroundColor: '#F0F0F0',
    borderRadius: 5,
    overflow: 'hidden',
    justifyContent: 'flex-end',
  },
  scoreBarFill: {
    width: '100%',
    borderRadius: 5,
  },
  timelineDate: {
    fontSize: 11,
    color: '#666',
    fontWeight: '500',
  },
  meaningfulStar: {
    fontSize: 12,
    marginTop: 2,
  },
  legend: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 20,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#F0F0F0',
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  legendLabel: {
    fontSize: 12,
    color: '#666',
    fontWeight: '500',
  },
  insightCard: {
    backgroundColor: '#FFF',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  insightHeader: {
    marginBottom: 12,
  },
  insightTitleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 6,
  },
  insightTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1A1A1A',
    flex: 1,
    marginRight: 12,
  },
  confidenceBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  confidenceText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#FFF',
    textTransform: 'uppercase',
  },
  insightType: {
    fontSize: 11,
    fontWeight: '600',
    color: '#999',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  insightDescription: {
    fontSize: 14,
    color: '#555',
    lineHeight: 20,
    marginBottom: 12,
  },
  insightMetrics: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#F0F0F0',
  },
  metricFlow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  metricText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#333',
  },
  arrow: {
    fontSize: 14,
    color: '#999',
  },
  impactText: {
    fontSize: 15,
    fontWeight: '700',
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyEmoji: {
    fontSize: 48,
    marginBottom: 16,
  },
  emptyText: {
    fontSize: 15,
    color: '#999',
    textAlign: 'center',
    lineHeight: 22,
    paddingHorizontal: 32,
  },
  suggestionCard: {
    flexDirection: 'row',
    backgroundColor: '#FFF9E6',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: '#FFE6A0',
  },
  suggestionEmoji: {
    fontSize: 32,
    marginRight: 12,
  },
  suggestionContent: {
    flex: 1,
  },
  suggestionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1A1A1A',
    marginBottom: 6,
  },
  suggestionText: {
    fontSize: 14,
    color: '#555',
    lineHeight: 20,
  },
  bottomPadding: {
    height: 40,
  },
});

