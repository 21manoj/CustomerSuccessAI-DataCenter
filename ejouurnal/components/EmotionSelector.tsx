import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Dimensions,
} from 'react-native';
import { Emotion } from '../types';

interface EmotionSelectorProps {
  emotions: Emotion[];
  selectedEmotion: Emotion | null;
  onEmotionSelect: (emotion: Emotion) => void;
}

const { width } = Dimensions.get('window');
const emotionSize = (width - 60) / 5; // 5 emotions per row with padding

export const EmotionSelector: React.FC<EmotionSelectorProps> = ({
  emotions,
  selectedEmotion,
  onEmotionSelect,
}) => {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>How are you feeling?</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scrollContainer}
      >
        {emotions.map((emotion) => (
          <TouchableOpacity
            key={emotion.id}
            style={[
              styles.emotionButton,
              {
                backgroundColor: selectedEmotion?.id === emotion.id 
                  ? emotion.color 
                  : '#f0f0f0',
                width: emotionSize,
                height: emotionSize,
              },
            ]}
            onPress={() => onEmotionSelect(emotion)}
            activeOpacity={0.7}
          >
            <Text style={styles.emotionEmoji}>{emotion.emoji}</Text>
            <Text style={[
              styles.emotionName,
              { color: selectedEmotion?.id === emotion.id ? '#fff' : '#333' }
            ]}>
              {emotion.name}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginVertical: 20,
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: 15,
    color: '#333',
  },
  scrollContainer: {
    paddingHorizontal: 10,
  },
  emotionButton: {
    marginHorizontal: 5,
    borderRadius: 15,
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3,
  },
  emotionEmoji: {
    fontSize: 24,
    marginBottom: 4,
  },
  emotionName: {
    fontSize: 10,
    fontWeight: '500',
    textAlign: 'center',
  },
});

