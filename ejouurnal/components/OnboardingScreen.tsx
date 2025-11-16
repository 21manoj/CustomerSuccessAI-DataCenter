import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
} from 'react-native';

interface OnboardingScreenProps {
  onComplete: () => void;
}

export const OnboardingScreen: React.FC<OnboardingScreenProps> = ({
  onComplete,
}) => {
  return (
    <View style={styles.container}>
      <ScrollView 
        style={styles.content}
        contentContainerStyle={styles.contentContainer}
        showsVerticalScrollIndicator={false}
      >
        {/* Hero Section */}
        <View style={styles.hero}>
          <Text style={styles.heroEmoji}>✨</Text>
          <Text style={styles.heroTitle}>Welcome to Fulfillment</Text>
          <Text style={styles.heroSubtitle}>
            Your AI-powered guide to a more meaningful life
          </Text>
        </View>

        {/* How It Works */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>How it works:</Text>
          
          <View style={styles.stepCard}>
            <View style={styles.stepNumber}>
              <Text style={styles.stepNumberText}>1️⃣</Text>
            </View>
            <View style={styles.stepContent}>
              <Text style={styles.stepTitle}>Set your intention</Text>
              <Text style={styles.stepDescription}>
                One meaningful shift you want to make this week
              </Text>
            </View>
          </View>

          <View style={styles.stepCard}>
            <View style={styles.stepNumber}>
              <Text style={styles.stepNumberText}>2️⃣</Text>
            </View>
            <View style={styles.stepContent}>
              <Text style={styles.stepTitle}>AI suggests micro-moves</Text>
              <Text style={styles.stepDescription}>
                Proven actions that support your intention
              </Text>
            </View>
          </View>

          <View style={styles.stepCard}>
            <View style={styles.stepNumber}>
              <Text style={styles.stepNumberText}>3️⃣</Text>
            </View>
            <View style={styles.stepContent}>
              <Text style={styles.stepTitle}>Discover your formula</Text>
              <Text style={styles.stepDescription}>
                Track check-ins → AI discovers what works for YOU
              </Text>
            </View>
          </View>
        </View>

        {/* Value Props */}
        <View style={styles.valueProps}>
          <ValueProp 
            icon="🎯"
            title="Personalized Insights"
            description="AI finds patterns in YOUR data"
          />
          <ValueProp 
            icon="📊"
            title="Track What Matters"
            description="Body, Mind, Soul, Purpose scores"
          />
          <ValueProp 
            icon="✍️"
            title="Daily AI Journal"
            description="Reflections written just for you"
          />
          <ValueProp 
            icon="🔄"
            title="The Virtuous Cycle"
            description="Intention → Action → Growth → Better Intention"
          />
        </View>

        <View style={styles.bottomSpacer} />
      </ScrollView>

      {/* CTA Button */}
      <View style={styles.footer}>
        <TouchableOpacity 
          style={styles.ctaButton}
          onPress={onComplete}
          activeOpacity={0.8}
        >
          <Text style={styles.ctaButtonText}>Start Your Journey →</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const ValueProp: React.FC<{ icon: string; title: string; description: string }> = ({
  icon,
  title,
  description,
}) => (
  <View style={styles.valueProp}>
    <Text style={styles.valuePropIcon}>{icon}</Text>
    <View style={styles.valuePropContent}>
      <Text style={styles.valuePropTitle}>{title}</Text>
      <Text style={styles.valuePropDescription}>{description}</Text>
    </View>
  </View>
);

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#8B5CF6', // V2: Purple gradient background
  },
  content: {
    flex: 1,
  },
  contentContainer: {
    paddingTop: 60,
    paddingBottom: 100,
  },
  hero: {
    alignItems: 'center',
    paddingHorizontal: 24,
    marginBottom: 40,
  },
  heroEmoji: {
    fontSize: 72,
    marginBottom: 20,
  },
  heroTitle: {
    fontSize: 34,
    fontWeight: '900',
    color: '#FFFFFF',
    textAlign: 'center',
    marginBottom: 12,
  },
  heroSubtitle: {
    fontSize: 17,
    color: '#E9D5FF',
    textAlign: 'center',
    lineHeight: 24,
    fontWeight: '500',
  },
  section: {
    paddingHorizontal: 20,
    marginBottom: 32,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: '#FFFFFF',
    marginBottom: 20,
    paddingHorizontal: 4,
  },
  stepCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    borderRadius: 20,
    padding: 20,
    marginBottom: 16,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
  },
  stepNumber: {
    marginRight: 16,
  },
  stepNumberText: {
    fontSize: 36,
  },
  stepContent: {
    flex: 1,
  },
  stepTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 6,
  },
  stepDescription: {
    fontSize: 15,
    color: '#E9D5FF',
    lineHeight: 21,
  },
  valueProps: {
    paddingHorizontal: 20,
  },
  valueProp: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 20,
    paddingHorizontal: 4,
  },
  valuePropIcon: {
    fontSize: 32,
    marginRight: 14,
  },
  valuePropContent: {
    flex: 1,
  },
  valuePropTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 4,
  },
  valuePropDescription: {
    fontSize: 15,
    color: '#E9D5FF',
    lineHeight: 21,
  },
  bottomSpacer: {
    height: 40,
  },
  footer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: 24,
    backgroundColor: '#8B5CF6',
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.2)',
  },
  ctaButton: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    paddingVertical: 18,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 4,
  },
  ctaButtonText: {
    fontSize: 18,
    fontWeight: '800',
    color: '#8B5CF6',
  },
});

