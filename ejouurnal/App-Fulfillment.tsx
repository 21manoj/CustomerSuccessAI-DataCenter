/**
 * FULFILLMENT APP - Complete Integration
 * 
 * Brings together all components:
 * - Home Screen with daypart chips
 * - Quick check-ins (≤20 seconds)
 * - Add Details (Premium)
 * - AI Journal generation & viewing
 * - Fulfillment Lineage with insights
 * - Weekly Ritual
 * - Settings & Profile
 * - Premium Paywall
 * 
 * Uses:
 * - InsightEngine for pattern detection
 * - StorageService for local persistence
 * - (Future) LLMPromptEngine for AI journals
 * - (Future) PrivacyEngine for cloud sync
 */

import React, { useState, useEffect } from 'react';
import { SafeAreaView, StatusBar, StyleSheet, Alert, Platform } from 'react-native';
import { HomeScreen } from './components/HomeScreen';
import { QuickCheckIn, CheckInData } from './components/QuickCheckIn';
import { FulfillmentLineage } from './components/FulfillmentLineage';
import { WeeklyRitual } from './components/WeeklyRitual';
import WeeklyReviewScreen from './components/WeeklyReviewScreen';
import ProfileScreen from './components/ProfileScreen';
import DemoJourneyScreen from './components/DemoJourneyScreen';
import { OnboardingScreen } from './components/OnboardingScreen';
import { AddDetailsScreen, DetailData } from './components/AddDetailsScreen';
import { JournalViewer } from './components/JournalViewer';
import { JournalHistory } from './components/JournalHistory';
import { SettingsScreen } from './components/SettingsScreen';
import { PremiumPaywall } from './components/PremiumPaywall';
import { StorageService } from './services/StorageService';
import {
  DayPart,
  CheckIn,
  DailyScores,
  WeeklySummary,
  LineageInsight,
  WeeklyIntention,
} from './types/fulfillment';

type Screen = 
  | 'onboarding'
  | 'home' 
  | 'checkin' 
  | 'lineage' 
  | 'ritual'
  | 'weekly-review'
  | 'profile'
  | 'demo-journey'
  | 'add-details'
  | 'journal-view'
  | 'journal-history'
  | 'settings'
  | 'paywall';

