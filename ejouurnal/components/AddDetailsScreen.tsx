import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
} from 'react-native';
import Slider from '@react-native-community/slider';

interface AddDetailsScreenProps {
  onSave: (details: DetailData) => void;
  onBack: () => void;
  initialData?: DetailData;
}

export interface DetailData {
  sleepHours?: number;
  sleepQuality?: number;
  breakfast?: 'good' | 'ok' | 'poor';
  breakfastNotes?: string;
  lunch?: 'good' | 'ok' | 'poor';
  lunchNotes?: string;
  dinner?: 'good' | 'ok' | 'poor';
  dinnerNotes?: string;
  snacks?: 'good' | 'ok' | 'poor';
  foodQuality?: number; // Overall food quality 1-5
  hydration?: number; // Glasses of water
  exerciseType?: string;
  exerciseDuration?: number;
  exerciseIntensity?: 'light' | 'moderate' | 'vigorous';
  exerciseFeeling?: string;
  socialQuality?: 'energized' | 'neutral' | 'drained';
  socialWho?: string;
  socialDuration?: number;
  socialType?: string;
  socialMinutes?: number; // Total quality social minutes
  screenMinutes?: number; // Total screen time in minutes
}

export const AddDetailsScreen: React.FC<AddDetailsScreenProps> = ({
  onSave,
  onBack,
  initialData
}) => {
  const [sleepHours, setSleepHours] = useState(initialData?.sleepHours || 7.5);
  const [sleepQuality, setSleepQuality] = useState(initialData?.sleepQuality || 4);
  const [breakfast, setBreakfast] = useState(initialData?.breakfast || 'good');
  const [breakfastNotes, setBreakfastNotes] = useState(initialData?.breakfastNotes || '');
  const [lunch, setLunch] = useState(initialData?.lunch || 'ok');
  const [lunchNotes, setLunchNotes] = useState(initialData?.lunchNotes || '');
  const [dinner, setDinner] = useState(initialData?.dinner || 'good');
  const [dinnerNotes, setDinnerNotes] = useState(initialData?.dinnerNotes || '');
  const [snacks, setSnacks] = useState(initialData?.snacks || 'ok');

  const [showExercise, setShowExercise] = useState(false);
  const [exerciseType, setExerciseType] = useState(initialData?.exerciseType || 'Walk');
  const [exerciseDuration, setExerciseDuration] = useState(initialData?.exerciseDuration || 30);
  const [exerciseIntensity, setExerciseIntensity] = useState(initialData?.exerciseIntensity || 'moderate');
  const [exerciseFeeling, setExerciseFeeling] = useState(initialData?.exerciseFeeling || '');

  const [showSocial, setShowSocial] = useState(false);
  const [socialQuality, setSocialQuality] = useState(initialData?.socialQuality || 'energized');
  const [socialWho, setSocialWho] = useState(initialData?.socialWho || '');
  const [socialDuration, setSocialDuration] = useState(initialData?.socialDuration || 30);

  const handleSave = () => {
    const details: DetailData = {
      sleepHours,
      sleepQuality,
      breakfast,
      breakfastNotes,
      lunch,
      lunchNotes,
      dinner,
      dinnerNotes,
      snacks,
      ...(showExercise && { exerciseType, exerciseDuration, exerciseIntensity, exerciseFeeling }),
      ...(showSocial && { socialQuality, socialWho, socialDuration })
    };

    onSave(details);
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack}>
          <Text style={styles.backButton}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Add Details</Text>
        <TouchableOpacity onPress={handleSave}>
          <Text style={styles.saveButton}>Save</Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={styles.subtitle}>
          Optional deep dive for richer insights
        </Text>

        {/* Sleep Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionIcon}>💤</Text>
            <Text style={styles.sectionTitle}>Sleep</Text>
          </View>

          <Text style={styles.label}>Hours Slept</Text>
          <Slider
            style={styles.slider}
            minimumValue={0}
            maximumValue={12}
            step={0.5}
            value={sleepHours}
            onValueChange={setSleepHours}
            minimumTrackTintColor="#007AFF"
            maximumTrackTintColor="#E0E0E0"
          />
          <Text style={styles.sliderValue}>{sleepHours.toFixed(1)}h</Text>

          <Text style={styles.label}>Quality</Text>
          <View style={styles.starContainer}>
            {[1, 2, 3, 4, 5].map(star => (
              <TouchableOpacity key={star} onPress={() => setSleepQuality(star)}>
                <Text style={styles.star}>
                  {star <= sleepQuality ? '⭐' : '☆'}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          <View style={styles.infoBox}>
            <Text style={styles.infoText}>
              💡 Tip: Better sleep quality = higher Body & Mind scores
            </Text>
          </View>
        </View>

        {/* Food Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionIcon}>🍽️</Text>
            <Text style={styles.sectionTitle}>Fuel & Nutrition</Text>
          </View>

          <FoodEntry
            meal="Breakfast"
            value={breakfast}
            onChange={setBreakfast}
            notes={breakfastNotes}
            onNotesChange={setBreakfastNotes}
          />
          <FoodEntry
            meal="Lunch"
            value={lunch}
            onChange={setLunch}
            notes={lunchNotes}
            onNotesChange={setLunchNotes}
          />
          <FoodEntry
            meal="Dinner"
            value={dinner}
            onChange={setDinner}
            notes={dinnerNotes}
            onNotesChange={setDinnerNotes}
          />
          <FoodEntry
            meal="Snacks"
            value={snacks}
            onChange={setSnacks}
          />
        </View>

        {/* Exercise Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionIcon}>💪</Text>
            <Text style={styles.sectionTitle}>Activity & Exercise</Text>
          </View>

          <View style={styles.infoBox}>
            <Text style={styles.infoText}>
              💡 Optional: Add manual exercise details for deeper insights
            </Text>
          </View>

          <TouchableOpacity
            style={styles.addButton}
            onPress={() => setShowExercise(!showExercise)}
          >
            <Text style={styles.addButtonText}>
              {showExercise ? '− Remove Manual Exercise' : '+ Add Manual Exercise'}
            </Text>
          </TouchableOpacity>

          {showExercise && (
            <View style={styles.expandedSection}>
              <Text style={styles.label}>Type</Text>
              <View style={styles.chipGrid}>
                {['Walk', 'Run', 'Gym', 'Yoga', 'Cycling', 'Swimming', 'HIIT', 'Pilates', 'Dance', 'Sports', 'Strength', 'Other'].map(type => (
                  <TouchableOpacity
                    key={type}
                    style={[
                      styles.chip,
                      exerciseType === type && styles.chipSelected
                    ]}
                    onPress={() => setExerciseType(type)}
                  >
                    <Text style={[
                      styles.chipText,
                      exerciseType === type && styles.chipTextSelected
                    ]}>
                      {type}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>

              <Text style={styles.label}>Duration</Text>
              <Slider
                style={styles.slider}
                minimumValue={0}
                maximumValue={120}
                step={5}
                value={exerciseDuration}
                onValueChange={setExerciseDuration}
                minimumTrackTintColor="#34C759"
                maximumTrackTintColor="#E0E0E0"
              />
              <Text style={styles.sliderValue}>{exerciseDuration} min</Text>

              <Text style={styles.label}>Intensity</Text>
              <View style={styles.buttonRow}>
                {['light', 'moderate', 'vigorous'].map(intensity => (
                  <TouchableOpacity
                    key={intensity}
                    style={[
                      styles.intensityButton,
                      exerciseIntensity === intensity && styles.intensityButtonSelected
                    ]}
                    onPress={() => setExerciseIntensity(intensity as any)}
                  >
                    <Text style={[
                      styles.intensityButtonText,
                      exerciseIntensity === intensity && styles.intensityButtonTextSelected
                    ]}>
                      {intensity.charAt(0).toUpperCase() + intensity.slice(1)}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>

              <Text style={styles.label}>How did it feel?</Text>
              <View style={styles.buttonRow}>
                {['😊 Energized', '😌 Good', '😐 Okay', '😓 Exhausted'].map(feeling => (
                  <TouchableOpacity
                    key={feeling}
                    style={[
                      styles.feelingButton,
                      exerciseFeeling === feeling && styles.feelingButtonSelected
                    ]}
                    onPress={() => setExerciseFeeling(feeling)}
                  >
                    <Text style={[
                      styles.feelingButtonText,
                      exerciseFeeling === feeling && styles.feelingButtonTextSelected
                    ]}>
                      {feeling}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>

              {exerciseType === 'Yoga' && (
                <>
                  <Text style={styles.label}>Yoga Style</Text>
                  <View style={styles.chipGrid}>
                    {['Vinyasa', 'Hatha', 'Yin', 'Power', 'Restorative', 'Ashtanga'].map(style => (
                      <TouchableOpacity
                        key={style}
                        style={[styles.chip, exerciseFeeling.includes(style) && styles.chipSelected]}
                        onPress={() => setExerciseFeeling(exerciseFeeling.includes(style) ? exerciseFeeling : `${exerciseFeeling} ${style}`.trim())}
                      >
                        <Text style={[styles.chipText, exerciseFeeling.includes(style) && styles.chipTextSelected]}>
                          {style}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </>
              )}
            </View>
          )}
        </View>

        {/* Social Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionIcon}>👥</Text>
            <Text style={styles.sectionTitle}>Social Connections</Text>
          </View>

          <Text style={styles.label}>Quality</Text>
          <View style={styles.buttonRow}>
            {[
              { value: 'energized', emoji: '⚡', label: 'Energized' },
              { value: 'neutral', emoji: '😐', label: 'Neutral' },
              { value: 'drained', emoji: '😔', label: 'Drained' }
            ].map(option => (
              <TouchableOpacity
                key={option.value}
                style={[
                  styles.socialButton,
                  socialQuality === option.value && styles.socialButtonSelected
                ]}
                onPress={() => setSocialQuality(option.value as any)}
              >
                <Text style={styles.socialEmoji}>{option.emoji}</Text>
                <Text style={[
                  styles.socialButtonText,
                  socialQuality === option.value && styles.socialButtonTextSelected
                ]}>
                  {option.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          <TouchableOpacity
            style={styles.addButton}
            onPress={() => setShowSocial(!showSocial)}
          >
            <Text style={styles.addButtonText}>
              {showSocial ? '− Remove Details' : '+ Add Optional Details'}
            </Text>
          </TouchableOpacity>

          {showSocial && (
            <View style={styles.expandedSection}>
              <Text style={styles.label}>Who? (Optional)</Text>
              <TextInput
                style={styles.textInput}
                value={socialWho}
                onChangeText={setSocialWho}
                placeholder='e.g., "Coffee with Sarah" or "Team meeting"'
                placeholderTextColor="#999"
              />

              <Text style={styles.label}>Duration</Text>
              <View style={styles.chipGrid}>
                {[15, 30, 60, 120].map(dur => (
                  <TouchableOpacity
                    key={dur}
                    style={[
                      styles.chip,
                      socialDuration === dur && styles.chipSelected
                    ]}
                    onPress={() => setSocialDuration(dur)}
                  >
                    <Text style={[
                      styles.chipText,
                      socialDuration === dur && styles.chipTextSelected
                    ]}>
                      {dur < 60 ? `${dur}m` : `${dur / 60}h`}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
          )}
        </View>

        {/* Screen Time Section - Coming Soon */}
        {/* 
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionIcon}>📱</Text>
            <Text style={styles.sectionTitle}>Screen Time (Coming Soon)</Text>
          </View>

          <View style={styles.infoBox}>
            <Text style={styles.infoText}>
              🔜 Screen time tracking will be available in a future update
            </Text>
          </View>
        </View>
        */}

        {/* Save Button */}
        <TouchableOpacity style={styles.saveButtonMain} onPress={handleSave}>
          <Text style={styles.saveButtonMainText}>Save All Details</Text>
        </TouchableOpacity>

        <View style={styles.bottomPadding} />
      </ScrollView>
    </View>
  );
};

