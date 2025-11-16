import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Dimensions,
} from 'react-native';
import { DayPart, Mood, ContextTag, MicroAct, PurposeProgress } from '../types/fulfillment';

const { width } = Dimensions.get('window');

interface QuickCheckInProps {
  dayPart: DayPart;
  onComplete: (data: CheckInData) => void;
  onCancel: () => void;
  onAddDetails?: () => void;
  isNightCheckIn?: boolean;
}

export interface CheckInData {
  mood: Mood;
  contexts: ContextTag[];
  microAct?: MicroAct;
  purposeProgress?: PurposeProgress;
}

const MOODS: Array<{ value: Mood; emoji: string; label: string }> = [
  { value: 'very-low', emoji: '😢', label: 'Rough' },
  { value: 'low', emoji: '😕', label: 'Low' },
  { value: 'neutral', emoji: '😐', label: 'Okay' },
  { value: 'good', emoji: '🙂', label: 'Good' },
  { value: 'great', emoji: '😊', label: 'Great' },
];

const CONTEXTS: Array<{ value: ContextTag; emoji: string; label: string }> = [
  { value: 'work', emoji: '💼', label: 'Work' },
  { value: 'sleep', emoji: '😴', label: 'Sleep' },
  { value: 'social', emoji: '👥', label: 'Social' },
];

const MICRO_ACTS: Array<{ value: MicroAct; emoji: string; label: string }> = [
  { value: 'gratitude', emoji: '🙏', label: 'Gratitude' },
  { value: 'meditation', emoji: '🧘', label: 'Meditate' },
  { value: 'walk', emoji: '🚶', label: 'Walk' },
  { value: 'nature', emoji: '🌳', label: 'Nature' },
  { value: 'kindness', emoji: '💝', label: 'Kindness' },
  { value: 'learning', emoji: '📚', label: 'Learning' },
  { value: 'breathwork', emoji: '🌬️', label: 'Breathwork' },
  { value: 'journal', emoji: '✍️', label: 'Journal' },
];

const PURPOSE_OPTIONS: Array<{ value: PurposeProgress; emoji: string; label: string }> = [
  { value: 'yes', emoji: '✅', label: 'Yes' },
  { value: 'partly', emoji: '◐', label: 'Partly' },
  { value: 'no', emoji: '⭕', label: 'Not yet' },
];