export default function AppFulfillment() {
  console.log('🎨 V2 App Loading with purple theme!');
  
  const [currentScreen, setCurrentScreen] = useState<Screen>('onboarding'); // V2: Start with onboarding
  const [hasCompletedOnboarding, setHasCompletedOnboarding] = useState(false);
  const [selectedDayPart, setSelectedDayPart] = useState<DayPart>('morning');
  const [completedDayParts, setCompletedDayParts] = useState<DayPart[]>([]);
  const [isPremium, setIsPremium] = useState(false);
  const [journalCount, setJournalCount] = useState(0);
  const [journalTone, setJournalTone] = useState<'reflective' | 'factual' | 'coach-like' | 'poetic'>('reflective');
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [currentStreak, setCurrentStreak] = useState(5);
  const [totalCheckIns, setTotalCheckIns] = useState(45);
  const [currentIntention, setCurrentIntention] = useState<WeeklyIntention | undefined>(undefined);
  const [userName, setUserName] = useState('Manoj Gupta');
  const [userEmail, setUserEmail] = useState('manoj@example.com');
  const [timezone, setTimezone] = useState('America/New_York');
  const [language, setLanguage] = useState('English');
  const [todayDetails, setTodayDetails] = useState<DetailData | null>(null);
  const [todayCheckIns, setTodayCheckIns] = useState<CheckInData[]>([]);
  const [userPersonalNotes, setUserPersonalNotes] = useState('');
  
  const storageService = StorageService.getInstance();

  // Web-compatible alert helper
  const showAlert = (title: string, message: string, onOk?: () => void) => {
    if (Platform.OS === 'web') {
      window.alert(`${title}\n\n${message}`);
      onOk && onOk();
    } else {
      Alert.alert(title, message, [{ text: 'OK', onPress: onOk }]);
    }
  };

  // Web-compatible prompt helper
  const showPrompt = (title: string, message: string, defaultValue: string, onSubmit: (value: string) => void) => {
    if (Platform.OS === 'web') {
      const result = window.prompt(`${title}\n${message}`, defaultValue);
      if (result !== null && result.trim()) {
        onSubmit(result.trim());
      }
    } else {
      Alert.prompt(title, message, (text) => {
        if (text && text.trim()) {
          onSubmit(text.trim());
        }
      }, 'plain-text', defaultValue);
    }
  };

  // Load saved state on mount (check if user has completed onboarding and set intention)
  useEffect(() => {
    const loadInitialState = async () => {
      // Check onboarding status
      const onboardingComplete = await storageService.getOnboardingStatus();
      setHasCompletedOnboarding(onboardingComplete);
      
      // Load intention
      const intentions = await storageService.getAllIntentions();
      if (intentions.length > 0) {
        const latest = intentions[intentions.length - 1];
        setCurrentIntention(latest);
        
        // If onboarding done and intention set, go straight to home
        if (onboardingComplete) {
          setCurrentScreen('home');
        } else {
          // First-time user, show onboarding
          setCurrentScreen('onboarding');
        }
      } else {
        // No intention set yet
        if (onboardingComplete) {
          // Returning user but no intention - go to ritual
          setCurrentScreen('ritual');
        } else {
          // First-time user - show onboarding
          setCurrentScreen('onboarding');
        }
      }
    };
    loadInitialState();
  }, []);

  // Mock data (replace with real data from storage)
  const [dailyScores, setDailyScores] = useState<DailyScores>({
    date: new Date(),
    bodyScore: 50,    // Start neutral
    mindScore: 50,    // Start neutral
    soulScore: 50,    // Start neutral
    purposeScore: 50, // Start neutral
    fulfillmentScore: 50,
    isMeaningfulDay: false, // Not meaningful until user checks in positively
  });

  const [historicalScores] = useState<DailyScores[]>([
    // Last 7 days of mock data
    { date: new Date(Date.now() - 6 * 24 * 60 * 60 * 1000), bodyScore: 65, mindScore: 55, soulScore: 70, purposeScore: 50, fulfillmentScore: 60, isMeaningfulDay: false },
    { date: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000), bodyScore: 70, mindScore: 62, soulScore: 75, purposeScore: 55, fulfillmentScore: 65, isMeaningfulDay: true },
    { date: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000), bodyScore: 68, mindScore: 58, soulScore: 72, purposeScore: 52, fulfillmentScore: 62, isMeaningfulDay: false },
    { date: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000), bodyScore: 75, mindScore: 70, soulScore: 80, purposeScore: 65, fulfillmentScore: 72, isMeaningfulDay: true },
    { date: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000), bodyScore: 73, mindScore: 68, soulScore: 78, purposeScore: 58, fulfillmentScore: 69, isMeaningfulDay: true },
    { date: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000), bodyScore: 70, mindScore: 65, soulScore: 82, purposeScore: 62, fulfillmentScore: 69, isMeaningfulDay: true },
    dailyScores,
  ]);

  const [weeklySummary] = useState<WeeklySummary>({
    weekStart: new Date(Date.now() - 6 * 24 * 60 * 60 * 1000),
    weekEnd: new Date(),
    meaningfulDaysCount: 5,
    avgBodyScore: 70,
    avgMindScore: 64,
    avgSoulScore: 77,
    avgPurposeScore: 57,
    avgFulfillmentScore: 67,
    topInsights: [],
    socialMinutesDelta: -18,
    purposeAdherence: 67,
  });

  const [insights] = useState<LineageInsight[]>([
    {
      id: '1',
      type: 'lag',
      title: 'Morning walks boost next-day focus',
      description: 'Days with ≥45 active minutes show +12 MindScore the next day. Your body movement directly impacts mental clarity.',
      confidence: 'high',
      sourceMetric: 'Active Minutes',
      targetMetric: 'Mind Score',
      lagDays: 1,
      impact: 12,
    },
    {
      id: '2',
      type: 'same-day',
      title: 'Meditation calms immediately',
      description: 'Check-ins after meditation show 15% higher mood ratings on average. Deep breathing activates your parasympathetic nervous system.',
      confidence: 'high',
      sourceMetric: 'Meditation',
      targetMetric: 'Mood',
      impact: 7,
    },
    {
      id: '3',
      type: 'breakpoint',
      title: 'Sleep threshold detected',
      description: 'When sleep drops below 6.5 hours, your MindScore typically drops by ~18 points. Prioritize 7+ hours for optimal clarity.',
      confidence: 'medium',
      sourceMetric: 'Sleep Hours',
      targetMetric: 'Mind Score',
      impact: -18,
    },
    {
      id: '4',
      type: 'purpose-path',
      title: 'Purpose builds on consistency',
      description: 'Completing 2+ micro-moves per day increases your PurposeScore by +15 points. Small daily actions compound into direction.',
      confidence: 'high',
      sourceMetric: 'Micro-Moves',
      targetMetric: 'Purpose Score',
      impact: 15,
    },
    {
      id: '5',
      type: 'same-day',
      title: 'Social media impacts clarity',
      description: 'Heavy social media use (>60 min) correlates with -8 MindScore in evening check-ins. Consider time limits.',
      confidence: 'medium',
      sourceMetric: 'Social Media Time',
      targetMetric: 'Mind Score',
      impact: -8,
    },
    {
      id: '6',
      type: 'same-day',
      title: 'Nature restores soul score',
      description: 'Spending 20+ minutes outdoors increases SoulScore by +10 points. Natural environments reduce cortisol and boost wellbeing.',
      confidence: 'high',
      sourceMetric: 'Nature Time',
      targetMetric: 'Soul Score',
      impact: 10,
    },
    {
      id: '7',
      type: 'lag',
      title: 'Exercise creates momentum',
      description: 'Days with vigorous exercise show +8 BodyScore and +6 MindScore for the next 2-3 days. Physical vitality cascades.',
      confidence: 'medium',
      sourceMetric: 'Exercise',
      targetMetric: 'Body & Mind',
      lagDays: 2,
      impact: 8,
    },
  ]);

  const [currentJournal, setCurrentJournal] = useState<any>(null);
  const [journals, setJournals] = useState<any[]>([]);

  // Load data on mount
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const checkIns = await storageService.getCheckInsForDate(new Date());
      const completedParts = checkIns.map(c => c.dayPart);
      setCompletedDayParts(completedParts);

      const allJournals = await storageService.getAllJournals();
      setJournals(allJournals);
      setJournalCount(allJournals.length);

      // Load today's journal if exists
      const todayJournal = await storageService.getJournalForDate(new Date());
      setCurrentJournal(todayJournal);
    } catch (error) {
      console.error('Error loading data:', error);
    }
  };

  const handleCheckInStart = (dayPart: DayPart) => {
    setSelectedDayPart(dayPart);
    setCurrentScreen('checkin');
  };

  // Helper: Map mood to score impact
  const getMoodScoreImpact = (mood: string): number => {
    const moodMap: Record<string, number> = {
      'very-low': -10,  // Rough day: significant negative impact
      'low': -5,        // Low: moderate negative impact
      'neutral': 0,     // Okay: no change
      'good': 5,        // Good: moderate positive impact
      'great': 10,      // Great: significant positive impact
    };
    return moodMap[mood] || 0;
  };

  // Helper: Calculate scores from check-in data
  const calculateScoresFromCheckIn = (data: CheckInData, currentScores: DailyScores) => {
    const baseMoodImpact = getMoodScoreImpact(data.mood);
    
    // Body score: affected by mood + contexts (sleep, exercise)
    const bodyImpact = baseMoodImpact + (data.contexts.includes('sleep') ? 5 : 0);
    
    // Mind score: affected by mood + work context + micro-acts (meditation)
    const mindImpact = baseMoodImpact + 
                      (data.contexts.includes('work') ? 3 : 0) +
                      (data.microAct === 'meditation' ? 5 : 0);
    
    // Soul score: affected by mood + social context + gratitude
    const soulImpact = baseMoodImpact + 
                      (data.contexts.includes('social') ? 4 : 0) +
                      (data.microAct === 'gratitude' ? 6 : 0);
    
    // Purpose score: primarily affected by purpose progress
    const purposeImpact = baseMoodImpact * 0.5 + 
                         (data.purposeProgress === 'yes' ? 15 : 
                          data.purposeProgress === 'partly' ? 8 : -3);
    
    // Calculate new scores (clamped between 0-100)
    const newBodyScore = Math.max(0, Math.min(100, currentScores.bodyScore + bodyImpact));
    const newMindScore = Math.max(0, Math.min(100, currentScores.mindScore + mindImpact));
    const newSoulScore = Math.max(0, Math.min(100, currentScores.soulScore + soulImpact));
    const newPurposeScore = Math.max(0, Math.min(100, currentScores.purposeScore + purposeImpact));
    
    // Fulfillment = weighted average (equal weights for now)
    const newFulfillment = Math.round((newBodyScore + newMindScore + newSoulScore + newPurposeScore) / 4);
    
    // Meaningful day = fulfillment >= 65
    const isMeaningfulDay = newFulfillment >= 65;
    
    return {
      bodyScore: newBodyScore,
      mindScore: newMindScore,
      soulScore: newSoulScore,
      purposeScore: newPurposeScore,
      fulfillmentScore: newFulfillment,
      isMeaningfulDay,
    };
  };

  const handleCheckInComplete = async (data: CheckInData) => {
    console.log('Check-in completed:', data);
    
    // Save check-in
    const newCheckIn: CheckIn = {
      id: Date.now().toString(),
      timestamp: new Date(),
      dayPart: selectedDayPart,
      mood: data.mood,
      contexts: data.contexts,
      microAct: data.microAct,
      purposeProgress: data.purposeProgress,
    };

    await storageService.saveCheckIn(newCheckIn);
    
    // Track today's check-ins for journal generation
    setTodayCheckIns([...todayCheckIns, data]);
    
    // Calculate new scores based on check-in data (ALWAYS update, not just first time)
    const newScores = calculateScoresFromCheckIn(data, dailyScores);
    console.log('📊 Score Update:', {
      dayPart: selectedDayPart,
      mood: data.mood,
      before: {
        body: dailyScores.bodyScore,
        mind: dailyScores.mindScore,
        soul: dailyScores.soulScore,
        purpose: dailyScores.purposeScore,
        fulfillment: dailyScores.fulfillmentScore,
      },
      after: newScores,
      meaningful: newScores.isMeaningfulDay ? '✨ YES' : '❌ NO'
    });
    setDailyScores({
      ...dailyScores,
      ...newScores,
      date: new Date(), // Update date
    });
    
    // Mark daypart as completed (for UI purposes)
    if (!completedDayParts.includes(selectedDayPart)) {
      const newCompleted = [...completedDayParts, selectedDayPart];
      setCompletedDayParts(newCompleted);

      // If night check-in and user is premium, generate journal
      if (selectedDayPart === 'night' && newCompleted.length === 4) {
        if (isPremium) {
          setTimeout(() => {
            generateJournal();
          }, 2000);
        } else if (journalCount < 3) {
          // Free trial: 3 journals
          setTimeout(() => {
            generateJournal();
          }, 2000);
        } else {
          // Show paywall
          setTimeout(() => {
            setCurrentScreen('paywall');
          }, 1000);
        }
      }
    }

    setCurrentScreen('home');
  };

  const generateJournal = async () => {
    try {
      console.log('🤖 Calling OpenAI to generate journal...');
      
      // Prepare enriched context for AI
      const enrichedContext = {
        userId: 'demo_user_001',
        tone: journalTone,
        scores: {
          body: dailyScores.bodyScore,
          mind: dailyScores.mindScore,
          soul: dailyScores.soulScore,
          purpose: dailyScores.purposeScore,
          fulfillment: dailyScores.fulfillmentScore,
          isMeaningfulDay: dailyScores.isMeaningfulDay,
        },
        checkIns: todayCheckIns.map(checkIn => ({
          mood: checkIn.mood,
          contexts: checkIn.contexts,
          microAct: checkIn.microAct,
          purposeProgress: checkIn.purposeProgress,
        })),
        details: todayDetails ? {
          sleepHours: todayDetails.sleepHours,
          sleepQuality: todayDetails.sleepQuality,
          exerciseType: todayDetails.exerciseType,
          exerciseDuration: todayDetails.exerciseDuration,
          exerciseIntensity: todayDetails.exerciseIntensity,
          exerciseFeeling: todayDetails.exerciseFeeling,
          foodQuality: todayDetails.foodQuality,
          hydration: todayDetails.hydration,
          socialMinutes: todayDetails.socialMinutes,
          screenMinutes: todayDetails.screenMinutes,
        } : null,
        intention: currentIntention ? {
          text: currentIntention.intention,
          microMoves: currentIntention.microMoves.map(m => m.description),
        } : null,
        userNotes: userPersonalNotes,
      };
      
      console.log('📦 Sending enriched context:', enrichedContext);
      
      // Call backend API to generate journal with OpenAI
      const response = await fetch('http://localhost:3005/api/journals/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(enrichedContext),
      });

      const data = await response.json();
      
      if (data.success && data.journal) {
        console.log('✅ OpenAI journal generated successfully!');
        
        // Create journal object from API response
        const newJournal = {
          id: data.journal.id || Date.now().toString(),
          date: new Date(),
          aiText: data.journal.content,
          tone: journalTone,
          scores: {
            overall: dailyScores.fulfillmentScore,
            body: dailyScores.bodyScore,
            mind: dailyScores.mindScore,
            soul: dailyScores.soulScore,
            purpose: dailyScores.purposeScore,
          },
          isMeaningfulDay: dailyScores.isMeaningfulDay,
        };

        await storageService.saveJournal(newJournal);
        setCurrentJournal(newJournal);
        setJournalCount(journalCount + 1);
        
        showAlert('✨ Journal Generated!', 'Your AI-generated daily reflection is ready to read', 
          () => setCurrentScreen('journal-view')
        );
      } else {
        throw new Error('Failed to generate journal');
      }
    } catch (error) {
      console.error('❌ Error generating journal:', error);
      
      // Fallback to mock journal if API fails
      console.log('⚠️ Falling back to mock journal...');
      const mockJournal = {
        id: Date.now().toString(),
        date: new Date(),
        aiText: generateMockJournalText(journalTone, dailyScores),
        tone: journalTone,
        scores: {
          overall: dailyScores.fulfillmentScore,
          body: dailyScores.bodyScore,
          mind: dailyScores.mindScore,
          soul: dailyScores.soulScore,
          purpose: dailyScores.purposeScore,
        },
        isMeaningfulDay: dailyScores.isMeaningfulDay,
      };

      await storageService.saveJournal(mockJournal);
      setCurrentJournal(mockJournal);
      setJournalCount(journalCount + 1);
      
      showAlert(
        '✨ Journal Generated!',
        'Your daily reflection is ready (offline mode)',
        () => setCurrentScreen('journal-view')
      );
    }
  };

  const generateMockJournalText = (tone: string, scores: DailyScores): string => {
    const overall = Math.round(scores.fulfillmentScore);
    const isRough = overall < 40;
    const isLow = overall >= 40 && overall < 65;
    const isGood = overall >= 65 && overall < 85;
    const isGreat = overall >= 85;
    
    if (tone === 'reflective') {
      if (isRough) {
        return `Today was rough, and that's okay. Your check-ins showed you're feeling low (${Math.round(scores.mindScore)} mind, ${Math.round(scores.soulScore)} soul), and your scores reflect that struggle.\n\nSome days are just hard. You're not failing - you're human. Tomorrow is a new chance to reset.\n\nWhat matters is that you showed up and tracked how you felt. That awareness is the first step.\n\n---\nOverall Fulfillment: ${overall}/100\nMeaningful Day: ${scores.isMeaningfulDay ? 'Yes ✨' : 'Not today'}`;
      } else if (isLow) {
        return `Today had its challenges. You felt "low" or "okay" through most check-ins, and your scores reflect that (${Math.round(scores.bodyScore)} body, ${Math.round(scores.mindScore)} mind).\n\nYou pushed through, even when it was hard. That takes strength.\n\nYour body scored ${Math.round(scores.bodyScore)}, mind ${Math.round(scores.mindScore)}, soul ${Math.round(scores.soulScore)}, purpose ${Math.round(scores.purposeScore)}. Not where you want to be, but you're tracking it - that's progress.\n\n---\nOverall Fulfillment: ${overall}/100\nMeaningful Day: ${scores.isMeaningfulDay ? 'Yes ✨' : 'Not today'}`;
      } else if (isGood) {
        return `Today was good. You felt "good" or "okay" through most check-ins, building steady momentum.\n\nYour body felt decent (${Math.round(scores.bodyScore)}), your mind was clear (${Math.round(scores.mindScore)}), and you connected with what matters (${Math.round(scores.soulScore)} soul, ${Math.round(scores.purposeScore)} purpose).\n\nThis is the sweet spot - not perfect, but present. You're showing up.\n\n---\nOverall Fulfillment: ${overall}/100\nMeaningful Day: ${scores.isMeaningfulDay ? 'Yes ✨' : 'Building toward it'}`;
      } else {
        return `Today was exceptional! You felt "great" through most check-ins, and it shows in your scores.\n\nBody: ${Math.round(scores.bodyScore)}, Mind: ${Math.round(scores.mindScore)}, Soul: ${Math.round(scores.soulScore)}, Purpose: ${Math.round(scores.purposeScore)} - everything aligned.\n\nDays like this remind you what's possible when you're energized, connected, and aligned with purpose.\n\n---\nOverall Fulfillment: ${overall}/100\nMeaningful Day: ${scores.isMeaningfulDay ? 'Yes ✨' : 'Close!'}`;
      }
    } else if (tone === 'factual') {
      return `Date: ${new Date().toLocaleDateString()}\n\nCheck-ins: ${completedDayParts.length}/4 completed\n\nScores:\n- Body: ${Math.round(scores.bodyScore)}/100\n- Mind: ${Math.round(scores.mindScore)}/100\n- Soul: ${Math.round(scores.soulScore)}/100\n- Purpose: ${Math.round(scores.purposeScore)}/100\n- Overall: ${overall}/100\n\nStatus: ${scores.isMeaningfulDay ? 'Meaningful Day' : 'Below meaningful threshold (65)'}`;
    } else if (tone === 'coach-like') {
      if (isRough) {
        return `Hey, tough day. I see you scored ${overall}/100 - that's rough, but you tracked it. That's the first win.\n\nBody: ${Math.round(scores.bodyScore)}, Mind: ${Math.round(scores.mindScore)}, Soul: ${Math.round(scores.soulScore)}, Purpose: ${Math.round(scores.purposeScore)}.\n\nTomorrow's a new day. Focus on one small thing: sleep, a walk, or calling someone. Small actions compound.\n\nYou got this. 💪`;
      } else if (isLow) {
        return `Today was a grind (${overall}/100), but you showed up. That counts.\n\nBody: ${Math.round(scores.bodyScore)}, Mind: ${Math.round(scores.mindScore)}, Soul: ${Math.round(scores.soulScore)}, Purpose: ${Math.round(scores.purposeScore)}.\n\nNot every day will feel great. But you're tracking, you're aware, and you're still moving forward. Tomorrow, aim for one thing that lifts your mind or soul. Small wins matter! 💪`;
      } else if (isGood) {
        return `Solid day! You scored ${overall}/100 - that's meaningful territory! 🎯\n\nBody: ${Math.round(scores.bodyScore)}, Mind: ${Math.round(scores.mindScore)}, Soul: ${Math.round(scores.soulScore)}, Purpose: ${Math.round(scores.purposeScore)}.\n\nYou're building momentum. Keep this up and you'll hit 70+ consistently. What worked today? Do more of that! 💪`;
      } else {
        return `CRUSHING IT! ${overall}/100 - that's exceptional! 🔥\n\nBody: ${Math.round(scores.bodyScore)}, Mind: ${Math.round(scores.mindScore)}, Soul: ${Math.round(scores.soulScore)}, Purpose: ${Math.round(scores.purposeScore)}.\n\nEverything aligned today. Remember this feeling. This is what's possible when you're energized, connected, and purposeful. Keep this momentum! 💪✨`;
      }
    } else if (tone === 'poetic') {
      if (isRough) {
        return `The day felt heavy. Low scores (${overall}) reflect the weight you carried.\n\nBody weary (${Math.round(scores.bodyScore)}). Mind clouded (${Math.round(scores.mindScore)}). Soul quiet (${Math.round(scores.soulScore)}). Purpose distant (${Math.round(scores.purposeScore)}).\n\nBut you documented it. That honesty is courage.\n\nTomorrow, another dawn. Another chance.`;
      } else if (isLow) {
        return `The day passed neither high nor low. A middle ground where effort met resistance.\n\nBody: ${Math.round(scores.bodyScore)}. Mind: ${Math.round(scores.mindScore)}. Soul: ${Math.round(scores.soulScore)}. Purpose: ${Math.round(scores.purposeScore)}.\n\nFulfillment: ${overall}. Not meaningfulyet. But measured. Tracked. Known.\n\nThe quiet accumulation of awareness.`;
      } else if (isGood) {
        return `October's light found you present. A day of ${overall} points - the sweet spot between striving and being.\n\nBody: ${Math.round(scores.bodyScore)}. Mind: ${Math.round(scores.mindScore)}. Soul: ${Math.round(scores.soulScore)}. Purpose: ${Math.round(scores.purposeScore)}.\n\nMeaningful: ${scores.isMeaningfulDay ? 'Yes' : 'Close'}. Not perfection. Presence.`;
      } else {
        return `Today, everything aligned. ${overall} points - the rare convergence of body, mind, soul, purpose.\n\nBody: ${Math.round(scores.bodyScore)}. Mind: ${Math.round(scores.mindScore)}. Soul: ${Math.round(scores.soulScore)}. Purpose: ${Math.round(scores.purposeScore)}.\n\nMeaningful: Yes.\n\nDays like this are why you track. The evidence of what's possible.`;
      }
    }
    
    // Default reflective
    return `Your day ended with a fulfillment score of ${overall}/100. Body: ${Math.round(scores.bodyScore)}, Mind: ${Math.round(scores.mindScore)}, Soul: ${Math.round(scores.soulScore)}, Purpose: ${Math.round(scores.purposeScore)}.\n\nMeaningful Day: ${scores.isMeaningfulDay ? 'Yes ✨' : 'Not today'}`;
  };

  const handleAddDetails = (details: DetailData) => {
    console.log('Details saved:', details);
    // Save to storage
    storageService.saveDetailData(new Date(), details);
    
    // Track today's details for journal generation
    setTodayDetails(details);
    
    // Update scores based on details (mock)
    setDailyScores({
      ...dailyScores,
      bodyScore: Math.min(100, dailyScores.bodyScore + 2),
      fulfillmentScore: Math.min(100, dailyScores.fulfillmentScore + 2),
    });

    if (Platform.OS === 'web') {
      alert('Details Saved\n\nThese will enrich your AI journal and insights');
    } else {
      Alert.alert(
        'Details Saved',
        'These will enrich your AI journal and insights'
      );
    }
    setCurrentScreen('home');
  };

  const handleJournalSave = (editedText: string, userNotes: string) => {
    if (currentJournal) {
      const updated = {
        ...currentJournal,
        userEditedText: editedText,
        userNotes: userNotes,
      };
      storageService.saveJournal(updated);
      // Track user notes for regeneration
      setUserPersonalNotes(userNotes);
      setCurrentJournal(updated);
    }
  };

  const handleToneChange = (newTone: any) => {
    setJournalTone(newTone);
    storageService.saveUserPreferences({} as any); // Save tone preference
  };

  const handleUpgrade = async (plan: 'monthly' | 'yearly') => {
    // In production: Integrate with RevenueCat/Stripe
    Alert.alert(
      'Upgrade to Premium',
      `Start your 7-day free trial of ${plan === 'yearly' ? 'Annual ($49.99/year)' : 'Monthly ($7.99/month)'} plan?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Start Trial',
          onPress: () => {
            setIsPremium(true);
            Alert.alert('Welcome to Premium! 🎉', 'All features unlocked');
            setCurrentScreen('home');
          }
        }
      ]
    );
  };

  const handleViewAddDetails = () => {
    if (!isPremium && journalCount >= 3) {
      setCurrentScreen('paywall');
    } else {
      setCurrentScreen('add-details');
    }
  };

  const handleCompleteOnboarding = async () => {
    // Mark onboarding as complete
    await storageService.setOnboardingStatus(true);
    setHasCompletedOnboarding(true);
    
    // Go to ritual to set intention
    setCurrentScreen('ritual');
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#F5F3FF" />

      {currentScreen === 'onboarding' && (
        <OnboardingScreen onComplete={handleCompleteOnboarding} />
      )}

      {currentScreen === 'home' && (
        <HomeScreen
          onCheckInStart={handleCheckInStart}
          onViewLineage={() => setCurrentScreen('lineage')}
          onWeeklyRitual={() => setCurrentScreen('weekly-review')}
          onViewAddDetails={handleViewAddDetails}
          onViewJournal={() => currentJournal && setCurrentScreen('journal-view')}
          onViewSettings={() => setCurrentScreen('profile')}
          dailyScores={dailyScores}
          weeklySummary={weeklySummary}
          completedDayParts={completedDayParts}
          hasJournal={!!currentJournal}
          isPremium={isPremium}
          userId="demo_user_001"
          currentIntention={currentIntention}
        />
      )}

      {currentScreen === 'checkin' && (
        <QuickCheckIn
          dayPart={selectedDayPart}
          onComplete={handleCheckInComplete}
          onCancel={() => setCurrentScreen('home')}
          onAddDetails={() => setCurrentScreen('add-details')}
          isNightCheckIn={selectedDayPart === 'night'}
        />
      )}

      {currentScreen === 'lineage' && (
        <FulfillmentLineage
          dailyScores={historicalScores}
          insights={insights}
          onBack={() => setCurrentScreen('home')}
        />
      )}

      {currentScreen === 'ritual' && (
        <WeeklyRitual
          weeklySummary={weeklySummary}
          currentIntention={currentIntention}
          onSaveIntention={async (intention, microMovesStrings, antiGlitter) => {
            console.log('Saving intention:', { intention, microMoves: microMovesStrings, antiGlitter });
            
            // Convert string[] to MicroMove[]
            const microMoves = microMovesStrings.map((move, index) => ({
              id: `${Date.now()}_${index}`,
              description: move,
              completed: false,
            }));
            
            // Create intention object
            const weeklyIntention: WeeklyIntention = {
              id: Date.now().toString(),
              weekStart: new Date(),
              intention: intention,
              microMoves: microMoves,
              antiGlitterExperiment: antiGlitter,
            };
            
            // Save to storage
            await storageService.saveWeeklyIntention(weeklyIntention);
            
            // Update state
            setCurrentIntention(weeklyIntention);
            
            // Show success and go back
            Alert.alert('✨ Intention Set!', 'Your weekly intention has been saved.');
            setCurrentScreen('home');
          }}
          onBack={() => setCurrentScreen('home')}
        />
      )}

      {currentScreen === 'add-details' && (
        <AddDetailsScreen
          onSave={handleAddDetails}
          onBack={() => setCurrentScreen('home')}
        />
      )}

      {currentScreen === 'journal-view' && currentJournal && (
        <JournalViewer
          journal={currentJournal}
          onBack={() => setCurrentScreen('home')}
          onSave={handleJournalSave}
          onRegenerate={() => {
            generateJournal();
            Alert.alert('Journal Regenerated', 'Generated with fresh insights');
          }}
          onExport={() => {
            Alert.alert('Export', 'Exporting as PDF...');
          }}
        />
      )}

      {currentScreen === 'journal-history' && (
        <JournalHistory
          journals={journals}
          onBack={() => setCurrentScreen('home')}
          onSelectJournal={(journal) => {
            setCurrentJournal(journal);
            setCurrentScreen('journal-view');
          }}
        />
      )}

      {currentScreen === 'settings' && (
        <SettingsScreen
          onBack={() => setCurrentScreen('home')}
          currentTone={journalTone}
          onToneChange={handleToneChange}
          onPreviewJournal={(tone) => {
            setJournalTone(tone);
            if (currentJournal) {
              setCurrentScreen('journal-view');
            }
          }}
          cloudSyncEnabled={false}
          onCloudSyncToggle={(enabled) => {
            console.log('Cloud sync:', enabled);
          }}
        />
      )}

      {currentScreen === 'weekly-review' && (
        <WeeklyReviewScreen
          onBack={() => setCurrentScreen('home')}
          onSetIntention={() => setCurrentScreen('ritual')}
          onViewInsights={() => setCurrentScreen('lineage')}
          weeklySummary={{
            meaningfulDaysCount: weeklySummary.meaningfulDaysCount,
            avgBodyScore: weeklySummary.avgBodyScore,
            avgMindScore: weeklySummary.avgMindScore,
            avgSoulScore: weeklySummary.avgSoulScore,
            avgPurposeScore: weeklySummary.avgPurposeScore,
            avgFulfillment: weeklySummary.avgFulfillmentScore,
            purposeAdherence: weeklySummary.purposeAdherence,
            totalCheckIns: completedDayParts.length,
            topInsights: insights.slice(0, 3),
            previousWeekMDW: 3,
          }}
          dailyBreakdown={historicalScores.map((score, index) => ({
            date: score.date,
            dayName: score.date.toLocaleDateString('en-US', { weekday: 'short' }),
            scores: {
              body: score.bodyScore,
              mind: score.mindScore,
              soul: score.soulScore,
              purpose: score.purposeScore,
            },
            checkInsCompleted: index === 6 ? completedDayParts.length : Math.floor(Math.random() * 4) + 1,
            isMeaningfulDay: score.isMeaningfulDay,
            highlight: index === 2 ? 'BEST DAY' : undefined,
          }))}
        />
      )}

      {currentScreen === 'profile' && (
        <ProfileScreen
          onBack={() => setCurrentScreen('home')}
          userName={userName}
          userEmail={userEmail}
          isPremium={isPremium}
          currentStreak={currentStreak}
          totalCheckIns={totalCheckIns}
          joinDate={new Date('2025-10-01')}
          currentTone={journalTone}
          notificationsEnabled={notificationsEnabled}
          onEditProfile={() => {
            if (Platform.OS === 'web') {
              // Web: Show simple menu
              const choice = window.confirm('Edit Profile\n\nClick OK to change name, Cancel to change email');
              if (choice) {
                // Change name
                showPrompt('Update Name', 'Enter your name:', userName, (newName) => {
                  setUserName(newName);
                  showAlert('Success', 'Name updated!');
                });
              } else {
                // Change email
                showPrompt('Update Email', 'Enter your email:', userEmail, (newEmail) => {
                  setUserEmail(newEmail);
                  showAlert('Success', 'Email updated!');
                });
              }
            } else {
              // Native: Use Alert.alert
              Alert.alert(
                'Edit Profile',
                'What would you like to edit?',
                [
                  {
                    text: 'Change Name',
                    onPress: () => {
                      showPrompt('Update Name', 'Enter your name:', userName, (newName) => {
                        setUserName(newName);
                        showAlert('Success', 'Name updated!');
                      });
                    }
                  },
                  {
                    text: 'Change Email',
                    onPress: () => {
                      showPrompt('Update Email', 'Enter your email:', userEmail, (newEmail) => {
                        setUserEmail(newEmail);
                        showAlert('Success', 'Email updated!');
                      });
                    }
                  },
                  { text: 'Cancel', style: 'cancel' },
                ]
              );
            }
          }}
          onManagePremium={() => {
            if (isPremium) {
              Alert.alert(
                'Premium Subscription',
                'Active since Oct 1, 2025\nNext billing: Nov 1, 2025\n\nManage subscription in App Store settings.',
                [{ text: 'OK' }]
              );
            } else {
              setCurrentScreen('paywall');
            }
          }}
          onGenerateJournal={generateJournal}
          onViewJournalHistory={() => setCurrentScreen('journal-history')}
          onToneChange={handleToneChange}
          onToggleNotifications={setNotificationsEnabled}
          onExportData={() => {
            Alert.alert('Export Data', 'Data export functionality coming soon!');
          }}
          onLogout={() => {
            Alert.alert('Logged Out', 'You have been logged out.');
            setCurrentScreen('home');
          }}
          onViewDemo={() => setCurrentScreen('demo-journey')}
          onAppSettings={async () => {
            if (Platform.OS === 'web') {
              // Web: Simplified menu using prompts
              const action = window.prompt(
                `App Settings\n\nCurrent Settings:\n• Timezone: ${timezone}\n• Language: ${language}\n\nEnter:\n1 = Change Timezone\n2 = Change Language\n3 = Clear All Data`,
                '1'
              );
              
              if (action === '1') {
                // Change Timezone
                const tz = window.prompt(
                  'Select Timezone:\n1 = EST (New York)\n2 = CST (Chicago)\n3 = MST (Denver)\n4 = PST (Los Angeles)\n5 = GMT (London)\n6 = JST (Tokyo)',
                  '1'
                );
                const tzMap: Record<string, {zone: string, name: string}> = {
                  '1': {zone: 'America/New_York', name: 'EST'},
                  '2': {zone: 'America/Chicago', name: 'CST'},
                  '3': {zone: 'America/Denver', name: 'MST'},
                  '4': {zone: 'America/Los_Angeles', name: 'PST'},
                  '5': {zone: 'Europe/London', name: 'GMT'},
                  '6': {zone: 'Asia/Tokyo', name: 'JST'},
                };
                if (tz && tzMap[tz]) {
                  setTimezone(tzMap[tz].zone);
                  window.alert(`✅ Timezone set to ${tzMap[tz].name}`);
                }
              } else if (action === '2') {
                // Change Language
                const lang = window.prompt(
                  'Select Language:\n1 = English\n2 = Spanish (Coming Soon)\n3 = French (Coming Soon)\n4 = German (Coming Soon)',
                  '1'
                );
                if (lang === '1') {
                  setLanguage('English');
                  window.alert('✅ Language set to English');
                } else if (lang === '2' || lang === '3' || lang === '4') {
                  window.alert('Coming Soon - This language will be supported in a future update');
                }
              } else if (action === '3') {
                // Clear All Data
                const confirm = window.confirm('⚠️ WARNING!\n\nThis will delete ALL your journals, check-ins, and intentions.\n\nThis CANNOT be undone.\n\nAre you sure?');
                if (confirm) {
                  storageService.clearAllData().then(() => {
                    setCompletedDayParts([]);
                    setJournals([]);
                    setCurrentJournal(null);
                    setCurrentIntention(undefined);
                    setDailyScores({
                      date: new Date(),
                      bodyScore: 50,
                      mindScore: 50,
                      soulScore: 50,
                      purposeScore: 50,
                      fulfillmentScore: 50,
                      isMeaningfulDay: false,
                    });
                    window.alert('✅ Data Cleared\n\nAll data has been deleted. The app has been reset.');
                  });
                }
              }
            } else {
              // Native: Use Alert.alert with action sheet
              Alert.alert(
                'App Settings',
                `Current Settings:\n• Timezone: ${timezone}\n• Language: ${language}`,
                [
                  {
                    text: 'Change Timezone',
                    onPress: () => {
                      Alert.alert(
                        'Select Timezone',
                        'Choose your timezone:',
                        [
                          { text: 'America/New_York (EST)', onPress: () => { setTimezone('America/New_York'); showAlert('✅ Updated', 'Timezone set to EST'); } },
                          { text: 'America/Chicago (CST)', onPress: () => { setTimezone('America/Chicago'); showAlert('✅ Updated', 'Timezone set to CST'); } },
                          { text: 'America/Denver (MST)', onPress: () => { setTimezone('America/Denver'); showAlert('✅ Updated', 'Timezone set to MST'); } },
                          { text: 'America/Los_Angeles (PST)', onPress: () => { setTimezone('America/Los_Angeles'); showAlert('✅ Updated', 'Timezone set to PST'); } },
                          { text: 'Europe/London (GMT)', onPress: () => { setTimezone('Europe/London'); showAlert('✅ Updated', 'Timezone set to GMT'); } },
                          { text: 'Asia/Tokyo (JST)', onPress: () => { setTimezone('Asia/Tokyo'); showAlert('✅ Updated', 'Timezone set to JST'); } },
                          { text: 'Cancel', style: 'cancel' },
                        ]
                      );
                    }
                  },
                  {
                    text: 'Change Language',
                    onPress: () => {
                      Alert.alert(
                        'Select Language',
                        'Choose your language (future feature):',
                        [
                          { text: 'English', onPress: () => { setLanguage('English'); showAlert('✅ Updated', 'Language set to English'); } },
                          { text: 'Spanish (Coming Soon)', onPress: () => showAlert('Coming Soon', 'Spanish language support will be added in a future update.') },
                          { text: 'French (Coming Soon)', onPress: () => showAlert('Coming Soon', 'French language support will be added in a future update.') },
                          { text: 'German (Coming Soon)', onPress: () => showAlert('Coming Soon', 'German language support will be added in a future update.') },
                          { text: 'Cancel', style: 'cancel' },
                        ]
                      );
                    }
                  },
                  {
                    text: 'Clear All Data (Testing)',
                    style: 'destructive',
                    onPress: async () => {
                      Alert.alert(
                        '⚠️ Warning!',
                        'This will delete all your journals, check-ins, and intentions. This cannot be undone.',
                        [
                          { text: 'Cancel', style: 'cancel' },
                          {
                            text: 'Delete Everything',
                            style: 'destructive',
                            onPress: async () => {
                              await storageService.clearAllData();
                              // Reset state
                              setCompletedDayParts([]);
                              setJournals([]);
                              setCurrentJournal(null);
                              setCurrentIntention(undefined);
                              setDailyScores({
                                date: new Date(),
                                bodyScore: 50,
                                mindScore: 50,
                                soulScore: 50,
                                purposeScore: 50,
                                fulfillmentScore: 50,
                                isMeaningfulDay: false,
                              });
                              showAlert('✅ Data Cleared', 'All data has been deleted. The app has been reset.');
                            }
                          }
                        ]
                      );
                    }
                  },
                  { text: 'Cancel', style: 'cancel' },
                ]
              );
            }
          }}
        />
      )}

      {currentScreen === 'demo-journey' && (
        <DemoJourneyScreen
          onBack={() => setCurrentScreen('home')}
          onExitDemo={() => setCurrentScreen('home')}
        />
      )}

      {currentScreen === 'paywall' && (
        <PremiumPaywall
          trigger={journalCount >= 3 ? 'journal-limit' : 'add-details'}
          onUpgrade={handleUpgrade}
          onClose={() => setCurrentScreen('home')}
          showCloseButton={true}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F3FF', // V2: Light purple background
  },
});

