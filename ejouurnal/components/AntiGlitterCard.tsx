import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
} from 'react-native';

interface AntiGlitterCardProps {
  socialMinutesToday: number;
  socialMinutesBaseline: number;
  sparkleCount: number;
  onSparkleTag: () => void;
  onViewDetails: () => void;
}

export const AntiGlitterCard: React.FC<AntiGlitterCardProps> = ({
  socialMinutesToday,
  socialMinutesBaseline,
  sparkleCount,
  onSparkleTag,
  onViewDetails,
}) => {
  const delta = socialMinutesToday - socialMinutesBaseline;
  const isOverBaseline = delta > 0;

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>Content Diet</Text>
        <TouchableOpacity onPress={onViewDetails}>
          <Text style={styles.detailsLink}>Details →</Text>
        </TouchableOpacity>
      </View>

      {/* Social minutes display */}
      <View style={styles.metricsRow}>
        <View style={styles.metric}>
          <Text style={styles.metricValue}>{socialMinutesToday}m</Text>
          <Text style={styles.metricLabel}>Today</Text>
        </View>

        <Text style={styles.vs}>vs</Text>

        <View style={styles.metric}>
          <Text style={styles.metricValue}>{socialMinutesBaseline}m</Text>
          <Text style={styles.metricLabel}>Your baseline</Text>
        </View>

        {delta !== 0 && (
          <View style={[
            styles.deltaBadge,
            { backgroundColor: isOverBaseline ? '#FFF5E6' : '#F0F9F6' },
          ]}>
            <Text style={[
              styles.deltaText,
              { color: isOverBaseline ? '#FF9500' : '#34C759' },
            ]}>
              {isOverBaseline ? '+' : ''}{delta}m
            </Text>
          </View>
        )}
      </View>

      {/* Sparkle trigger button */}
      <View style={styles.sparkleSection}>
        <Text style={styles.sparklePrompt}>
          Felt worse after scrolling?
        </Text>
        <TouchableOpacity
          style={styles.sparkleButton}
          onPress={onSparkleTag}
          activeOpacity={0.7}
        >
          <Text style={styles.sparkleIcon}>✨</Text>
          <Text style={styles.sparkleButtonText}>Tag Sparkle</Text>
        </TouchableOpacity>
      </View>

      {sparkleCount > 0 && (
        <View style={styles.sparkleCount}>
          <Text style={styles.sparkleCountText}>
            {sparkleCount} {sparkleCount === 1 ? 'sparkle' : 'sparkles'} today
          </Text>
        </View>
      )}

      {/* Insight */}
      {isOverBaseline && (
        <View style={styles.insightBox}>
          <Text style={styles.insightIcon}>📊</Text>
          <Text style={styles.insightText}>
            You were +22 calm on days with {'<'}45 min social
          </Text>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#FFF',
    borderRadius: 20,
    padding: 20,
    marginHorizontal: 16,
    marginVertical: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  title: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1A1A1A',
  },
  detailsLink: {
    fontSize: 14,
    fontWeight: '600',
    color: '#007AFF',
  },
  metricsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
    gap: 16,
  },
  metric: {
    alignItems: 'center',
  },
  metricValue: {
    fontSize: 32,
    fontWeight: '800',
    color: '#333',
  },
  metricLabel: {
    fontSize: 12,
    color: '#999',
    marginTop: 4,
  },
  vs: {
    fontSize: 14,
    fontWeight: '600',
    color: '#CCC',
  },
  deltaBadge: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 12,
  },
  deltaText: {
    fontSize: 16,
    fontWeight: '700',
  },
  sparkleSection: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 16,
    paddingBottom: 8,
  },
  sparklePrompt: {
    fontSize: 15,
    color: '#666',
  },
  sparkleButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F5F5F7',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    gap: 6,
  },
  sparkleIcon: {
    fontSize: 16,
  },
  sparkleButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  sparkleCount: {
    alignItems: 'center',
    paddingVertical: 8,
  },
  sparkleCountText: {
    fontSize: 13,
    color: '#999',
    fontStyle: 'italic',
  },
  insightBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#E5F1FF',
    padding: 12,
    borderRadius: 12,
    marginTop: 12,
    gap: 10,
  },
  insightIcon: {
    fontSize: 20,
  },
  insightText: {
    flex: 1,
    fontSize: 13,
    color: '#005BBB',
    lineHeight: 18,
  },
});