export const QuickCheckIn: React.FC<QuickCheckInProps> = ({
  dayPart,
  onComplete,
  onCancel,
  onAddDetails,
  isNightCheckIn = false,
}) => {
  const [step, setStep] = useState<'mood' | 'context' | 'microact' | 'purpose' | 'complete'>('mood');
  const [selectedMood, setSelectedMood] = useState<Mood | null>(null);
  const [selectedContexts, setSelectedContexts] = useState<ContextTag[]>([]);
  const [selectedMicroAct, setSelectedMicroAct] = useState<MicroAct | null>(null);
  const [selectedPurpose, setSelectedPurpose] = useState<PurposeProgress | null>(null);
  const [fadeAnim] = useState(new Animated.Value(1));
  const [startTime] = useState(Date.now());
  const [checkInData, setCheckInData] = useState<CheckInData | null>(null);

  const getDayPartEmoji = () => {
    const emojiMap = {
      morning: '🌅',
      day: '☀️',
      evening: '🌆',
      night: '🌙',
    };
    return emojiMap[dayPart];
  };

  const getDayPartLabel = () => {
    return dayPart.charAt(0).toUpperCase() + dayPart.slice(1);
  };

  const handleMoodSelect = (mood: Mood) => {
    setSelectedMood(mood);
    // Auto-advance after selection
    setTimeout(() => {
      transitionToNextStep('context');
    }, 300);
  };

  const toggleContext = (context: ContextTag) => {
    setSelectedContexts((prev) => {
      if (prev.includes(context)) {
        return prev.filter((c) => c !== context);
      } else if (prev.length < 2) {
        return [...prev, context];
      }
      return prev;
    });
  };

  const handleContextNext = () => {
    transitionToNextStep('microact');
  };

  const handleMicroActSelect = (act: MicroAct) => {
    setSelectedMicroAct(act);
    if (isNightCheckIn) {
      setTimeout(() => {
        transitionToNextStep('purpose');
      }, 300);
    } else {
      setTimeout(() => {
        completeCheckIn(act);
      }, 300);
    }
  };

  const handleSkipMicroAct = () => {
    if (isNightCheckIn) {
      transitionToNextStep('purpose');
    } else {
      completeCheckIn();
    }
  };

  const handlePurposeSelect = (progress: PurposeProgress) => {
    setSelectedPurpose(progress);
    setTimeout(() => {
      completeCheckIn(selectedMicroAct || undefined, progress);
    }, 300);
  };

  const completeCheckIn = (microAct?: MicroAct, purposeProgress?: PurposeProgress) => {
    if (!selectedMood) return;

    const duration = Date.now() - startTime;
    console.log(`Check-in completed in ${(duration / 1000).toFixed(1)}s`);

    const data: CheckInData = {
      mood: selectedMood,
      contexts: selectedContexts,
      microAct: microAct || selectedMicroAct || undefined,
      purposeProgress: purposeProgress || selectedPurpose || undefined,
    };

    // Save check-in data and show completion screen
    setCheckInData(data);
    setStep('complete');
  };

  const handleFinishCheckIn = () => {
    if (checkInData) {
      onComplete(checkInData);
    }
  };

  const handleAddDetailsAndFinish = () => {
    if (checkInData) {
      onComplete(checkInData);
      // Parent will handle navigation to Add Details
      if (onAddDetails) {
        setTimeout(() => onAddDetails(), 100);
      }
    }
  };

  const transitionToNextStep = (nextStep: typeof step) => {
    Animated.sequence([
      Animated.timing(fadeAnim, {
        toValue: 0,
        duration: 150,
        useNativeDriver: true,
      }),
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 150,
        useNativeDriver: true,
      }),
    ]).start();
    setTimeout(() => setStep(nextStep), 150);
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={onCancel} style={styles.cancelButton}>
          <Text style={styles.cancelText}>✕</Text>
        </TouchableOpacity>
        <View style={styles.headerTitle}>
          <Text style={styles.dayPartEmoji}>{getDayPartEmoji()}</Text>
          <Text style={styles.dayPartText}>{getDayPartLabel()} Check-in</Text>
        </View>
        <View style={styles.spacer} />
      </View>

      {/* Progress dots */}
      <View style={styles.progressDots}>
        <View style={[styles.dot, step !== 'mood' && styles.dotCompleted]} />
        <View style={[styles.dot, step === 'microact' || step === 'purpose' ? styles.dotCompleted : styles.dotPending]} />
        {isNightCheckIn && (
          <View style={[styles.dot, step === 'purpose' ? styles.dotActive : styles.dotPending]} />
        )}
      </View>

      {/* Content */}
      <Animated.View style={[styles.content, { opacity: fadeAnim }]}>
        {step === 'mood' && (
          <View style={styles.stepContainer}>
            <Text style={styles.question}>How are you feeling?</Text>
            <View style={styles.moodGrid}>
              {MOODS.map((mood) => (
                <TouchableOpacity
                  key={mood.value}
                  style={[
                    styles.moodButton,
                    selectedMood === mood.value && styles.moodButtonSelected,
                  ]}
                  onPress={() => handleMoodSelect(mood.value)}
                  activeOpacity={0.7}
                >
                  <Text style={styles.moodEmoji}>{mood.emoji}</Text>
                  <Text style={styles.moodLabel}>{mood.label}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}

        {step === 'context' && (
          <View style={styles.stepContainer}>
            <Text style={styles.question}>What's the context?</Text>
            <Text style={styles.hint}>Pick 0-2 tags</Text>
            <View style={styles.contextGrid}>
              {CONTEXTS.map((context) => (
                <TouchableOpacity
                  key={context.value}
                  style={[
                    styles.contextChip,
                    selectedContexts.includes(context.value) && styles.contextChipSelected,
                  ]}
                  onPress={() => toggleContext(context.value)}
                  activeOpacity={0.7}
                >
                  <Text style={styles.contextEmoji}>{context.emoji}</Text>
                  <Text style={[
                    styles.contextLabel,
                    selectedContexts.includes(context.value) && styles.contextLabelSelected,
                  ]}>
                    {context.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
            <TouchableOpacity style={styles.nextButton} onPress={handleContextNext}>
              <Text style={styles.nextButtonText}>Next →</Text>
            </TouchableOpacity>
          </View>
        )}

        {step === 'microact' && (
          <View style={styles.stepContainer}>
            <Text style={styles.question}>Any micro-act today?</Text>
            <Text style={styles.hint}>Optional</Text>
            <View style={styles.microActGrid}>
              {MICRO_ACTS.map((act) => (
                <TouchableOpacity
                  key={act.value}
                  style={[
                    styles.microActButton,
                    selectedMicroAct === act.value && styles.microActButtonSelected,
                  ]}
                  onPress={() => handleMicroActSelect(act.value)}
                  activeOpacity={0.7}
                >
                  <Text style={styles.microActEmoji}>{act.emoji}</Text>
                  <Text style={styles.microActLabel}>{act.label}</Text>
                </TouchableOpacity>
              ))}
            </View>
            <TouchableOpacity style={styles.skipButton} onPress={handleSkipMicroAct}>
              <Text style={styles.skipButtonText}>Skip</Text>
            </TouchableOpacity>
          </View>
        )}

        {step === 'purpose' && (
          <View style={styles.stepContainer}>
            <Text style={styles.question}>Did you move the ball today?</Text>
            <Text style={styles.hint}>On your weekly purpose</Text>
            <View style={styles.purposeGrid}>
              {PURPOSE_OPTIONS.map((option) => (
                <TouchableOpacity
                  key={option.value}
                  style={[
                    styles.purposeButton,
                    selectedPurpose === option.value && styles.purposeButtonSelected,
                  ]}
                  onPress={() => handlePurposeSelect(option.value)}
                  activeOpacity={0.7}
                >
                  <Text style={styles.purposeEmoji}>{option.emoji}</Text>
                  <Text style={styles.purposeLabel}>{option.label}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}

        {step === 'complete' && checkInData && (
          <View style={styles.stepContainer}>
            <Text style={styles.completeEmoji}>✅</Text>
            <Text style={styles.completeTitle}>Check-in Complete!</Text>
            <Text style={styles.completeSubtitle}>
              {checkInData.microAct ? `You did: ${checkInData.microAct}` : 'Nice work staying aware'}
            </Text>
            
            {/* Buttons */}
            <View style={styles.completeButtons}>
              {onAddDetails && checkInData.microAct && (
                <TouchableOpacity 
                  style={styles.addDetailsOptionButton}
                  onPress={handleAddDetailsAndFinish}
                  activeOpacity={0.8}
                >
                  <Text style={styles.addDetailsOptionIcon}>📊</Text>
                  <View style={styles.addDetailsOptionText}>
                    <Text style={styles.addDetailsOptionTitle}>Add Details (Optional)</Text>
                    <Text style={styles.addDetailsOptionSubtitle}>
                      Enrich your {checkInData.microAct} data
                    </Text>
                  </View>
                  <Text style={styles.addDetailsOptionArrow}>→</Text>
                </TouchableOpacity>
              )}
              
              <TouchableOpacity 
                style={styles.doneButton}
                onPress={handleFinishCheckIn}
                activeOpacity={0.8}
              >
                <Text style={styles.doneButtonText}>Done</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
      </Animated.View>

      {/* Timer info */}
      {step !== 'complete' && (
        <View style={styles.footer}>
          <Text style={styles.timerText}>⚡ Takes ~15 seconds</Text>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F3FF', // V2: Light purple background
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
  cancelButton: {
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 20,
    backgroundColor: '#F3F4F6',
  },
  cancelText: {
    fontSize: 24,
    color: '#6B7280',
  },
  headerTitle: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  dayPartEmoji: {
    fontSize: 28,
    marginRight: 10,
  },
  dayPartText: {
    fontSize: 20,
    fontWeight: '800',
    color: '#1F2937',
  },
  spacer: {
    width: 36,
  },
  progressDots: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 20,
    gap: 10,
    backgroundColor: '#FFFFFF',
    marginBottom: 4,
  },
  dot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#8B5CF6',
  },
  dotCompleted: {
    backgroundColor: '#10B981',
  },
  dotActive: {
    backgroundColor: '#8B5CF6',
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  dotPending: {
    backgroundColor: '#D1D5DB',
  },
  content: {
    flex: 1,
    paddingHorizontal: 20,
  },
  stepContainer: {
    flex: 1,
  },
  question: {
    fontSize: 28,
    fontWeight: '800',
    color: '#1F2937',
    textAlign: 'center',
    marginBottom: 10,
    marginTop: 20,
  },
  hint: {
    fontSize: 15,
    color: '#6B7280',
    textAlign: 'center',
    marginBottom: 36,
    fontWeight: '500',
  },
  moodGrid: {
    flexDirection: 'row',
    justifyContent: 'center',
    flexWrap: 'wrap',
    gap: 12,
    maxWidth: 400,
    alignSelf: 'center',
  },
  moodButton: {
    width: 70,
    height: 70,
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#E5E7EB',
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.08,
    shadowRadius: 6,
    elevation: 3,
  },
  moodButtonSelected: {
    borderColor: '#A78BFA',
    backgroundColor: '#F5F3FF',
    borderWidth: 3,
    shadowColor: '#8B5CF6',
    shadowOpacity: 0.25,
  },
  moodEmoji: {
    fontSize: 36,
    marginBottom: 4,
  },
  moodLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: '#374151',
  },
  contextGrid: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 12,
  },
  contextChip: {
    paddingHorizontal: 20,
    paddingVertical: 16,
    backgroundColor: '#FFF',
    borderRadius: 20,
    borderWidth: 2,
    borderColor: '#E8E8E8',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  contextChipSelected: {
    borderColor: '#007AFF',
    backgroundColor: '#E5F1FF',
  },
  contextEmoji: {
    fontSize: 20,
  },
  contextLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  contextLabelSelected: {
    color: '#007AFF',
  },
  nextButton: {
    marginTop: 40,
    backgroundColor: '#007AFF',
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  nextButtonText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFF',
  },
  microActGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 10,
    maxWidth: 400,
    alignSelf: 'center',
  },
  microActButton: {
    width: 85,
    height: 85,
    backgroundColor: '#FFF',
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#E8E8E8',
    padding: 8,
  },
  microActButtonSelected: {
    borderColor: '#34C759',
    backgroundColor: '#F0F9F6',
  },
  microActEmoji: {
    fontSize: 28,
    marginBottom: 4,
  },
  microActLabel: {
    fontSize: 10,
    fontWeight: '600',
    color: '#333',
    textAlign: 'center',
  },
  skipButton: {
    marginTop: 24,
    paddingVertical: 12,
    alignItems: 'center',
  },
  skipButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#999',
  },
  purposeGrid: {
    gap: 16,
  },
  purposeButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF',
    padding: 20,
    borderRadius: 16,
    borderWidth: 2,
    borderColor: '#E8E8E8',
    gap: 16,
  },
  purposeButtonSelected: {
    borderColor: '#FFD93D',
    backgroundColor: '#FFFBF0',
  },
  purposeEmoji: {
    fontSize: 32,
  },
  purposeLabel: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  footer: {
    padding: 20,
    alignItems: 'center',
  },
  timerText: {
    fontSize: 13,
    color: '#999',
  },
  // Completion Screen Styles
  completeEmoji: {
    fontSize: 72,
    textAlign: 'center',
    marginBottom: 20,
  },
  completeTitle: {
    fontSize: 28,
    fontWeight: '800',
    color: '#1F2937',
    textAlign: 'center',
    marginBottom: 8,
  },
  completeSubtitle: {
    fontSize: 16,
    color: '#6B7280',
    textAlign: 'center',
    marginBottom: 32,
    fontWeight: '500',
  },
  completeButtons: {
    gap: 12,
    paddingHorizontal: 20,
  },
  addDetailsOptionButton: {
    backgroundColor: '#EDE9FE',
    borderRadius: 20,
    padding: 18,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#C4B5FD',
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
    elevation: 3,
  },
  addDetailsOptionIcon: {
    fontSize: 32,
    marginRight: 14,
  },
  addDetailsOptionText: {
    flex: 1,
  },
  addDetailsOptionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1F2937',
    marginBottom: 3,
  },
  addDetailsOptionSubtitle: {
    fontSize: 13,
    color: '#6B7280',
  },
  addDetailsOptionArrow: {
    fontSize: 20,
    color: '#8B5CF6',
    fontWeight: '700',
  },
  doneButton: {
    backgroundColor: '#8B5CF6',
    borderRadius: 20,
    paddingVertical: 18,
    alignItems: 'center',
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  doneButtonText: {
    fontSize: 18,
    fontWeight: '800',
    color: '#FFFFFF',
  },
});

