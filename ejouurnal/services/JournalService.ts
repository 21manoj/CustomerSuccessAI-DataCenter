import AsyncStorage from '@react-native-async-storage/async-storage';
import { JournalEntry, Emotion, DailySummary, Suggestion } from '../types';

const ENTRIES_KEY = 'journal_entries';
const EMOTIONS_KEY = 'emotions';

export class JournalService {
  private static instance: JournalService;
  
  public static getInstance(): JournalService {
    if (!JournalService.instance) {
      JournalService.instance = new JournalService();
    }
    return JournalService.instance;
  }

  // Default emotions
  private defaultEmotions: Emotion[] = [
    { id: '1', name: 'Happy', emoji: '😊', color: '#FFD700', intensity: 4 },
    { id: '2', name: 'Sad', emoji: '😢', color: '#4169E1', intensity: 2 },
    { id: '3', name: 'Angry', emoji: '😠', color: '#FF4500', intensity: 1 },
    { id: '4', name: 'Anxious', emoji: '😰', color: '#FF69B4', intensity: 2 },
    { id: '5', name: 'Excited', emoji: '🤩', color: '#FF1493', intensity: 5 },
    { id: '6', name: 'Calm', emoji: '😌', color: '#98FB98', intensity: 3 },
    { id: '7', name: 'Frustrated', emoji: '😤', color: '#FF6347', intensity: 2 },
    { id: '8', name: 'Grateful', emoji: '🙏', color: '#32CD32', intensity: 4 },
    { id: '9', name: 'Lonely', emoji: '😔', color: '#708090', intensity: 2 },
    { id: '10', name: 'Confident', emoji: '💪', color: '#00CED1', intensity: 4 },
  ];

  async getEmotions(): Promise<Emotion[]> {
    try {
      const stored = await AsyncStorage.getItem(EMOTIONS_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
      await this.saveEmotions(this.defaultEmotions);
      return this.defaultEmotions;
    } catch (error) {
      console.error('Error getting emotions:', error);
      return this.defaultEmotions;
    }
  }

  async saveEmotions(emotions: Emotion[]): Promise<void> {
    try {
      await AsyncStorage.setItem(EMOTIONS_KEY, JSON.stringify(emotions));
    } catch (error) {
      console.error('Error saving emotions:', error);
    }
  }

  async getEntries(): Promise<JournalEntry[]> {
    try {
      const stored = await AsyncStorage.getItem(ENTRIES_KEY);
      if (stored) {
        const entries = JSON.parse(stored);
        return entries.map((entry: any) => ({
          ...entry,
          timestamp: new Date(entry.timestamp)
        }));
      }
      return [];
    } catch (error) {
      console.error('Error getting entries:', error);
      return [];
    }
  }

  async saveEntry(entry: JournalEntry): Promise<void> {
    try {
      const entries = await this.getEntries();
      entries.push(entry);
      await AsyncStorage.setItem(ENTRIES_KEY, JSON.stringify(entries));
    } catch (error) {
      console.error('Error saving entry:', error);
    }
  }

  async getEntriesByDate(date: Date): Promise<JournalEntry[]> {
    const entries = await this.getEntries();
    const targetDate = date.toDateString();
    return entries.filter(entry => entry.timestamp.toDateString() === targetDate);
  }

  async generateDailySummary(date: Date): Promise<DailySummary> {
    const entries = await this.getEntriesByDate(date);
    
    if (entries.length === 0) {
      return {
        date: date.toDateString(),
        entries: [],
        dominantEmotion: this.defaultEmotions[0],
        summary: 'No entries for this day.',
        suggestions: []
      };
    }

    // Find dominant emotion
    const emotionCounts = new Map<string, number>();
    entries.forEach(entry => {
      const count = emotionCounts.get(entry.emotion.id) || 0;
      emotionCounts.set(entry.emotion.id, count + 1);
    });

    const dominantEmotionId = Array.from(emotionCounts.entries())
      .sort(([,a], [,b]) => b - a)[0][0];
    
    const emotions = await this.getEmotions();
    const dominantEmotion = emotions.find(e => e.id === dominantEmotionId) || emotions[0];

    // Generate summary
    const summary = this.generateSummaryText(entries, dominantEmotion);
    
    // Generate suggestions
    const suggestions = this.generateSuggestions(entries, dominantEmotion);

    return {
      date: date.toDateString(),
      entries,
      dominantEmotion,
      summary,
      suggestions
    };
  }

  private generateSummaryText(entries: JournalEntry[], dominantEmotion: Emotion): string {
    const timeOfDay = entries.map(entry => {
      const hour = entry.timestamp.getHours();
      if (hour < 12) return 'morning';
      if (hour < 17) return 'afternoon';
      return 'evening';
    });

    const locations = [...new Set(entries.map(entry => entry.where))];
    const people = [...new Set(entries.map(entry => entry.who))];

    let summary = `Today you felt ${dominantEmotion.name.toLowerCase()} (${dominantEmotion.emoji}) `;
    summary += `with ${entries.length} journal entry${entries.length > 1 ? 'ies' : ''}. `;
    
    if (timeOfDay.length > 0) {
      const mostCommonTime = timeOfDay.sort((a,b) => 
        timeOfDay.filter(v => v === a).length - timeOfDay.filter(v => v === b).length
      ).pop();
      summary += `Most of your entries were from the ${mostCommonTime}. `;
    }

    if (locations.length > 0) {
      summary += `You were in ${locations.join(', ')}. `;
    }

    if (people.length > 0) {
      summary += `You spent time with ${people.join(', ')}. `;
    }

    return summary;
  }

  private generateSuggestions(entries: JournalEntry[], dominantEmotion: Emotion): Suggestion[] {
    const suggestions: Suggestion[] = [];
    
    // Check for concerning patterns
    const negativeEmotions = entries.filter(entry => 
      ['Sad', 'Angry', 'Anxious', 'Frustrated', 'Lonely'].includes(entry.emotion.name)
    );

    if (negativeEmotions.length > entries.length * 0.6) {
      suggestions.push({
        id: '1',
        type: 'professional',
        title: 'Consider Professional Support',
        description: 'You\'ve been experiencing many difficult emotions lately. A mental health professional can help you work through these feelings.',
        action: 'Find a therapist or counselor',
        priority: 'high'
      });
    }

    if (dominantEmotion.name === 'Lonely') {
      suggestions.push({
        id: '2',
        type: 'community',
        title: 'Connect with Community',
        description: 'Feeling lonely? Consider joining a local group or online community that shares your interests.',
        action: 'Join a community group',
        priority: 'medium'
      });
    }

    if (dominantEmotion.name === 'Anxious') {
      suggestions.push({
        id: '3',
        type: 'community',
        title: 'Mindfulness Practice',
        description: 'Anxiety can be managed with mindfulness techniques. Consider joining a meditation group.',
        action: 'Try meditation or breathing exercises',
        priority: 'medium'
      });
    }

    // Positive reinforcement
    if (dominantEmotion.name === 'Happy' || dominantEmotion.name === 'Grateful') {
      suggestions.push({
        id: '4',
        type: 'community',
        title: 'Share Your Joy',
        description: 'You\'re feeling great! Consider sharing your positive energy with others.',
        action: 'Connect with friends or family',
        priority: 'low'
      });
    }

    return suggestions;
  }
}

