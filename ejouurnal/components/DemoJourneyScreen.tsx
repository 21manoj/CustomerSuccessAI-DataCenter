import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Dimensions,
} from 'react-native';

const { width } = Dimensions.get('window');

interface DemoJourneyProps {
  onBack: () => void;
  onExitDemo: () => void;
}

export const DemoJourneyScreen: React.FC<DemoJourneyProps> = ({
  onBack,
  onExitDemo,
}) => {
  const [currentWeek, setCurrentWeek] = useState(1);
  const [currentDay, setCurrentDay] = useState(1);

  // Sample user: Sarah's 4-week journey
  const journey = {
    intention: "Show up with more presence for my family",
    microMoves: [
      "10-min morning walk 3x",
      "Read 2 chapters of that book",
      "Call a friend I've been missing"
    ],
    antiGlitter: "No phone first hour after waking",
    
    weeks: [
      {
        week: 1,
        theme: "Discovery - Finding What Works",
        meaningfulDays: 3,
        avgFulfillment: 58,
        microMoveCompletion: { walk: 2, read: 1, call: 0 },
        keyInsight: "Morning walks boost mental clarity (+12 Mind)",
        journalSnippet: "You did your walk this morning and scored 68 vs 52 yesterday without it. I'm starting to see a pattern...",
        learnings: [
          "Walks boost mind score significantly",
          "No-phone mornings feel better",
          "Still figuring out the routine"
        ]
      },
      {
        week: 2,
        theme: "Optimization - Refining Your Formula",
        meaningfulDays: 5,
        avgFulfillment: 71,
        microMoveCompletion: { walk: 5, read: 3, call: 1 },
        keyInsight: "Walk + No-phone morning = +18 Mind (not just +12!)",
        journalSnippet: "You combined your walk with no-phone morning - that's your sweet spot! 78 fulfillment vs 65 with walk alone.",
        learnings: [
          "Combining walk + no-phone amplifies effect",
          "Reading at night → better sleep",
          "Social calls energize you"
        ]
      },
      {
        week: 3,
        theme: "Habit Formation - Building Consistency",
        meaningfulDays: 6,
        avgFulfillment: 78,
        microMoveCompletion: { walk: 6, read: 5, call: 2 },
        keyInsight: "2+ micro-moves per day → +15 Purpose boost",
        journalSnippet: "6 walks in a row! You're building a streak. When you hit 2+ micro-moves, you average 82 fulfillment. That's your presence formula.",
        learnings: [
          "Consistency matters more than perfection",
          "Streaks create momentum",
          "Your formula is emerging"
        ]
      },
      {
        week: 4,
        theme: "Mastery - Living Your Intention",
        meaningfulDays: 6,
        avgFulfillment: 82,
        microMoveCompletion: { walk: 6, read: 6, call: 4 },
        keyInsight: "You've found YOUR presence formula",
        journalSnippet: "Not trying to be present anymore - you ARE present. Walk + no-phone + connect = 82 avg. You've proven it for 4 weeks. This is your identity now.",
        learnings: [
          "Your formula: Walk + No-phone + Connect",
          "82 avg fulfillment when you follow it",
          "Intention → Identity transformation"
        ]
      }
    ]
  };

  const currentWeekData = journey.weeks[currentWeek - 1];

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack}>
          <Text style={styles.backButton}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>🎬 AI Guidance Demo</Text>
        <TouchableOpacity onPress={onExitDemo}>
          <Text style={styles.exitButton}>Exit</Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Progress Indicator */}
        <View style={styles.progressBar}>
          {[1, 2, 3, 4].map(week => (
            <TouchableOpacity
              key={week}
              style={[
                styles.progressDot,
                currentWeek === week && styles.progressDotActive,
                currentWeek > week && styles.progressDotComplete
              ]}
              onPress={() => setCurrentWeek(week)}
            >
              <Text style={[
                styles.progressDotText,
                (currentWeek === week || currentWeek > week) && styles.progressDotTextActive
              ]}>
                {week}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Week Theme */}
        <View style={styles.themeCard}>
          <Text style={styles.weekLabel}>Week {currentWeek} of 4</Text>
          <Text style={styles.themeTitle}>{currentWeekData.theme}</Text>
        </View>

        {/* Sarah's Intention */}
        <View style={styles.intentionCard}>
          <Text style={styles.cardTitle}>🎯 Sarah's Intention</Text>
          <Text style={styles.intentionText}>"{journey.intention}"</Text>
          
          <View style={styles.microMovesBox}>
            <Text style={styles.microMovesTitle}>Micro-Moves:</Text>
            {journey.microMoves.map((move, index) => (
              <View key={index} style={styles.microMoveRow}>
                <Text style={styles.microMoveCheck}>
                  {currentWeek === 1 && index === 0 && currentWeekData.microMoveCompletion.walk >= 2 ? '✅' :
                   currentWeek === 1 && index === 0 ? '⏳' :
                   currentWeek >= 2 && index === 0 ? '✅' :
                   currentWeek >= 2 && index === 1 && currentWeekData.microMoveCompletion.read >= 3 ? '✅' :
                   currentWeek >= 3 && index === 2 && currentWeekData.microMoveCompletion.call >= 2 ? '✅' :
                   currentWeek >= 4 ? '✅' : '⏳'}
                </Text>
                <Text style={styles.microMoveText}>{move}</Text>
                <Text style={styles.microMoveCount}>
                  {index === 0 ? `${currentWeekData.microMoveCompletion.walk}/7` :
                   index === 1 ? `${currentWeekData.microMoveCompletion.read}/7` :
                   `${currentWeekData.microMoveCompletion.call}/7`}
                </Text>
              </View>
            ))}
          </View>
          
          <View style={styles.antiGlitterBox}>
            <Text style={styles.antiGlitterLabel}>Anti-Glitter Experiment:</Text>
            <Text style={styles.antiGlitterText}>{journey.antiGlitter}</Text>
          </View>
        </View>

        {/* Week Results */}
        <View style={styles.resultsCard}>
          <Text style={styles.cardTitle}>📊 Week {currentWeek} Results</Text>
          
          <View style={styles.statRow}>
            <StatBox label="Meaningful Days" value={`${currentWeekData.meaningfulDays}/7`} />
            <StatBox label="Avg Fulfillment" value={currentWeekData.avgFulfillment.toString()} />
          </View>
          
          <View style={styles.gradeBox}>
            <Text style={styles.gradeLabel}>Intention Progress:</Text>
            <Text style={styles.gradeValue}>
              {currentWeek === 1 ? 'C+ (58%)' :
               currentWeek === 2 ? 'B (71%)' :
               currentWeek === 3 ? 'B+ (78%)' :
               'A- (82%)'}
            </Text>
          </View>
        </View>

        {/* Key Insight */}
        <View style={styles.insightCard}>
          <Text style={styles.cardTitle}>💡 AI Discovered This Week</Text>
          <View style={styles.insightBox}>
            <Text style={styles.insightType}>
              {currentWeek === 1 ? '⚡ SAME-DAY' :
               currentWeek === 2 ? '🎯 BREAKPOINT' :
               currentWeek === 3 ? '🔮 PURPOSE-PATH' :
               '🌟 MASTERY'}
            </Text>
            <Text style={styles.insightTitle}>{currentWeekData.keyInsight}</Text>
          </View>
        </View>

        {/* AI Journal Excerpt */}
        <View style={styles.journalCard}>
          <Text style={styles.cardTitle}>📔 AI Journal Excerpt</Text>
          <View style={styles.journalBox}>
            <Text style={styles.journalText}>"{currentWeekData.journalSnippet}"</Text>
          </View>
          <View style={styles.journalMeta}>
            <Text style={styles.journalMetaText}>
              Day {currentWeek === 1 ? 3 : currentWeek === 2 ? 10 : currentWeek === 3 ? 17 : 28} • 
              {currentWeek === 1 ? ' Discovery phase' :
               currentWeek === 2 ? ' Optimization phase' :
               currentWeek === 3 ? ' Habit formation' :
               ' Mastery achieved'}
            </Text>
          </View>
        </View>

        {/* What Sarah Learned */}
        <View style={styles.learningsCard}>
          <Text style={styles.cardTitle}>✨ What Sarah Learned</Text>
          {currentWeekData.learnings.map((learning, index) => (
            <View key={index} style={styles.learningRow}>
              <Text style={styles.learningBullet}>•</Text>
              <Text style={styles.learningText}>{learning}</Text>
            </View>
          ))}
        </View>

        {/* The Transformation */}
        {currentWeek === 4 && (
          <View style={styles.transformationCard}>
            <Text style={styles.transformationTitle}>🌟 THE TRANSFORMATION</Text>
            
            <View style={styles.beforeAfter}>
              <View style={styles.beforeBox}>
                <Text style={styles.beforeLabel}>Week 1</Text>
                <Text style={styles.beforeText}>
                  "I want to be more present"
                </Text>
                <Text style={styles.beforeSubtext}>Vague, unmeasured, hoping</Text>
              </View>
              
              <Text style={styles.arrow}>↓</Text>
              
              <View style={styles.afterBox}>
                <Text style={styles.afterLabel}>Week 4</Text>
                <Text style={styles.afterText}>
                  "I AM present when I: Walk + No-phone + Connect"
                </Text>
                <Text style={styles.afterSubtext}>Proven formula, measurable, doing it</Text>
              </View>
            </View>
            
            <View style={styles.formulaBox}>
              <Text style={styles.formulaTitle}>Sarah's Presence Formula:</Text>
              <Text style={styles.formulaText}>
                Morning: Walk (10 min) + No phone (1 hour){'\n'}
                Evening: Reading OR Social call{'\n'}
                = 82 avg fulfillment = Presence achieved
              </Text>
            </View>
          </View>
        )}

        {/* Navigation */}
        <View style={styles.navigation}>
          {currentWeek > 1 && (
            <TouchableOpacity 
              style={styles.navButton}
              onPress={() => setCurrentWeek(currentWeek - 1)}
            >
              <Text style={styles.navButtonText}>← Previous Week</Text>
            </TouchableOpacity>
          )}
          
          {currentWeek < 4 ? (
            <TouchableOpacity 
              style={[styles.navButton, styles.navButtonPrimary]}
              onPress={() => setCurrentWeek(currentWeek + 1)}
            >
              <Text style={styles.navButtonTextPrimary}>Next Week →</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity 
              style={[styles.navButton, styles.navButtonSuccess]}
              onPress={onExitDemo}
            >
              <Text style={styles.navButtonTextPrimary}>Start Your Journey! ✨</Text>
            </TouchableOpacity>
          )}
        </View>

        <View style={styles.bottomPadding} />
      </ScrollView>
    </View>
  );
};