// Helper Components
const FoodEntry: React.FC<{
  meal: string;
  value: 'good' | 'ok' | 'poor';
  onChange: (value: 'good' | 'ok' | 'poor') => void;
  notes?: string;
  onNotesChange?: (notes: string) => void;
}> = ({ meal, value, onChange, notes, onNotesChange }) => (
  <View style={styles.foodEntry}>
    <Text style={styles.mealLabel}>{meal}</Text>
    <View style={styles.buttonRow}>
      {(['good', 'ok', 'poor'] as const).map(quality => (
        <TouchableOpacity
          key={quality}
          style={[
            styles.qualityButton,
            value === quality && styles.qualityButtonSelected
          ]}
          onPress={() => onChange(quality)}
        >
          <Text style={[
            styles.qualityButtonText,
            value === quality && styles.qualityButtonTextSelected
          ]}>
            {quality.charAt(0).toUpperCase() + quality.slice(1)}
          </Text>
        </TouchableOpacity>
      ))}
    </View>
    {onNotesChange && (
      <TextInput
        style={styles.notesInput}
        value={notes}
        onChangeText={onNotesChange}
        placeholder="Optional: What did you eat?"
        placeholderTextColor="#999"
      />
    )}
  </View>
);

const ScreenTimeRow: React.FC<{
  label: string;
  minutes: number;
  baseline?: number;
}> = ({ label, minutes, baseline }) => {
  const delta = baseline ? minutes - baseline : 0;
  const deltaText = delta > 0 ? `+${delta}m` : delta < 0 ? `${delta}m` : '';
  const deltaColor = delta > 0 ? '#FF9500' : delta < 0 ? '#34C759' : '#666';

  return (
    <View style={styles.screenTimeRow}>
      <Text style={styles.screenTimeLabel}>{label}</Text>
      <View style={styles.screenTimeValue}>
        <Text style={styles.screenTimeMinutes}>{minutes}m</Text>
        {deltaText && (
          <Text style={[styles.screenTimeDelta, { color: deltaColor }]}>
            {deltaText}
          </Text>
        )}
      </View>
    </View>
  );
};

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
    fontSize: 20,
    fontWeight: '800',
    color: '#1F2937',
  },
  saveButton: {
    fontSize: 17,
    fontWeight: '700',
    color: '#8B5CF6',
  },
  content: {
    flex: 1,
  },
  subtitle: {
    fontSize: 15,
    color: '#6B7280',
    textAlign: 'center',
    paddingVertical: 18,
    paddingHorizontal: 20,
    fontWeight: '500',
  },
  section: {
    backgroundColor: '#FFFFFF',
    marginHorizontal: 16,
    marginBottom: 20,
    borderRadius: 24,
    padding: 22,
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 3,
    borderWidth: 1,
    borderColor: '#E9D5FF',
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  sectionIcon: {
    fontSize: 28,
    marginRight: 12,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1A1A1A',
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
    marginTop: 12,
  },
  slider: {
    width: '100%',
    height: 40,
  },
  sliderValue: {
    fontSize: 24,
    fontWeight: '700',
    color: '#007AFF',
    textAlign: 'center',
    marginTop: 8,
  },
  starContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 8,
  },
  star: {
    fontSize: 32,
  },
  infoBox: {
    backgroundColor: '#E5F1FF',
    borderRadius: 12,
    padding: 12,
    marginTop: 12,
  },
  infoText: {
    fontSize: 12,
    color: '#007AFF',
    textAlign: 'center',
  },
  foodEntry: {
    marginBottom: 16,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  mealLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  buttonRow: {
    flexDirection: 'row',
    gap: 8,
  },
  qualityButton: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: '#F0F0F0',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#E0E0E0',
  },
  qualityButtonSelected: {
    backgroundColor: '#34C759',
    borderColor: '#34C759',
  },
  qualityGoodSelected: {
    backgroundColor: '#34C759',
  },
  qualityOkSelected: {
    backgroundColor: '#FFD93D',
  },
  qualityPoorSelected: {
    backgroundColor: '#FF6B6B',
  },
  qualityButtonText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#666',
  },
  qualityButtonTextSelected: {
    color: '#FFF',
  },
  notesInput: {
    marginTop: 8,
    backgroundColor: '#F9F9F9',
    borderRadius: 10,
    padding: 12,
    fontSize: 14,
    color: '#333',
    borderWidth: 1,
    borderColor: '#E8E8E8',
  },
  deviceDataBox: {
    backgroundColor: '#F0F9F6',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#D0F0E4',
  },
  deviceDataLabel: {
    fontSize: 12,
    color: '#34C759',
    marginBottom: 4,
  },
  deviceDataValue: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1A5A3A',
  },
  addButton: {
    marginTop: 12,
    backgroundColor: '#F5F5F7',
    borderRadius: 12,
    padding: 16,
    borderWidth: 2,
    borderStyle: 'dashed',
    borderColor: '#007AFF',
    alignItems: 'center',
  },
  addButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#007AFF',
  },
  expandedSection: {
    marginTop: 16,
  },
  chipGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  chip: {
    paddingHorizontal: 18,
    paddingVertical: 11,
    borderRadius: 22,
    backgroundColor: '#F3F4F6',
    borderWidth: 2,
    borderColor: '#E5E7EB',
  },
  chipSelected: {
    backgroundColor: '#8B5CF6',
    borderColor: '#8B5CF6',
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 3,
  },
  chipText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#6B7280',
  },
  chipTextSelected: {
    color: '#FFFFFF',
  },
  intensityButton: {
    flex: 1,
    paddingVertical: 13,
    borderRadius: 12,
    backgroundColor: '#F3F4F6',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#E5E7EB',
  },
  intensityButtonSelected: {
    backgroundColor: '#8B5CF6',
    borderColor: '#8B5CF6',
    shadowColor: '#8B5CF6',
    shadowOpacity: 0.25,
    elevation: 2,
  },
  intensityButtonText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#6B7280',
  },
  intensityButtonTextSelected: {
    color: '#FFF',
  },
  feelingButton: {
    flex: 1,
    paddingVertical: 10,
    paddingHorizontal: 8,
    borderRadius: 10,
    backgroundColor: '#F9F9FB',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#E8E8E8',
    marginHorizontal: 3,
  },
  feelingButtonSelected: {
    backgroundColor: '#34C759',
    borderColor: '#34C759',
  },
  feelingButtonText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#666',
  },
  feelingButtonTextSelected: {
    color: '#FFF',
  },
  socialButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 12,
    backgroundColor: '#F0F0F0',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#E0E0E0',
  },
  socialButtonSelected: {
    backgroundColor: '#34C759',
    borderColor: '#34C759',
  },
  socialEmoji: {
    fontSize: 20,
    marginBottom: 4,
  },
  socialButtonText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#666',
  },
  socialButtonTextSelected: {
    color: '#FFF',
  },
  textInput: {
    backgroundColor: '#F9F9F9',
    borderRadius: 12,
    padding: 14,
    fontSize: 14,
    color: '#333',
    borderWidth: 1,
    borderColor: '#E8E8E8',
  },
  screenBreakdown: {
    marginTop: 12,
    gap: 8,
  },
  screenTimeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#F9F9F9',
    padding: 12,
    borderRadius: 10,
  },
  screenTimeLabel: {
    fontSize: 14,
    color: '#333',
  },
  screenTimeValue: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  screenTimeMinutes: {
    fontSize: 14,
    fontWeight: '700',
    color: '#333',
  },
  screenTimeDelta: {
    fontSize: 12,
    fontWeight: '600',
  },
  sparkleButton: {
    marginTop: 12,
    backgroundColor: '#FFF5E6',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#FFE6A0',
    alignItems: 'center',
  },
  sparkleButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FF9500',
  },
  saveButtonMain: {
    marginHorizontal: 16,
    marginTop: 16,
    marginBottom: 8,
    backgroundColor: '#007AFF',
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    shadowColor: '#007AFF',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  saveButtonMainText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFF',
  },
  bottomPadding: {
    height: 40,
  },
});

