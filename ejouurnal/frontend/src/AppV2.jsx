import React, { useState } from 'react';
import { Heart, Brain, Zap, Target, ArrowLeft, TrendingUp, Calendar, Sun, Cloud, Moon, Sunrise, ChevronRight, Crown, Lock, Settings, User, Bell, Shield, Download, LogOut, Sparkles, Award, BarChart3, LineChart, Activity } from 'lucide-react';

const FulfillmentV2 = () => {
  const [currentScreen, setCurrentScreen] = useState('onboarding1');
  const [selectedDayPart, setSelectedDayPart] = useState('morning');
  const [checkInStep, setCheckInStep] = useState(0);
  const [currentUserId, setCurrentUserId] = useState(null);
  const [isPremium, setIsPremium] = useState(false);
  
  const API_BASE = 'http://localhost:3005';
  
  // Initialize user
  React.useEffect(() => {
    async function initUser() {
      try {
        const response = await fetch(`${API_BASE}/api/users`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            name: 'V2 User', 
            email: `v2_${Date.now()}@test.com`,
            persona: 'engaged'
          })
        });
        const data = await response.json();
        setCurrentUserId(data.id);
      } catch (error) {
        console.error('Error creating user:', error);
      }
    }
    initUser();
  }, []);

  // ONBOARDING SCREENS
  const Onboarding1 = () => (
    <div className="h-full bg-gradient-to-br from-blue-600 via-teal-500 to-green-400 flex flex-col items-center justify-center px-8 text-white">
      <div className="text-7xl mb-6 animate-pulse">🌱</div>
      <h1 className="text-3xl font-bold mb-2 text-center">Fulfillment</h1>
      <p className="text-center text-white/90 text-sm leading-relaxed mb-2">
        Track what truly matters.
      </p>
      <p className="text-center text-white/80 text-xs leading-relaxed mb-12 max-w-xs">
        4 quick check-ins daily. See how your choices ripple into calm, strength, and purpose.
      </p>
      <button
        onClick={() => setCurrentScreen('onboarding2')}
        className="bg-white text-blue-600 px-10 py-4 rounded-full font-semibold shadow-xl active:scale-95 transition-transform"
      >
        Get Started
      </button>
    </div>
  );

  const Onboarding2 = () => (
    <div className="h-full bg-gradient-to-br from-gray-50 via-blue-50 to-teal-50 flex flex-col">
      <div className="flex-1 flex flex-col items-center justify-center px-8">
        <div className="w-20 h-20 bg-gradient-to-br from-orange-400 to-red-400 rounded-3xl flex items-center justify-center mb-6 shadow-lg">
          <span className="text-4xl">✨</span>
        </div>
        <h2 className="text-2xl font-bold text-gray-800 mb-3 text-center">The Glitter Trap</h2>
        <p className="text-center text-gray-600 text-sm leading-relaxed px-4">
          Social feeds show everyone's highlight reel. You scroll through perfect lives and feel... less than.
          <br/><br/>
          <span className="font-semibold">But endless scroll doesn't equal fulfillment.</span>
        </p>
      </div>
      <div className="px-8 pb-8">
        <div className="flex gap-2 justify-center mb-6">
          <div className="w-8 h-1.5 rounded-full bg-blue-600"></div>
          <div className="w-8 h-1.5 rounded-full bg-gray-300"></div>
          <div className="w-8 h-1.5 rounded-full bg-gray-300"></div>
        </div>
        <button
          onClick={() => setCurrentScreen('onboarding3')}
          className="w-full bg-blue-600 text-white py-4 rounded-xl font-semibold active:scale-95 transition-transform"
        >
          Continue
        </button>
      </div>
    </div>
  );

  const Onboarding3 = () => (
    <div className="h-full bg-gradient-to-br from-gray-50 via-blue-50 to-teal-50 flex flex-col">
      <div className="flex-1 flex flex-col items-center justify-center px-8">
        <div className="w-20 h-20 bg-gradient-to-br from-teal-400 to-green-400 rounded-3xl flex items-center justify-center mb-6 shadow-lg">
          <span className="text-4xl">🔗</span>
        </div>
        <h2 className="text-2xl font-bold text-gray-800 mb-3 text-center">Your Fulfillment Lineage</h2>
        <p className="text-center text-gray-600 text-sm leading-relaxed px-4 mb-6">
          We show how your daily choices connect. How sleep affects focus. How movement creates calm. How purpose builds strength.
          <br/><br/>
          <span className="font-semibold">See the ripple effects of your life.</span>
        </p>
        
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-4 border border-teal-200 max-w-xs">
          <p className="text-xs text-gray-700 leading-relaxed">
            📊 "Morning walks → +12 MindScore next day"
            <br/>
            🧘 "Meditation → +7 immediate calm"
          </p>
        </div>
      </div>
      <div className="px-8 pb-8">
        <div className="flex gap-2 justify-center mb-6">
          <div className="w-8 h-1.5 rounded-full bg-gray-300"></div>
          <div className="w-8 h-1.5 rounded-full bg-blue-600"></div>
          <div className="w-8 h-1.5 rounded-full bg-gray-300"></div>
        </div>
        <button
          onClick={() => setCurrentScreen('onboarding4')}
          className="w-full bg-blue-600 text-white py-4 rounded-xl font-semibold active:scale-95 transition-transform"
        >
          Continue
        </button>
      </div>
    </div>
  );

  const Onboarding4 = () => (
    <div className="h-full bg-gradient-to-br from-gray-50 via-blue-50 to-teal-50 flex flex-col">
      <div className="flex-1 flex flex-col items-center justify-center px-8">
        <div className="w-20 h-20 bg-gradient-to-br from-blue-400 to-indigo-400 rounded-3xl flex items-center justify-center mb-6 shadow-lg">
          <span className="text-4xl">⚡</span>
        </div>
        <h2 className="text-2xl font-bold text-gray-800 mb-3 text-center">Track 4 Dimensions</h2>
        <p className="text-center text-gray-600 text-sm leading-relaxed mb-6 px-4">
          4 quick check-ins daily (≤20 seconds each).
          <br/>
          Morning • Day • Evening • Night
        </p>
        
        <div className="grid grid-cols-2 gap-3 w-full max-w-sm">
          <DimensionCard 
            icon={<Activity size={22} className="text-red-500" />}
            label="Body"
            description="Strength & Energy"
            color="bg-red-50"
          />
          <DimensionCard 
            icon={<Brain size={22} className="text-teal-500" />}
            label="Mind"
            description="Calm & Clarity"
            color="bg-teal-50"
          />
          <DimensionCard 
            icon={<Heart size={22} className="text-green-400" />}
            label="Soul"
            description="Meaning & Connection"
            color="bg-green-50"
          />
          <DimensionCard 
            icon={<Target size={22} className="text-yellow-500" />}
            label="Purpose"
            description="Direction"
            color="bg-yellow-50"
          />
        </div>
      </div>
      <div className="px-8 pb-8">
        <div className="flex gap-2 justify-center mb-6">
          <div className="w-8 h-1.5 rounded-full bg-gray-300"></div>
          <div className="w-8 h-1.5 rounded-full bg-gray-300"></div>
          <div className="w-8 h-1.5 rounded-full bg-blue-600"></div>
        </div>
        <button
          onClick={() => setCurrentScreen('home')}
          className="w-full bg-gradient-to-r from-blue-600 to-teal-600 text-white py-4 rounded-xl font-semibold shadow-lg active:scale-95 transition-transform"
        >
          Start My Journey
        </button>
      </div>
    </div>
  );

  // HOME SCREEN
  const HomeScreen = () => (
    <div className="h-full bg-gradient-to-br from-gray-50 to-blue-50 overflow-y-auto pb-20">
      <div className="pt-14 pb-4 px-6">
        <h1 className="text-2xl font-bold text-gray-800 mb-1">How's your day unfolding?</h1>
        <p className="text-sm text-gray-500">Tap a moment to check in</p>
      </div>

      {/* Daypart Chips */}
      <div className="px-6 mb-6">
        <div className="grid grid-cols-4 gap-2">
          <DayPartChip 
            emoji="🌅"
            label="Morning"
            time="6-10am"
            completed={true}
            onClick={() => {
              setSelectedDayPart('morning');
              setCurrentScreen('checkin-mood');
            }}
          />
          <DayPartChip 
            emoji="☀️"
            label="Day"
            time="10-4pm"
            completed={false}
            current={true}
            onClick={() => {
              setSelectedDayPart('day');
              setCurrentScreen('checkin-mood');
            }}
          />
          <DayPartChip 
            emoji="🌆"
            label="Evening"
            time="4-8pm"
            completed={false}
            onClick={() => setCurrentScreen('checkin-mood')}
          />
          <DayPartChip 
            emoji="🌙"
            label="Night"
            time="8pm+"
            completed={false}
            onClick={() => setCurrentScreen('checkin-mood')}
          />
        </div>
      </div>

      {/* Today's Fulfillment */}
      <div className="px-6 mb-4">
        <div className="bg-white rounded-3xl p-6 shadow-lg">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Today's Fulfillment</h3>
          
          <div className="text-center mb-6">
            <div className="text-5xl font-extrabold text-blue-600 mb-1">71</div>
            <div className="text-xs text-gray-500">Overall Score</div>
          </div>

          <div className="space-y-3">
            <ScoreBar label="Body" score={72} color="bg-red-400" />
            <ScoreBar label="Mind" score={68} color="bg-teal-400" />
            <ScoreBar label="Soul" score={85} color="bg-green-400" />
            <ScoreBar label="Purpose" score={60} color="bg-yellow-400" />
          </div>

          <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded-xl p-3 text-center">
            <span className="text-sm font-semibold text-yellow-700">✨ Meaningful Day</span>
          </div>
        </div>
      </div>

      {/* This Week */}
      <div className="px-6 mb-4">
        <div className="bg-white rounded-3xl p-6 shadow-lg">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-700">This Week</h3>
            <button 
              onClick={() => setCurrentScreen('weekly-ritual')}
              className="text-sm font-semibold text-blue-600"
            >
              Review →
            </button>
          </div>

          <div className="text-center mb-4 pb-4 border-b border-gray-100">
            <div className="flex items-center justify-center gap-2 mb-1">
              <div className="text-5xl font-extrabold text-green-500">5</div>
              <div className="text-2xl">📈</div>
            </div>
            <div className="text-sm text-gray-600">Meaningful Days</div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-800">67%</div>
              <div className="text-xs text-gray-500">Purpose<br/>micro-moves</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">-18m</div>
              <div className="text-xs text-gray-500">Social<br/>vs baseline</div>
            </div>
          </div>
        </div>
      </div>

      {/* Fulfillment Lineage Button */}
      <div className="px-6 mb-6">
        <button
          onClick={() => setCurrentScreen('lineage')}
          className="w-full bg-gradient-to-r from-teal-500 to-blue-500 text-white rounded-2xl p-5 shadow-lg active:scale-95 transition-transform"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="text-3xl">🔗</div>
              <div className="text-left">
                <div className="font-semibold text-base">View Fulfillment Lineage</div>
                <div className="text-sm opacity-90">See how your choices connect</div>
              </div>
            </div>
            <ChevronRight size={24} className="opacity-80" />
          </div>
        </button>
      </div>

      <NavigationMenu currentScreen="home" setCurrentScreen={setCurrentScreen} />
    </div>
  );

  // CHECK-IN: MOOD STEP
  const CheckInMoodScreen = () => {
    const moods = [
      { emoji: '😢', label: 'Rough' },
      { emoji: '😕', label: 'Low' },
      { emoji: '😐', label: 'Okay' },
      { emoji: '🙂', label: 'Good' },
      { emoji: '😊', label: 'Great' },
    ];

    return (
      <div className="h-full bg-gradient-to-br from-blue-50 to-teal-50">
        <div className="pt-14 pb-4 px-6">
          <button onClick={() => setCurrentScreen('home')} className="mb-4">
            <div className="text-2xl">✕</div>
          </button>
          <div className="flex items-center gap-3 mb-2">
            <div className="text-3xl">🌅</div>
            <div className="text-xl font-bold text-gray-800">Morning Check-in</div>
          </div>
        </div>

        {/* Progress Dots */}
        <div className="flex justify-center gap-2 mb-8">
          <div className="w-2 h-2 rounded-full bg-blue-600"></div>
          <div className="w-2 h-2 rounded-full bg-gray-300"></div>
          <div className="w-2 h-2 rounded-full bg-gray-300"></div>
        </div>

        <div className="px-6">
          <h2 className="text-2xl font-bold text-gray-800 text-center mb-6">
            How are you feeling?
          </h2>

          <div className="flex justify-center gap-3 flex-wrap max-w-md mx-auto">
            {moods.map((mood, i) => (
              <button
                key={i}
                onClick={() => setCurrentScreen('checkin-context')}
                className="w-16 h-16 bg-white rounded-2xl flex flex-col items-center justify-center border-2 border-gray-200 hover:border-blue-500 hover:bg-blue-50 active:scale-95 transition-all"
              >
                <div className="text-3xl mb-1">{mood.emoji}</div>
                <div className="text-xs text-gray-600">{mood.label}</div>
              </button>
            ))}
          </div>

          <div className="text-center mt-12 text-sm text-gray-500">
            ⚡ Takes ~15 seconds
          </div>
        </div>
      </div>
    );
  };

  // CHECK-IN: CONTEXT STEP
  const CheckInContextScreen = () => {
    const [selected, setSelected] = useState([]);
    const contexts = [
      { emoji: '💼', label: 'Work' },
      { emoji: '😴', label: 'Sleep' },
      { emoji: '👥', label: 'Social' },
    ];

    const toggleContext = (label) => {
      if (selected.includes(label)) {
        setSelected(selected.filter(l => l !== label));
      } else if (selected.length < 2) {
        setSelected([...selected, label]);
      }
    };

    return (
      <div className="h-full bg-gradient-to-br from-blue-50 to-teal-50">
        <div className="pt-14 pb-4 px-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="text-3xl">🌅</div>
            <div className="text-xl font-bold text-gray-800">Morning Check-in</div>
          </div>
        </div>

        <div className="flex justify-center gap-2 mb-8">
          <div className="w-2 h-2 rounded-full bg-green-500"></div>
          <div className="w-2 h-2 rounded-full bg-blue-600"></div>
          <div className="w-2 h-2 rounded-full bg-gray-300"></div>
        </div>

        <div className="px-6">
          <h2 className="text-2xl font-bold text-gray-800 text-center mb-2">
            What's the context?
          </h2>
          <p className="text-sm text-gray-500 text-center mb-8">Pick 0-2 tags</p>

          <div className="flex justify-center gap-3 flex-wrap max-w-sm mx-auto mb-12">
            {contexts.map((ctx, i) => (
              <button
                key={i}
                onClick={() => toggleContext(ctx.label)}
                className={`px-6 py-4 rounded-2xl flex items-center gap-2 border-2 transition-all ${
                  selected.includes(ctx.label)
                    ? 'bg-blue-600 border-blue-600 text-white'
                    : 'bg-white border-gray-200 text-gray-700'
                }`}
              >
                <div className="text-2xl">{ctx.emoji}</div>
                <div className="font-semibold">{ctx.label}</div>
              </button>
            ))}
          </div>

          <button
            onClick={() => setCurrentScreen('checkin-microact')}
            className="w-full bg-blue-600 text-white py-4 rounded-xl font-semibold active:scale-95 transition-transform"
          >
            Next →
          </button>
        </div>
      </div>
    );
  };

  // CHECK-IN: MICRO-ACT STEP
  const CheckInMicroActScreen = () => {
    const microActs = [
      { emoji: '🙏', label: 'Gratitude' },
      { emoji: '💝', label: 'Kindness' },
      { emoji: '📚', label: 'Learning' },
      { emoji: '🌳', label: 'Nature' },
      { emoji: '🧘', label: 'Meditation' },
      { emoji: '🌬️', label: 'Breathwork' },
      { emoji: '🚶', label: 'Walk' },
      { emoji: '✍️', label: 'Journal' },
    ];

    return (
      <div className="h-full bg-gradient-to-br from-blue-50 to-teal-50">
        <div className="pt-14 pb-4 px-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="text-3xl">🌅</div>
            <div className="text-xl font-bold text-gray-800">Morning Check-in</div>
          </div>
        </div>

        <div className="flex justify-center gap-2 mb-8">
          <div className="w-2 h-2 rounded-full bg-green-500"></div>
          <div className="w-2 h-2 rounded-full bg-green-500"></div>
          <div className="w-2 h-2 rounded-full bg-blue-600"></div>
        </div>

        <div className="px-6">
          <h2 className="text-2xl font-bold text-gray-800 text-center mb-2">
            Any micro-act today?
          </h2>
          <p className="text-sm text-gray-500 text-center mb-8">Optional</p>

          <div className="grid grid-cols-4 gap-3 max-w-sm mx-auto mb-8">
            {microActs.map((act, i) => (
              <button
                key={i}
                onClick={() => setCurrentScreen('home')}
                className="aspect-square bg-white rounded-2xl flex flex-col items-center justify-center border-2 border-gray-200 hover:border-green-500 hover:bg-green-50 active:scale-95 transition-all"
              >
                <div className="text-2xl mb-1">{act.emoji}</div>
                <div className="text-xs text-gray-600 text-center px-1">{act.label}</div>
              </button>
            ))}
          </div>

          <button
            onClick={() => setCurrentScreen('home')}
            className="w-full text-gray-500 py-3 font-semibold"
          >
            Skip
          </button>
        </div>
      </div>
    );
  };

  // FULFILLMENT LINEAGE SCREEN
  const LineageScreen = () => (
    <div className="h-full bg-gradient-to-br from-gray-50 to-teal-50 overflow-y-auto pb-20">
      <div className="pt-14 pb-4 px-6">
        <button onClick={() => setCurrentScreen('home')} className="mb-4">
          <ArrowLeft size={24} className="text-gray-600" />
        </button>
        <h1 className="text-2xl font-bold text-gray-800 mb-1">Fulfillment Lineage</h1>
        <p className="text-sm text-gray-600">How your choices ripple into calm, strength, and purpose</p>
      </div>

      {/* Timeline */}
      <div className="px-6 mb-6">
        <div className="bg-white rounded-3xl p-5 shadow-lg">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-700">Your Journey</h3>
            <div className="flex gap-2">
              <button className="px-3 py-1 bg-blue-600 text-white rounded-lg text-xs font-semibold">Week</button>
              <button className="px-3 py-1 bg-gray-100 text-gray-600 rounded-lg text-xs font-semibold">Month</button>
            </div>
          </div>

          {/* Timeline visualization */}
          <div className="flex gap-3 overflow-x-auto pb-2">
            {[...Array(7)].map((_, i) => (
              <div key={i} className="flex-shrink-0">
                <div className="flex gap-1 mb-2" style={{height: '80px', alignItems: 'flex-end'}}>
                  <div className="w-2 bg-red-400 rounded-t" style={{height: `${65 + i * 2}%`}}></div>
                  <div className="w-2 bg-teal-400 rounded-t" style={{height: `${60 + i * 3}%`}}></div>
                  <div className="w-2 bg-green-400 rounded-t" style={{height: `${70 + i * 2}%`}}></div>
                  <div className="w-2 bg-yellow-400 rounded-t" style={{height: `${55 + i * 5}%`}}></div>
                </div>
                <div className="text-xs text-gray-500 text-center">
                  {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][i]}
                </div>
                {i === 4 && <div className="text-center text-lg">⭐</div>}
              </div>
            ))}
          </div>

          <div className="flex justify-center gap-4 mt-4 pt-4 border-t border-gray-100">
            <LegendItem color="bg-red-400" label="Body" />
            <LegendItem color="bg-teal-400" label="Mind" />
            <LegendItem color="bg-green-400" label="Soul" />
            <LegendItem color="bg-yellow-400" label="Purpose" />
          </div>
        </div>
      </div>

      {/* Key Connections */}
      <div className="px-6 mb-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Key Connections</h3>
        <p className="text-xs text-gray-500 mb-4">Patterns we're seeing in your data</p>

        <InsightCard
          icon="💡"
          title="Morning walks boost next-day focus"
          type="LAG • 1d lag"
          confidence="HIGH"
          description="Days with ≥45 active minutes show +12 MindScore the next day. Try a morning walk tomorrow."
          impact="+12 pts"
          color="border-yellow-400"
        />

        <InsightCard
          icon="🧘"
          title="Meditation calms immediately"
          type="SAME-DAY"
          confidence="HIGH"
          description="Check-ins after meditation show 15% higher mood ratings on average. Keep it up!"
          impact="+7 pts"
          color="border-teal-400"
        />

        <InsightCard
          icon="⚠️"
          title="Sleep threshold detected"
          type="BREAKPOINT"
          confidence="MEDIUM"
          description="When sleep drops below 6.5 hours, your MindScore typically drops by ~18 points. Prioritize rest."
          impact="-18 pts"
          color="border-red-400"
        />
      </div>

      {/* What to Try */}
      <div className="px-6 mb-6">
        <div className="bg-gradient-to-r from-blue-500 to-teal-500 text-white rounded-3xl p-6 shadow-xl">
          <div className="text-3xl mb-3">💡</div>
          <h3 className="font-bold text-lg mb-2">Your most impactful pattern</h3>
          <p className="text-sm opacity-95">
            Days with ≥45 active minutes typically show +12 MindScore the next day. Try a morning walk tomorrow.
          </p>
        </div>
      </div>

      <NavigationMenu currentScreen="insights" setCurrentScreen={setCurrentScreen} />
    </div>
  );

  // WEEKLY RITUAL SCREEN
  const WeeklyRitualScreen = () => (
    <div className="h-full bg-gradient-to-br from-gray-50 to-purple-50 overflow-y-auto pb-20">
      <div className="pt-14 pb-4 px-6">
        <button onClick={() => setCurrentScreen('home')} className="mb-4">
          <ArrowLeft size={24} className="text-gray-600" />
        </button>
        <h1 className="text-2xl font-bold text-gray-800 mb-1">Weekly Ritual</h1>
        <p className="text-sm text-gray-600">10-minute Sunday planning</p>
      </div>

      {/* Last Week */}
      <div className="px-6 mb-6">
        <div className="bg-white rounded-3xl p-6 shadow-lg">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Last Week's Fulfillment</h3>
          
          <div className="text-center mb-4 pb-4 border-b border-gray-100">
            <div className="flex items-center justify-center gap-3 mb-1">
              <div className="text-5xl font-extrabold text-green-500">5</div>
              <div className="text-3xl">📈</div>
            </div>
            <div className="text-sm text-gray-600">Meaningful Days</div>
          </div>

          <div className="flex justify-around">
            <div className="text-center">
              <div className="w-3 h-3 rounded-full bg-red-400 mx-auto mb-1"></div>
              <div className="text-xl font-bold text-gray-800">70</div>
              <div className="text-xs text-gray-500">Body</div>
            </div>
            <div className="text-center">
              <div className="w-3 h-3 rounded-full bg-teal-400 mx-auto mb-1"></div>
              <div className="text-xl font-bold text-gray-800">64</div>
              <div className="text-xs text-gray-500">Mind</div>
            </div>
            <div className="text-center">
              <div className="w-3 h-3 rounded-full bg-green-400 mx-auto mb-1"></div>
              <div className="text-xl font-bold text-gray-800">77</div>
              <div className="text-xs text-gray-500">Soul</div>
            </div>
            <div className="text-center">
              <div className="w-3 h-3 rounded-full bg-yellow-400 mx-auto mb-1"></div>
              <div className="text-xl font-bold text-gray-800">57</div>
              <div className="text-xs text-gray-500">Purpose</div>
            </div>
          </div>
        </div>
      </div>

      {/* This Week's Intention */}
      <div className="px-6 mb-6">
        <div className="bg-white rounded-3xl p-6 shadow-lg">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">This Week's Intention</h3>
          <p className="text-xs text-gray-500 mb-4">One sentence. What matters most?</p>
          
          <textarea
            className="w-full bg-gray-50 border border-gray-200 rounded-xl p-4 text-sm resize-none"
            rows={3}
            placeholder="e.g., Show up with more presence for my family"
          ></textarea>
          <div className="text-right text-xs text-gray-400 mt-1">0/120</div>
        </div>
      </div>

      {/* 3 Micro-Moves */}
      <div className="px-6 mb-6">
        <div className="bg-white rounded-3xl p-6 shadow-lg">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">3 Micro-Moves</h3>
          <p className="text-xs text-gray-500 mb-4">Small, specific actions</p>
          
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-7 h-7 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-bold flex-shrink-0">1</div>
              <input
                className="flex-1 bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm"
                placeholder="e.g., 10-min morning walk 3x"
              />
            </div>
            <div className="flex items-center gap-3">
              <div className="w-7 h-7 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-bold flex-shrink-0">2</div>
              <input
                className="flex-1 bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm"
                placeholder="e.g., Read 2 chapters of book"
              />
            </div>
            <div className="flex items-center gap-3">
              <div className="w-7 h-7 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-bold flex-shrink-0">3</div>
              <input
                className="flex-1 bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm"
                placeholder="e.g., Call a friend I've missed"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Anti-Glitter Experiment */}
      <div className="px-6 mb-6">
        <div className="bg-white rounded-3xl p-6 shadow-lg">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Anti-Glitter Experiment</h3>
          <p className="text-xs text-gray-500 mb-4">Optional: Try one boundary</p>
          
          <div className="flex flex-wrap gap-2">
            {['30-min morning no-feed', 'Grayscale home screen', 'No phone first hour', 'Social apps only after 6pm'].map((exp, i) => (
              <button key={i} className="px-3 py-2 bg-gray-100 text-gray-700 text-xs rounded-full border border-gray-200 hover:border-blue-500 hover:bg-blue-50">
                {exp}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="px-6 mb-6">
        <button
          onClick={() => setCurrentScreen('home')}
          className="w-full bg-blue-600 text-white py-4 rounded-xl font-semibold shadow-lg active:scale-95 transition-transform"
        >
          Save Intention
        </button>
      </div>

      <NavigationMenu currentScreen="home" setCurrentScreen={setCurrentScreen} />
    </div>
  );

  // PREMIUM SCREEN
  const PremiumScreen = () => (
    <div className="h-full bg-gradient-to-br from-purple-600 via-blue-600 to-teal-600 overflow-y-auto pb-20">
      <div className="pt-14 pb-6 px-6">
        <div className="flex items-center justify-center mb-4">
          <Crown size={56} className="text-yellow-300" />
        </div>
        <h1 className="text-3xl font-bold text-white text-center mb-2">Premium</h1>
        <p className="text-center text-white/90 text-sm">Unlock deep insights</p>
      </div>

      <div className="px-6 space-y-4 pb-6">
        <PremiumFeatureCard
          icon={<Sparkles size={24} />}
          title="Deep Lineage Analysis"
          description="Lag correlations, breakpoint detection, and personalized score weights"
        />
        <PremiumFeatureCard
          icon={<Target size={24} />}
          title="Purpose Programs"
          description="Guided 4-week tracks: Calm, Strength, Relationships, and more"
        />
        <PremiumFeatureCard
          icon={<BarChart3 size={24} />}
          title="Coach Summaries"
          description="Weekly PDF export with charts + insights for you or your therapist"
        />
        <PremiumFeatureCard
          icon={<Activity size={24} />}
          title="Focus Toolkit"
          description="App blocking, custom rituals, and deep work timer with insights"
        />
        <PremiumFeatureCard
          icon={<Download size={24} />}
          title="Data Export & Backup"
          description="End-to-end encrypted cloud backups and CSV export"
        />

        <div className="bg-white rounded-3xl p-6 shadow-xl mt-8">
          <div className="text-center mb-4">
            <p className="text-3xl font-bold text-gray-800 mb-1">$7.99/month</p>
            <p className="text-sm text-gray-500">or $49.99/year</p>
          </div>
          <button className="w-full bg-gradient-to-r from-purple-600 to-blue-600 text-white py-4 rounded-xl font-semibold shadow-lg active:scale-95 transition-transform mb-3">
            Start Free Trial
          </button>
          <p className="text-xs text-gray-500 text-center">7 days free, cancel anytime</p>
        </div>
      </div>

      <NavigationMenu currentScreen="premium" setCurrentScreen={setCurrentScreen} />
    </div>
  );

  // PROFILE SCREEN
  const ProfileScreen = () => (
    <div className="h-full bg-gradient-to-br from-gray-50 to-gray-100 overflow-y-auto pb-20">
      <div className="pt-14 pb-6 px-6">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-20 h-20 bg-gradient-to-br from-blue-400 to-teal-400 rounded-full flex items-center justify-center text-white text-2xl font-bold">
            MG
          </div>
          <div>
            <h2 className="text-xl font-semibold text-gray-800">Manoj Gupta</h2>
            <p className="text-sm text-gray-500">manoj@example.com</p>
          </div>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4 mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-blue-800">🔥 Current Streak</span>
            <span className="text-2xl font-bold text-blue-600">12 days</span>
          </div>
          <p className="text-xs text-blue-600">Keep going! Building consistency.</p>
        </div>
      </div>

      <div className="px-6 space-y-2 mb-6">
        <SettingsItem icon={User} label="Edit Profile" onClick={() => {}} />
        <SettingsItem icon={Bell} label="Notifications" badge="4x daily" onClick={() => {}} />
        <SettingsItem icon={Crown} label="Manage Subscription" onClick={() => setCurrentScreen('premium')} />
        <SettingsItem icon={Download} label="Export Data" onClick={() => {}} />
        <SettingsItem icon={Shield} label="Privacy & Security" onClick={() => {}} />
        <SettingsItem icon={Settings} label="App Settings" onClick={() => {}} />
      </div>

      <NavigationMenu currentScreen="profile" setCurrentScreen={setCurrentScreen} />
    </div>
  );

  // NAVIGATION MENU
  const NavigationMenu = ({ currentScreen, setCurrentScreen }) => (
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 safe-area-bottom z-50">
      <div className="flex justify-around py-2">
        <NavButton 
          icon={Calendar} 
          label="Today" 
          active={currentScreen === 'home'}
          onClick={() => setCurrentScreen('home')}
        />
        <NavButton 
          icon={TrendingUp} 
          label="Insights" 
          active={currentScreen === 'insights' || currentScreen === 'lineage'}
          onClick={() => setCurrentScreen('lineage')}
        />
        <NavButton 
          icon={Crown} 
          label="Premium" 
          active={currentScreen === 'premium'}
          onClick={() => setCurrentScreen('premium')}
        />
        <NavButton 
          icon={User} 
          label="Profile" 
          active={currentScreen === 'profile'}
          onClick={() => setCurrentScreen('profile')}
        />
      </div>
    </div>
  );

  const NavButton = ({ icon: Icon, label, active, onClick }) => (
    <button 
      onClick={onClick}
      className={`flex flex-col items-center gap-1 px-4 py-2 ${active ? 'text-blue-600' : 'text-gray-400'}`}
    >
      <Icon size={20} />
      <span className="text-xs font-medium">{label}</span>
    </button>
  );

  // Render Current Screen
  const renderScreen = () => {
    switch(currentScreen) {
      case 'onboarding1': return <Onboarding1 />;
      case 'onboarding2': return <Onboarding2 />;
      case 'onboarding3': return <Onboarding3 />;
      case 'onboarding4': return <Onboarding4 />;
      case 'home': return <HomeScreen />;
      case 'checkin-mood': return <CheckInMoodScreen />;
      case 'checkin-context': return <CheckInContextScreen />;
      case 'checkin-microact': return <CheckInMicroActScreen />;
      case 'lineage': return <LineageScreen />;
      case 'weekly-ritual': return <WeeklyRitualScreen />;
      case 'premium': return <PremiumScreen />;
      case 'profile': return <ProfileScreen />;
      default: return <HomeScreen />;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-4 md:p-8">
      <div className="relative">
        {/* iPhone Mockup Frame */}
        <div className="w-[375px] h-[812px] bg-black rounded-[50px] shadow-2xl relative overflow-hidden border-8 border-gray-800">
          {/* Notch */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-40 h-7 bg-black rounded-b-3xl z-50"></div>
          
          {/* Status Bar */}
          <div className="absolute top-0 left-0 right-0 h-11 z-40 px-8 flex items-center justify-between text-xs font-medium text-white">
            <span>9:41</span>
            <div className="flex items-center gap-1">
              <div className="w-4 h-3 border border-white rounded-sm"></div>
              <div className="w-1 h-2 bg-white rounded-sm"></div>
            </div>
          </div>
          
          {/* Screen Content */}
          <div className="w-full h-full">{renderScreen()}</div>
          
          {/* Home Indicator */}
          <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-32 h-1 bg-white/30 rounded-full"></div>
        </div>
        
        {/* Screen Label */}
        <div className="absolute -bottom-12 left-0 right-0 text-center text-white text-sm font-medium">
          {currentScreen.includes('onboarding') && 'Onboarding'}
          {currentScreen === 'home' && 'Home Screen'}
          {currentScreen.includes('checkin') && 'Quick Check-in (≤20s)'}
          {currentScreen === 'lineage' && 'Fulfillment Lineage'}
          {currentScreen === 'weekly-ritual' && 'Weekly Ritual'}
          {currentScreen === 'premium' && 'Premium Features'}
          {currentScreen === 'profile' && 'Profile & Settings'}
        </div>
      </div>
    </div>
  );
};

// Helper Components
const DimensionCard = ({ icon, label, description, color }) => (
  <div className={`${color} rounded-2xl p-4 border border-gray-200`}>
    <div className="mb-2">{icon}</div>
    <div className="text-sm font-bold text-gray-800">{label}</div>
    <div className="text-xs text-gray-600">{description}</div>
  </div>
);

const DayPartChip = ({ emoji, label, time, completed, current, onClick }) => (
  <button
    onClick={onClick}
    className={`relative flex flex-col items-center p-3 rounded-2xl border-2 transition-all active:scale-95 ${
      completed
        ? 'bg-green-50 border-green-400'
        : current
        ? 'bg-blue-50 border-blue-500 shadow-lg'
        : 'bg-white border-gray-200'
    }`}
  >
    {completed && (
      <div className="absolute top-1 right-1 w-5 h-5 bg-green-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
        ✓
      </div>
    )}
    <div className="text-2xl mb-1">{emoji}</div>
    <div className={`text-xs font-semibold ${completed ? 'text-green-700' : current ? 'text-blue-700' : 'text-gray-700'}`}>
      {label}
    </div>
    <div className="text-xs text-gray-500">{time}</div>
  </button>
);

const ScoreBar = ({ label, score, color }) => (
  <div>
    <div className="flex justify-between items-center mb-1">
      <span className="text-sm font-semibold text-gray-700">{label}</span>
      <span className="text-sm font-bold text-gray-800">{score}</span>
    </div>
    <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
      <div className={`h-full ${color} rounded-full`} style={{width: `${score}%`}}></div>
    </div>
  </div>
);

const LegendItem = ({ color, label }) => (
  <div className="flex items-center gap-2">
    <div className={`w-2.5 h-2.5 rounded-full ${color}`}></div>
    <span className="text-xs text-gray-600">{label}</span>
  </div>
);

const InsightCard = ({ icon, title, type, confidence, description, impact, color }) => (
  <div className={`bg-white rounded-2xl p-5 mb-3 shadow-md border-l-4 ${color}`}>
    <div className="flex items-start justify-between mb-2">
      <div className="flex items-start gap-3 flex-1">
        <div className="text-2xl">{icon}</div>
        <div className="flex-1">
          <div className="font-bold text-gray-800 text-sm mb-1">{title}</div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs text-gray-500 uppercase">{type}</span>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
              confidence === 'HIGH' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
            }`}>
              {confidence}
            </span>
          </div>
        </div>
      </div>
      <div className={`text-sm font-bold ${impact.startsWith('+') ? 'text-green-600' : 'text-red-600'}`}>
        {impact}
      </div>
    </div>
    <p className="text-xs text-gray-600 leading-relaxed">{description}</p>
  </div>
);

const PremiumFeatureCard = ({ icon, title, description, onClick }) => (
  <button onClick={onClick} className="w-full bg-white/90 backdrop-blur-sm rounded-2xl p-5 text-left shadow-lg active:scale-95 transition-transform">
    <div className="flex items-start gap-4">
      <div className="w-12 h-12 bg-gradient-to-br from-purple-100 to-blue-100 rounded-2xl flex items-center justify-center text-purple-600 flex-shrink-0">
        {icon}
      </div>
      <div className="flex-1">
        <h3 className="font-semibold text-gray-800 mb-1">{title}</h3>
        <p className="text-sm text-gray-600 leading-relaxed">{description}</p>
      </div>
      <ChevronRight size={20} className="text-gray-400 flex-shrink-0" />
    </div>
  </button>
);

const SettingsItem = ({ icon: Icon, label, badge, onClick }) => (
  <button onClick={onClick} className="w-full bg-white rounded-2xl p-4 flex items-center justify-between active:bg-gray-50 transition-colors shadow-sm">
    <div className="flex items-center gap-3">
      <Icon size={20} className="text-gray-600" />
      <span className="text-sm font-medium text-gray-800">{label}</span>
    </div>
    <div className="flex items-center gap-2">
      {badge && <span className="text-xs text-gray-500 font-medium">{badge}</span>}
      <ChevronRight size={18} className="text-gray-400" />
    </div>
  </button>
);

export default FulfillmentV2;