const StatBox: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <View style={styles.statBox}>
    <Text style={styles.statValue}>{value}</Text>
    <Text style={styles.statLabel}>{label}</Text>
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
  exitButton: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
  },
  content: {
    flex: 1,
  },
  progressBar: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 24,
    gap: 20,
  },
  progressDot: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: '#E0E0E0',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    borderColor: '#E0E0E0',
  },
  progressDotActive: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  progressDotComplete: {
    backgroundColor: '#34C759',
    borderColor: '#34C759',
  },
  progressDotText: {
    fontSize: 18,
    fontWeight: '700',
    color: '#999',
  },
  progressDotTextActive: {
    color: '#FFF',
  },
  themeCard: {
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginBottom: 16,
    borderRadius: 20,
    padding: 24,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 3,
  },
  weekLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#666',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 8,
  },
  themeTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#007AFF',
    textAlign: 'center',
  },
  intentionCard: {
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginBottom: 16,
    borderRadius: 20,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1A1A1A',
    marginBottom: 12,
  },
  intentionText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    fontStyle: 'italic',
    marginBottom: 16,
  },
  microMovesBox: {
    backgroundColor: '#F9F9FB',
    borderRadius: 12,
    padding: 14,
    marginBottom: 12,
  },
  microMovesTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: '#666',
    marginBottom: 8,
  },
  microMoveRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 6,
  },
  microMoveCheck: {
    fontSize: 16,
    marginRight: 10,
    width: 24,
  },
  microMoveText: {
    flex: 1,
    fontSize: 14,
    color: '#333',
  },
  microMoveCount: {
    fontSize: 13,
    fontWeight: '600',
    color: '#007AFF',
  },
  antiGlitterBox: {
    backgroundColor: '#FFF9E6',
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: '#FFD93D',
  },
  antiGlitterLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#997700',
    marginBottom: 4,
  },
  antiGlitterText: {
    fontSize: 13,
    color: '#664400',
  },
  resultsCard: {
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginBottom: 16,
    borderRadius: 20,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  statRow: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 16,
  },
  statBox: {
    flex: 1,
    backgroundColor: '#F5F8FF',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  statValue: {
    fontSize: 28,
    fontWeight: '800',
    color: '#007AFF',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 11,
    color: '#666',
    textAlign: 'center',
  },
  gradeBox: {
    backgroundColor: '#F0F9FF',
    borderRadius: 12,
    padding: 14,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  gradeLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0066CC',
  },
  gradeValue: {
    fontSize: 18,
    fontWeight: '800',
    color: '#007AFF',
  },
  insightCard: {
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginBottom: 16,
    borderRadius: 20,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  insightBox: {
    backgroundColor: '#FFF9E6',
    borderRadius: 12,
    padding: 16,
    borderLeftWidth: 4,
    borderLeftColor: '#FFD93D',
  },
  insightType: {
    fontSize: 11,
    fontWeight: '700',
    color: '#997700',
    marginBottom: 8,
    letterSpacing: 1,
  },
  insightTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#1A1A1A',
  },
  journalCard: {
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginBottom: 16,
    borderRadius: 20,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  journalBox: {
    backgroundColor: '#F5F5F7',
    borderRadius: 12,
    padding: 16,
  },
  journalText: {
    fontSize: 14,
    color: '#333',
    lineHeight: 22,
    fontStyle: 'italic',
  },
  journalMeta: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#E8E8E8',
  },
  journalMetaText: {
    fontSize: 12,
    color: '#999',
  },
  learningsCard: {
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginBottom: 16,
    borderRadius: 20,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  learningRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 10,
  },
  learningBullet: {
    fontSize: 16,
    color: '#34C759',
    marginRight: 10,
    fontWeight: '700',
  },
  learningText: {
    flex: 1,
    fontSize: 14,
    color: '#333',
    lineHeight: 20,
  },
  transformationCard: {
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginBottom: 16,
    borderRadius: 20,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 16,
    elevation: 4,
  },
  transformationTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: '#34C759',
    textAlign: 'center',
    marginBottom: 24,
  },
  beforeAfter: {
    marginBottom: 20,
  },
  beforeBox: {
    backgroundColor: '#FFEBEE',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  beforeLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: '#C62828',
    marginBottom: 8,
    textTransform: 'uppercase',
  },
  beforeText: {
    fontSize: 15,
    color: '#D32F2F',
    fontWeight: '600',
    marginBottom: 6,
  },
  beforeSubtext: {
    fontSize: 12,
    color: '#E57373',
  },
  arrow: {
    fontSize: 32,
    color: '#34C759',
    textAlign: 'center',
    marginVertical: 8,
  },
  afterBox: {
    backgroundColor: '#E8F5E9',
    borderRadius: 12,
    padding: 16,
  },
  afterLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: '#2E7D32',
    marginBottom: 8,
    textTransform: 'uppercase',
  },
  afterText: {
    fontSize: 15,
    color: '#388E3C',
    fontWeight: '600',
    marginBottom: 6,
  },
  afterSubtext: {
    fontSize: 12,
    color: '#66BB6A',
  },
  formulaBox: {
    backgroundColor: '#E3F2FD',
    borderRadius: 12,
    padding: 16,
    borderWidth: 2,
    borderColor: '#007AFF',
  },
  formulaTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#0066CC',
    marginBottom: 8,
  },
  formulaText: {
    fontSize: 13,
    color: '#1976D2',
    lineHeight: 20,
    fontWeight: '500',
  },
  navigation: {
    flexDirection: 'row',
    marginHorizontal: 16,
    gap: 12,
    marginTop: 8,
  },
  navButton: {
    flex: 1,
    backgroundColor: '#F5F5F7',
    borderRadius: 16,
    paddingVertical: 16,
    alignItems: 'center',
  },
  navButtonPrimary: {
    backgroundColor: '#007AFF',
  },
  navButtonSuccess: {
    backgroundColor: '#34C759',
  },
  navButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  navButtonTextPrimary: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFF',
  },
  bottomPadding: {
    height: 40,
  },
});

export default DemoJourneyScreen;

