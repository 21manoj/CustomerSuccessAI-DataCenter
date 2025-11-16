import React, { useState } from 'react';
import { Heart, Brain, Zap, Target, ArrowLeft, TrendingUp, Calendar, Sun, Cloud, Moon, Sunrise, ChevronRight, Crown, Lock, Settings, User, Bell, Shield, Download, LogOut, Sparkles, Award, BarChart3, LineChart } from 'lucide-react';

const MobileMockup = () => {
  const [currentScreen, setCurrentScreen] = useState('onboarding1');
  const [selectedPart, setSelectedPart] = useState('morning');
  const [checkInStep, setCheckInStep] = useState(0);
  const [scores, setScores] = useState({});

  // Navigation Menu
  const NavigationMenu = ({ currentScreen, setCurrentScreen }) => (
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 safe-area-bottom">
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
          active={currentScreen === 'insights'}
          onClick={() => setCurrentScreen('insights')}
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
      className={`flex flex-col items-center gap-1 px-4 py-2 ${active ? 'text-purple-600' : 'text-gray-400'}`}
    >
      <Icon size={20} />
      <span className="text-xs">{label}</span>
    </button>
  );

  // ONBOARDING SCREENS
  const Onboarding1 = () => (
    <div className="h-full bg-gradient-to-br from-purple-600 via-pink-500 to-orange-400 flex flex-col items-center justify-center px-8 text-white">
      <div className="text-7xl mb-6 animate-pulse">✨</div>
      <h1 className="text-3xl font-light mb-3 text-center">Soul Journal</h1>
      <p className="text-center text-white/90 text-sm leading-relaxed mb-12">
        Track what actually matters.<br/>Not your highlight reel.
      </p>
      <button
        onClick={() => setCurrentScreen('onboarding2')}
        className="bg-white text-purple-600 px-10 py-4 rounded-full font-medium shadow-xl active:scale-95 transition-transform"
      >
        Get Started
      </button>
      <button className="mt-6 text-white/80 text-sm underline">
        Already have an account?
      </button>
    </div>
  );

  const Onboarding2 = () => (
    <div className="h-full bg-gradient-to-br from-amber-50 via-rose-50 to-purple-50 flex flex-col">
      <div className="flex-1 flex flex-col items-center justify-center px-8">
        <div className="w-20 h-20 bg-gradient-to-br from-purple-400 to-pink-400 rounded-3xl flex items-center justify-center mb-6 shadow-lg">
          <span className="text-4xl">📱</span>
        </div>
        <h2 className="text-2xl font-light text-gray-800 mb-3 text-center">All That Glitters...</h2>
        <p className="text-center text-gray-600 text-sm leading-relaxed">
          Social media shows everyone's highlight reel. You scroll through exotic vacations, perfect lives, and feel... less than.
          <br/><br/>
          <span className="font-medium">But that's not real life.</span>
        </p>
      </div>
      <div className="px-8 pb-8">
        <div className="flex gap-2 justify-center mb-6">
          <div className="w-2 h-2 rounded-full bg-gray-300"></div>
          <div className="w-2 h-2 rounded-full bg-purple-500"></div>
          <div className="w-2 h-2 rounded-full bg-gray-300"></div>
          <div className="w-2 h-2 rounded-full bg-gray-300"></div>
        </div>
        <button
          onClick={() => setCurrentScreen('onboarding3')}
          className="w-full bg-purple-600 text-white py-4 rounded-2xl font-medium active:scale-95 transition-transform"
        >
          Continue
        </button>
      </div>
    </div>
  );

  const Onboarding3 = () => (
    <div className="h-full bg-gradient-to-br from-amber-50 via-rose-50 to-purple-50 flex flex-col">
      <div className="flex-1 flex flex-col items-center justify-center px-8">
        <div className="w-20 h-20 bg-gradient-to-br from-emerald-400 to-teal-400 rounded-3xl flex items-center justify-center mb-6 shadow-lg">
          <span className="text-4xl">🌱</span>
        </div>
        <h2 className="text-2xl font-light text-gray-800 mb-3 text-center">...Is Not Gold</h2>
        <p className="text-center text-gray-600 text-sm leading-relaxed">
          Real fulfillment comes from physical vitality, mental clarity, heart fulfillment, and living with purpose.
          <br/><br/>
          <span className="font-medium">We'll help you track your truth.</span>
        </p>
      </div>
      <div className="px-8 pb-8">
        <div className="flex gap-2 justify-center mb-6">
          <div className="w-2 h-2 rounded-full bg-gray-300"></div>
          <div className="w-2 h-2 rounded-full bg-gray-300"></div>
          <div className="w-2 h-2 rounded-full bg-purple-500"></div>
          <div className="w-2 h-2 rounded-full bg-gray-300"></div>
        </div>
        <button
          onClick={() => setCurrentScreen('onboarding4')}
          className="w-full bg-purple-600 text-white py-4 rounded-2xl font-medium active:scale-95 transition-transform"
        >
          Continue
        </button>
      </div>
    </div>
  );

  const Onboarding4 = () => (
    <div className="h-full bg-gradient-to-br from-amber-50 via-rose-50 to-purple-50 flex flex-col">
      <div className="flex-1 flex flex-col items-center justify-center px-8">
        <div className="w-20 h-20 bg-gradient-to-br from-blue-400 to-indigo-400 rounded-3xl flex items-center justify-center mb-6 shadow-lg">
          <span className="text-4xl">⏰</span>
        </div>
        <h2 className="text-2xl font-light text-gray-800 mb-3 text-center">4 Quick Check-ins Daily</h2>
        <p className="text-center text-gray-600 text-sm leading-relaxed mb-6">
          Morning, Afternoon, Evening, Night.
          <br/><br/>
          Each takes 30 seconds. Rate how you feel across 4 dimensions, track what influences you, and discover your personal fulfillment formula.
        </p>
        
        <div className="grid grid-cols-2 gap-3 w-full max-w-xs">
          <div className="bg-white/60 backdrop-blur-sm rounded-2xl p-4 border border-white">
            <Zap size={24} className="text-orange-500 mb-2" />
            <p className="text-xs text-gray-700 font-medium">Physical</p>
          </div>
          <div className="bg-white/60 backdrop-blur-sm rounded-2xl p-4 border border-white">
            <Brain size={24} className="text-blue-500 mb-2" />
            <p className="text-xs text-gray-700 font-medium">Mental</p>
          </div>
          <div className="bg-white/60 backdrop-blur-sm rounded-2xl p-4 border border-white">
            <Heart size={24} className="text-pink-500 mb-2" />
            <p className="text-xs text-gray-700 font-medium">Soul</p>
          </div>
          <div className="bg-white/60 backdrop-blur-sm rounded-2xl p-4 border border-white">
            <Target size={24} className="text-purple-500 mb-2" />
            <p className="text-xs text-gray-700 font-medium">Purpose</p>
          </div>
        </div>
      </div>
      <div className="px-8 pb-8">
        <div className="flex gap-2 justify-center mb-6">
          <div className="w-2 h-2 rounded-full bg-gray-300"></div>
          <div className="w-2 h-2 rounded-full bg-gray-300"></div>
          <div className="w-2 h-2 rounded-full bg-gray-300"></div>
          <div className="w-2 h-2 rounded-full bg-purple-500"></div>
        </div>
        <button
          onClick={() => setCurrentScreen('home')}
          className="w-full bg-purple-600 text-white py-4 rounded-2xl font-medium active:scale-95 transition-transform"
        >
          Start My Journey
        </button>
      </div>
    </div>
  );

  // HOME SCREEN
  const HomeScreen = () => (
    <div className="h-full bg-gradient-to-br from-amber-50 via-rose-50 to-purple-50 overflow-y-auto pb-20">
      <div className="pt-16 pb-6 px-6 text-center">
        <div className="text-4xl mb-3">✨</div>
        <h1 className="text-2xl font-light text-gray-800 mb-1">Soul Journal</h1>
        <p className="text-xs text-gray-500">Wednesday, October 15</p>
      </div>

      <div className="px-6 space-y-3">
        <CheckInCard 
          icon={<Sunrise size={20} />}
          title="Morning"
          time="6am - 12pm"
          completed={false}
          onClick={() => {
            setSelectedPart('morning');
            setCurrentScreen('checkin');
          }}
        />
        <CheckInCard 
          icon={<Sun size={20} />}
          title="Afternoon"
          time="12pm - 6pm"
          completed={true}
        />
        <CheckInCard 
          icon={<Cloud size={20} />}
          title="Evening"
          time="6pm - 10pm"
          completed={false}
        />
        <CheckInCard 
          icon={<Moon size={20} />}
          title="Night"
          time="10pm - 12am"
          completed={false}
        />
      </div>

      <div className="px-6 pt-6">
        <div className="bg-white/60 backdrop-blur-sm rounded-2xl p-5 border border-gray-100">
          <p className="text-sm text-gray-600 italic leading-relaxed">
            "Not all those who wander are lost."
          </p>
          <p className="text-xs text-gray-400 mt-2">— J.R.R. Tolkien</p>
        </div>
      </div>

      <NavigationMenu currentScreen="home" setCurrentScreen={setCurrentScreen} />
    </div>
  );

  // CHECK-IN SCREEN (simplified for space)
  const CheckInScreen = () => {
    const dimensions = [
      { id: 'physical', icon: Zap, title: 'Physical Vitality', question: 'How does your body feel?', color: 'from-orange-400 to-amber-500', options: ['Drained', 'Tired', 'Okay', 'Energized', 'Strong'] },
      { id: 'mental', icon: Brain, title: 'Mental Clarity', question: 'How is your mind?', color: 'from-blue-400 to-indigo-500', options: ['Scattered', 'Foggy', 'Calm', 'Clear', 'Focused'] },
    ];
    const current = dimensions[0];
    const Icon = current.icon;

    return (
      <div className="h-full bg-gradient-to-br from-purple-50 via-blue-50 to-pink-50">
        <div className="pt-16 pb-4 px-6">
          <button onClick={() => setCurrentScreen('home')} className="mb-4">
            <ArrowLeft size={24} className="text-gray-600" />
          </button>
          <p className="text-xs text-gray-500 mb-3">MORNING CHECK-IN</p>
        </div>

        <div className="px-6">
          <div className="bg-white rounded-3xl p-8 shadow-xl">
            <div className={`w-16 h-16 rounded-full bg-gradient-to-br ${current.color} flex items-center justify-center mb-4`}>
              <Icon size={32} className="text-white" strokeWidth={1.5} />
            </div>
            <h2 className="text-xl font-light text-gray-800 mb-2">{current.title}</h2>
            <p className="text-sm text-gray-500 mb-6">{current.question}</p>

            <div className="space-y-2">
              {current.options.map((option, index) => (
                <button
                  key={index}
                  onClick={() => setCurrentScreen('home')}
                  className="w-full p-4 rounded-xl bg-gray-50 hover:bg-gray-100 text-left border border-gray-100"
                >
                  <span className="text-gray-700 text-sm">{option}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  };

  // PREMIUM FEATURES SCREEN
  const PremiumScreen = () => (
    <div className="h-full bg-gradient-to-br from-purple-600 via-pink-500 to-orange-400 overflow-y-auto pb-20">
      <div className="pt-16 pb-6 px-6">
        <div className="flex items-center justify-center mb-4">
          <Crown size={48} className="text-yellow-300" />
        </div>
        <h1 className="text-3xl font-light text-white text-center mb-2">Premium</h1>
        <p className="text-center text-white/90 text-sm">Unlock your full story</p>
      </div>

      <div className="px-6 space-y-4 pb-6">
        <PremiumFeatureCard
          icon={<Sparkles size={24} />}
          title="Fulfillment Formula"
          description="Discover what activities truly bring you joy vs. what just glitters"
          onClick={() => setCurrentScreen('premium-formula')}
        />
        <PremiumFeatureCard
          icon={<BarChart3 size={24} />}
          title="Glitter vs Gold Report"
          description="See which activities provide lasting fulfillment vs quick dopamine hits"
          onClick={() => setCurrentScreen('premium-report')}
        />
        <PremiumFeatureCard
          icon={<LineChart size={24} />}
          title="Social Media Impact"
          description="Track how social media affects your mental clarity and purpose"
          onClick={() => setCurrentScreen('premium-social')}
        />
        <PremiumFeatureCard
          icon={<Award size={24} />}
          title="Challenges & Streaks"
          description="7-day detox challenges with before/after comparisons"
        />
        <PremiumFeatureCard
          icon={<TrendingUp size={24} />}
          title="Lineage View"
          description="See how physical vitality leads to mental clarity and purposeful living"
        />
        <PremiumFeatureCard
          icon={<Download size={24} />}
          title="Export Your Data"
          description="Own your journey. Download all your insights and reflections"
        />

        <div className="bg-white rounded-3xl p-6 shadow-xl mt-8">
          <div className="text-center mb-4">
            <p className="text-2xl font-bold text-gray-800 mb-1">$4.99/month</p>
            <p className="text-sm text-gray-500">7-day free trial</p>
          </div>
          <button className="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white py-4 rounded-2xl font-medium shadow-lg active:scale-95 transition-transform mb-3">
            Start Free Trial
          </button>
          <p className="text-xs text-gray-500 text-center">Cancel anytime. No commitments.</p>
        </div>
      </div>

      <NavigationMenu currentScreen="premium" setCurrentScreen={setCurrentScreen} />
    </div>
  );

  // PREMIUM FEATURE DETAIL: FULFILLMENT FORMULA
  const PremiumFormulaScreen = () => (
    <div className="h-full bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 overflow-y-auto">
      <div className="pt-16 pb-4 px-6">
        <button onClick={() => setCurrentScreen('premium')} className="mb-4">
          <ArrowLeft size={24} className="text-gray-600" />
        </button>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 bg-gradient-to-br from-purple-400 to-pink-400 rounded-2xl flex items-center justify-center">
            <Sparkles size={24} className="text-white" />
          </div>
          <h1 className="text-2xl font-light text-gray-800">Your Formula</h1>
        </div>
        <p className="text-sm text-gray-600">Based on 28 days of data</p>
      </div>

      <div className="px-6 space-y-4 pb-6">
        <div className="bg-white rounded-3xl p-6 shadow-lg">
          <h3 className="text-sm font-semibold text-emerald-600 mb-3">✨ YOUR GOLD MOMENTS</h3>
          <p className="text-gray-700 leading-relaxed mb-4">
            You feel most alive when you're <span className="font-semibold">creating</span>, <span className="font-semibold">exercising</span>, or having <span className="font-semibold">deep conversations</span>. Your purpose score jumps <span className="font-semibold text-emerald-600">+2.3 points</span> on these days.
          </p>
          <div className="space-y-2">
            <InsightBar label="🎨 Creating" impact="+2.4" color="bg-emerald-400" width="95%" />
            <InsightBar label="🏃 Exercise" impact="+2.1" color="bg-emerald-400" width="85%" />
            <InsightBar label="💬 Deep Talk" impact="+1.8" color="bg-emerald-400" width="72%" />
          </div>
        </div>

        <div className="bg-white rounded-3xl p-6 shadow-lg">
          <h3 className="text-sm font-semibold text-red-600 mb-3">⚠️ GLITTER ALERTS</h3>
          <p className="text-gray-700 leading-relaxed mb-4">
            <span className="font-semibold">Social media</span> and <span className="font-semibold">shopping</span> give you a quick boost (+0.8) but your mental clarity drops by <span className="font-semibold text-red-600">-1.5</span> in the next check-in.
          </p>
          <div className="bg-red-50 border border-red-200 rounded-xl p-4">
            <p className="text-sm text-red-800">
              💭 <span className="font-medium">Consider:</span> Is the scroll worth the scatter?
            </p>
          </div>
        </div>

        <div className="bg-gradient-to-br from-purple-600 to-pink-600 rounded-3xl p-6 shadow-xl text-white">
          <h3 className="text-sm font-semibold mb-3">📊 YOUR LINEAGE</h3>
          <div className="space-y-3">
            <p className="text-sm">Physical strength days → <span className="font-semibold">+40%</span> better mental clarity</p>
            <p className="text-sm">Mental clarity → <span className="font-semibold">+60%</span> more purposeful living</p>
            <p className="text-sm">Days with purpose → <span className="font-semibold">+35%</span> soul fulfillment next morning</p>
          </div>
        </div>

        <div className="bg-white rounded-3xl p-6 shadow-lg">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">💡 THIS WEEK'S INSIGHT</h3>
          <p className="text-gray-700 leading-relaxed">
            You scored highest (18.5/20) on Tuesday morning after Monday's evening nature walk. You scored lowest (9/20) on Thursday after heavy Wednesday social media use.
          </p>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-3xl p-6">
          <h3 className="text-sm font-semibold text-blue-800 mb-2">🎯 RECOMMENDATION</h3>
          <p className="text-sm text-blue-700 leading-relaxed">
            Try this: One full day without social media this week. Based on your patterns, you might gain +3 points in mental clarity and +2 in purpose.
          </p>
        </div>
      </div>
    </div>
  );

  // PREMIUM FEATURE: SOCIAL MEDIA IMPACT
  const PremiumSocialScreen = () => (
    <div className="h-full bg-gradient-to-br from-red-50 via-orange-50 to-amber-50 overflow-y-auto">
      <div className="pt-16 pb-4 px-6">
        <button onClick={() => setCurrentScreen('premium')} className="mb-4">
          <ArrowLeft size={24} className="text-gray-600" />
        </button>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 bg-gradient-to-br from-red-400 to-orange-400 rounded-2xl flex items-center justify-center">
            <span className="text-2xl">📱</span>
          </div>
          <h1 className="text-2xl font-light text-gray-800">Social Media Impact</h1>
        </div>
        <p className="text-sm text-gray-600">Your relationship with the scroll</p>
      </div>

      <div className="px-6 space-y-4 pb-6">
        <div className="bg-white rounded-3xl p-6 shadow-lg">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">The Truth</h3>
          <div className="bg-gradient-to-r from-red-500 to-orange-500 text-white rounded-2xl p-5 mb-4">
            <p className="text-3xl font-bold mb-1">-2.8 points</p>
            <p className="text-sm opacity-90">Your average score drops on social media days</p>
          </div>
          <p className="text-sm text-gray-600 leading-relaxed">
            You score <span className="font-semibold">2.8 points lower</span> (out of 20) on days when you use social media, compare yourself to others, or scroll mindlessly.
          </p>
        </div>

        <div className="bg-white rounded-3xl p-6 shadow-lg">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">WHAT'S AFFECTED MOST</h3>
          <div className="space-y-3">
            <ImpactRow icon={Brain} label="Mental Clarity" impact="-1.8" severity="high" />
            <ImpactRow icon={Target} label="Purpose" impact="-1.4" severity="high" />
            <ImpactRow icon={Heart} label="Soul" impact="-0.9" severity="medium" />
            <ImpactRow icon={Zap} label="Physical" impact="-0.4" severity="low" />
          </div>
        </div>

        <div className="bg-white rounded-3xl p-6 shadow-lg">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">📅 WEEKLY COMPARISON</h3>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="bg-emerald-50 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-emerald-600 mb-1">16.2</p>
              <p className="text-xs text-gray-600">Days without<br/>social media</p>
            </div>
            <div className="bg-red-50 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-red-600 mb-1">13.4</p>
              <p className="text-xs text-gray-600">Days with<br/>social media</p>
            </div>
          </div>
          <p className="text-xs text-gray-500 text-center">Out of 20 points maximum</p>
        </div>

        <div className="bg-gradient-to-br from-orange-600 to-red-600 rounded-3xl p-6 text-white shadow-xl">
          <h3 className="font-semibold mb-3">💪 Try a Challenge</h3>
          <p className="text-sm opacity-90 mb-4">
            Based on your data, a 7-day social media detox could boost your scores significantly.
          </p>
          <button className="w-full bg-white text-orange-600 py-3 rounded-xl font-medium active:scale-95 transition-transform">
            Start 7-Day Detox Challenge
          </button>
        </div>
      </div>
    </div>
  );

  // GLITTER VS GOLD REPORT
  const PremiumReportScreen = () => (
    <div className="h-full bg-gradient-to-br from-amber-50 via-yellow-50 to-orange-50 overflow-y-auto">
      <div className="pt-16 pb-4 px-6">
        <button onClick={() => setCurrentScreen('premium')} className="mb-4">
          <ArrowLeft size={24} className="text-gray-600" />
        </button>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 bg-gradient-to-br from-yellow-400 to-orange-400 rounded-2xl flex items-center justify-center">
            <BarChart3 size={24} className="text-white" />
          </div>
          <h1 className="text-2xl font-light text-gray-800">Glitter vs Gold</h1>
        </div>
        <p className="text-sm text-gray-600">Weekly analysis • Oct 8-15</p>
      </div>

      <div className="px-6 space-y-4 pb-6">
        <div className="bg-white rounded-3xl p-6 shadow-lg">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-700">BEST vs WORST DAY</h3>
          </div>
          <div className="space-y-3">
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-emerald-800">Tuesday Morning</span>
                <span className="text-lg font-bold text-emerald-600">18.5</span>
              </div>
              <p className="text-xs text-emerald-700">After Monday evening nature walk + exercise</p>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-xl p-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-red-800">Thursday Afternoon</span>
                <span className="text-lg font-bold text-red-600">9.0</span>
              </div>
              <p className="text-xs text-red-700">After heavy Wednesday social media use</p>
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-yellow-400 to-orange-400 rounded-3xl p-6 text-white shadow-xl">
          <h3 className="font-semibold mb-3">✨ THE GLITTER</h3>
          <p className="text-sm opacity-95 mb-4">
            Activities that feel good in the moment but leave you feeling worse later:
          </p>
          <div className="space-y-2">
            <GlitterItem emoji="📱" label="Social Media" immediate="+0.8" delayed="-1.5" />
            <GlitterItem emoji="🛍️" label="Shopping" immediate="+0.6" delayed="-1.2" />
            <GlitterItem emoji="😔" label="Comparing" immediate="+0.3" delayed="-1.8" />
          </div>
        </div>

        <div className="bg-gradient-to-br from-emerald-500 to-teal-500 rounded-3xl p-6 text-white shadow-xl">
          <h3 className="font-semibold mb-3">🏆 THE GOLD</h3>
          <p className="text-sm opacity-95 mb-4">
            Activities that provide lasting fulfillment:
          </p>
          <div className="space-y-2">
            <GoldItem emoji="🎨" label="Creating" score="+2.4" sustained="✓" />
            <GoldItem emoji="🏃" label="Exercise" score="+2.1" sustained="✓" />
            <GoldItem emoji="🌳" label="Nature" score="+1.9" sustained="✓" />
          </div>
        </div>

        <div className="bg-white rounded-3xl p-6 shadow-lg">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">📈 CONSISTENCY SCORE</h3>
          <div className="flex items-center justify-between mb-2">
            <span className="text-3xl font-bold text-purple-600">82%</span>
            <span className="text-sm text-gray-600">23/28 check-ins</span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-purple-400 to-pink-400 rounded-full" style={{width: '82%'}}></div>
          </div>
          <p className="text-xs text-gray-500 mt-2">Great job staying consistent!</p>
        </div>
      </div>
    </div>
  );

  // PROFILE/SETTINGS SCREEN
  const ProfileScreen = () => (
    <div className="h-full bg-gradient-to-br from-gray-50 to-gray-100 overflow-y-auto pb-20">
      <div className="pt-16 pb-6 px-6">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-20 h-20 bg-gradient-to-br from-purple-400 to-pink-400 rounded-full flex items-center justify-center text-white text-2xl font-bold">
            JD
          </div>
          <div>
            <h2 className="text-xl font-medium text-gray-800">Jane Doe</h2>
            <p className="text-sm text-gray-500">jane@example.com</p>
            <div className="flex items-center gap-2 mt-1">
              <Crown size={14} className="text-yellow-500" />
              <span className="text-xs text-purple-600 font-medium">Premium Member</span>
            </div>
          </div>
        </div>

        <div className="bg-purple-50 border border-purple-200 rounded-2xl p-4 mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-purple-800">🔥 Current Streak</span>
            <span className="text-2xl font-bold text-purple-600">23 days</span>
          </div>
          <p className="text-xs text-purple-600">Keep going! You're building a powerful habit.</p>
        </div>
      </div>

      <div className="px-6 space-y-2">
        <SettingsItem icon={User} label="Edit Profile" onClick={() => {}} />
        <SettingsItem icon={Bell} label="Notifications" badge="4x daily" onClick={() => {}} />
        <SettingsItem icon={Crown} label="Manage Subscription" onClick={() => setCurrentScreen('premium')} />
        <SettingsItem icon={Download} label="Export Data" onClick={() => {}} />
        <SettingsItem icon={Shield} label="Privacy & Security" onClick={() => {}} />
        <SettingsItem icon={Settings} label="App Settings" onClick={() => {}} />
      </div>

      <div className="px-6 mt-6 space-y-3">
        <button className="w-full text-left px-4 py-3 text-sm text-gray-600">
          About Soul Journal
        </button>
        <button className="w-full text-left px-4 py-3 text-sm text-gray-600">
          Terms & Privacy
        </button>
        <button className="w-full text-left px-4 py-3 text-sm text-gray-600">
          Help & Support
        </button>
        <button className="w-full text-left px-4 py-4 text-sm text-red-600 flex items-center gap-2">
          <LogOut size={18} />
          Log Out
        </button>
      </div>

      <div className="px-6 py-6 text-center">
        <p className="text-xs text-gray-400">Version 1.0.0</p>
      </div>

      <NavigationMenu currentScreen="profile" setCurrentScreen={setCurrentScreen} />
    </div>
  );

  // Render Current Screen
  const renderScreen = () => {
    switch(currentScreen) {
      case 'onboarding1': return <Onboarding1 />;
      case 'onboarding2': return <Onboarding2 />;
      case 'onboarding3': return <Onboarding3 />;
      case 'onboarding4': return <Onboarding4 />;
      case 'home': return <HomeScreen />;
      case 'checkin': return <CheckInScreen />;
      case 'premium': return <PremiumScreen />;
      case 'premium-formula': return <PremiumFormulaScreen />;
      case 'premium-social': return <PremiumSocialScreen />;
      case 'premium-report': return <PremiumReportScreen />;
      case 'profile': return <ProfileScreen />;
      default: return <HomeScreen />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4 md:p-8">
      <div className="relative">
        <div className="w-[375px] h-[812px] bg-black rounded-[50px] shadow-2xl relative overflow-hidden border-8 border-gray-800">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-40 h-7 bg-black rounded-b-3xl z-50"></div>
          <div className="absolute top-0 left-0 right-0 h-11 z-40 px-8 flex items-center justify-between text-xs font-medium">
            <span className="text-gray-800">9:41</span>
            <div className="flex items-center gap-1">
              <div className="w-4 h-3 border border-gray-800 rounded-sm"></div>
              <div className="w-1 h-2 bg-gray-800 rounded-sm"></div>
            </div>
          </div>
          <div className="w-full h-full">{renderScreen()}</div>
          <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-32 h-1 bg-gray-800 rounded-full"></div>
        </div>
        <div className="absolute -bottom-12 left-0 right-0 text-center text-white text-sm">
          {currentScreen.includes('onboarding') && 'Onboarding'}
          {currentScreen === 'home' && 'Home'}
          {currentScreen === 'premium' && 'Premium Features'}
          {currentScreen === 'premium-formula' && 'Fulfillment Formula'}
          {currentScreen === 'premium-social' && 'Social Media Impact'}
          {currentScreen === 'premium-report' && 'Glitter vs Gold Report'}
          {currentScreen === 'profile' && 'Profile & Settings'}
        </div>
      </div>
    </div>
  );
};

// Helper Components
const CheckInCard = ({ icon, title, time, completed, onClick }) => (
  <button onClick={onClick} className={`w-full p-4 rounded-2xl text-left transition-all active:scale-95 ${completed ? 'bg-emerald-100/80 backdrop-blur-sm border-2 border-emerald-300' : 'bg-white/60 backdrop-blur-sm border-2 border-white/50 shadow-sm'}`}>
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${completed ? 'bg-emerald-200' : 'bg-purple-100'}`}>
          {completed ? <span className="text-lg">✓</span> : icon}
        </div>
        <div>
          <div className="font-medium text-gray-800 text-sm">{title}</div>
          <div className="text-xs text-gray-500">{time}</div>
        </div>
      </div>
      {!completed && <div className="text-purple-400">→</div>}
    </div>
  </button>
);

const PremiumFeatureCard = ({ icon, title, description, onClick }) => (
  <button onClick={onClick} className="w-full bg-white/90 backdrop-blur-sm rounded-2xl p-5 text-left shadow-lg active:scale-95 transition-transform">
    <div className="flex items-start gap-4">
      <div className="w-12 h-12 bg-gradient-to-br from-purple-100 to-pink-100 rounded-2xl flex items-center justify-center text-purple-600 flex-shrink-0">
        {icon}
      </div>
      <div className="flex-1">
        <h3 className="font-medium text-gray-800 mb-1">{title}</h3>
        <p className="text-sm text-gray-600 leading-relaxed">{description}</p>
      </div>
      <ChevronRight size={20} className="text-gray-400 flex-shrink-0" />
    </div>
  </button>
);

const InsightBar = ({ label, impact, color, width }) => (
  <div>
    <div className="flex justify-between items-center mb-1">
      <span className="text-sm text-gray-700">{label}</span>
      <span className="text-sm font-semibold text-emerald-600">{impact}</span>
    </div>
    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
      <div className={`h-full ${color} rounded-full`} style={{width}}></div>
    </div>
  </div>
);

const ImpactRow = ({ icon: Icon, label, impact, severity }) => (
  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
    <div className="flex items-center gap-3">
      <Icon size={18} className="text-gray-600" />
      <span className="text-sm text-gray-700">{label}</span>
    </div>
    <span className={`text-sm font-semibold ${severity === 'high' ? 'text-red-600' : severity === 'medium' ? 'text-orange-600' : 'text-yellow-600'}`}>
      {impact}
    </span>
  </div>
);

const GlitterItem = ({ emoji, label, immediate, delayed }) => (
  <div className="bg-white/20 backdrop-blur-sm rounded-xl p-3">
    <div className="flex items-center justify-between mb-1">
      <span className="text-sm font-medium">{emoji} {label}</span>
    </div>
    <div className="flex gap-4 text-xs">
      <span>Now: <span className="font-semibold">{immediate}</span></span>
      <span>Later: <span className="font-semibold">{delayed}</span></span>
    </div>
  </div>
);

const GoldItem = ({ emoji, label, score, sustained }) => (
  <div className="bg-white/20 backdrop-blur-sm rounded-xl p-3">
    <div className="flex items-center justify-between">
      <span className="text-sm font-medium">{emoji} {label}</span>
      <span className="text-sm font-semibold">{score} {sustained}</span>
    </div>
  </div>
);

const SettingsItem = ({ icon: Icon, label, badge, onClick }) => (
  <button onClick={onClick} className="w-full bg-white rounded-2xl p-4 flex items-center justify-between active:bg-gray-50 transition-colors">
    <div className="flex items-center gap-3">
      <Icon size={20} className="text-gray-600" />
      <span className="text-sm text-gray-800">{label}</span>
    </div>
    <div className="flex items-center gap-2">
      {badge && <span className="text-xs text-gray-500">{badge}</span>}
      <ChevronRight size={18} className="text-gray-400" />
    </div>
  </button>
);

export default MobileMockup;