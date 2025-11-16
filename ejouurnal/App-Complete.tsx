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
import { SafeAreaView, StatusBar, StyleSheet, Alert } from 'react-native';
import { HomeScreen } from './components/HomeScreen';
import { QuickCheckIn, CheckInData } from './components/QuickCheckIn';
import { FulfillmentLineage } from './components/FulfillmentLineage';
import { WeeklyRitual } from './components/WeeklyRitual';
import WeeklyReviewScreen from './components/WeeklyReviewScreen';
import ProfileScreen from './components/ProfileScreen';
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
  | 'home' 
  | 'checkin' 
  | 'lineage' 
  | 'ritual'
  | 'weekly-review'
  | 'profile'
  | 'add-details'
  | 'journal-view'
  | 'journal-history'
  | 'settings'
  | 'paywall';

export default function AppComplete() {
  const [currentScreen, setCurrentScreen] = useState<Screen>('home');
  const [selectedDayPart, setSelectedDayPart] = useState<DayPart>('morning');
  const [completedDayParts, setCompletedDayParts] = useState<DayPart[]>([]);
  const [isPremium, setIsPremium] = useState(false);
  const [journalCount, setJournalCount] = useState(0);
  const [journalTone, setJournalTone] = useState<'reflective' | 'factual' | 'coach-like' | 'poetic'>('reflective');
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [currentStreak, setCurrentStreak] = useState(5);
  const [totalCheckIns, setTotalCheckIns] = useState(45);
  
  const storageService = StorageService.getInstance();

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
    // Mock journal generation (in production, call LLMPromptEngine)
    const mockJournal = {
      id: Date.now().toString(),
      date: new Date(),
      aiText: generateMockJournalText(journalTone),
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
    
    Alert.alert(
      '✨ Journal Generated!',
      'Your daily reflection is ready to read',
      [
        { text: 'Later', style: 'cancel' },
        { text: 'Read Now', onPress: () => setCurrentScreen('journal-view') }
      ]
    );
  };

  const generateMockJournalText = (tone: string): string => {
    // Mock journal texts for different tones
    const journals: Record<string, string> = {
      reflective: `You started the morning feeling good 🙂 after a solid 7.5 hours of sleep - the third consecutive night of quality rest. Your body responded well, carrying that energy through the day with 8,234 steps and a mindful 30-minute walk.\n\nMind-wise, you encountered work stress in the afternoon but took a 10-minute walk (a micro-act that's been boosting your MindScore by +7 points lately). Your mood lifted to "great" 😊 by evening.\n\nYou felt energized after a deep conversation - your 4th positive social interaction this week. This aligns with your intention to "show up with more presence."\n\nPurpose progress: You completed 2 of 3 micro-moves today. That's 67% weekly adherence, up from 50% last week.\n\nPattern Alert: This is your best day in 3 weeks. You scored 74 overall, up from 58 last week.\n\n---\nOverall Fulfillment: 74/100\nMeaningful Day: Yes ✨`,
      
      factual: `Date: ${new Date().toLocaleDateString()}\n\nCheck-ins: 4/4 completed\nAverage mood: Good (80/100)\nMicro-acts: Walk (1x), Meditation (1x)\n\nSleep: 7.5h (Quality: 4/5)\nActivity: 8,234 steps, 30min\nScreen: 3h 42min, Social: 32min\n\nScores:\n- Body: 72/100 (+3)\n- Mind: 68/100 (+5)\n- Soul: 85/100 (+2)\n- Purpose: 60/100 (+4)\n- Overall: 74/100\n\nWeekly: 2/3 micro-moves (67%)\nStatus: Meaningful Day`,
      
      'coach-like': `Great work today! 💪\n\nYou crushed it with 7.5h sleep - that's 3 days in a row! Your body is responding to this consistency.\n\nI noticed you handled work stress beautifully. Instead of scrolling, you took a 10-minute walk. That's exactly the intervention that's been adding +7 points to your MindScore. Keep choosing movement over screens!\n\nYour social connections were energizing today. You're living your intention to "show up with more presence."\n\nYou're at 67% on weekly micro-moves (2/3). One more and you'll hit your target!\n\nOverall: 74/100 - Meaningful Day achieved! ✨`,
      
      poetic: `October's amber light filtered through consciousness at dawn - another cycle of rest complete. Seven hours, thirty minutes. The fourth morning in gentle succession where sleep came easily, stayed deeply.\n\nYou moved through the day like water finding its course. Eight thousand steps written in invisible ink. A thirty-minute walk when afternoon weight grew heavy - not escape, but return.\n\nWords mattered today. Presence chosen over performance. The arithmetic of subtraction becoming addition.\n\nTwo promises kept toward purpose. The third waiting. Not perfection - presence.\n\nFulfillment: 74. Meaningful: Yes.\nThe quiet accumulation of intentional days.`
    };

    return journals[tone] || journals.reflective;
  };

  const handleAddDetails = (details: DetailData) => {
    console.log('Details saved:', details);
    // Save to storage
    storageService.saveDetailData(new Date(), details);
    
    // Update scores based on details (mock)
    setDailyScores({
      ...dailyScores,
      bodyScore: Math.min(100, dailyScores.bodyScore + 2),
      fulfillmentScore: Math.min(100, dailyScores.fulfillmentScore + 2),
    });

    Alert.alert(
      'Details Saved',
      'These will enrich your AI journal and insights'
    );
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

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#FAFBFC" />

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
        />
      )}

      {currentScreen === 'checkin' && (
        <QuickCheckIn
          dayPart={selectedDayPart}
          onComplete={handleCheckInComplete}
          onCancel={() => setCurrentScreen('home')}
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
          currentIntention={undefined}
          onSaveIntention={(intention, microMoves, antiGlitter) => {
            console.log('Saving intention:', intention);
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
          userName="Manoj Gupta"
          userEmail="manoj@example.com"
          isPremium={isPremium}
          currentStreak={currentStreak}
          totalCheckIns={totalCheckIns}
          joinDate={new Date('2025-10-01')}
          currentTone={journalTone}
          notificationsEnabled={notificationsEnabled}
          onEditProfile={() => {
            Alert.alert('Edit Profile', 'Profile editing coming soon!');
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
    backgroundColor: '#FAFBFC',
  },
});

