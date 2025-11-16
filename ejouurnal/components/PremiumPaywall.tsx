import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
} from 'react-native';

interface PremiumPaywallProps {
  trigger: 'journal-limit' | 'mdw-achieved' | 'insight-clicked' | 'add-details';
  onUpgrade: (plan: 'monthly' | 'yearly') => void;
  onClose: () => void;
  showCloseButton?: boolean;
}

const PREMIUM_FEATURES = [
  {
    icon: '✨',
    title: 'Unlimited AI Journals',
    description: 'Daily reflections in 4 tones',
    highlight: true
  },
  {
    icon: '🔗',
    title: 'Deep Lineage Analysis',
    description: 'Lag correlations & breakpoint detection'
  },
  {
    icon: '📊',
    title: 'Add Details',
    description: 'Track sleep, food, exercise & social'
  },
  {
    icon: '🎯',
    title: 'Purpose Programs',
    description: 'Guided 4-week tracks for calm, strength & more'
  },
  {
    icon: '👨‍⚕️',
    title: 'Coach Summaries',
    description: 'Weekly PDF for you or your therapist'
  },
  {
    icon: '⚙️',
    title: 'Focus Toolkit',
    description: 'App blocking & custom rituals'
  },
  {
    icon: '☁️',
    title: 'Cloud Backup',
    description: 'End-to-end encrypted sync'
  },
  {
    icon: '📥',
    title: 'Data Export',
    description: 'Own your data - export anytime'
  }
];

export const PremiumPaywall: React.FC<PremiumPaywallProps> = ({
  trigger,
  onUpgrade,
  onClose,
  showCloseButton = true
}) => {
  const getTriggerMessage = () => {
    switch (trigger) {
      case 'journal-limit':
        return {
          title: "You've used your 3 free journals",
          subtitle: 'Unlock unlimited AI-generated reflections'
        };
      case 'mdw-achieved':
        return {
          title: "You had 3 Meaningful Days this week! 🎉",
          subtitle: 'Unlock deeper insights to reach 5+ MDW'
        };
      case 'insight-clicked':
        return {
          title: "You've discovered your patterns",
          subtitle: 'Unlock all insights & personalized programs'
        };
      case 'add-details':
        return {
          title: 'Track the full picture',
          subtitle: 'Add sleep, food, exercise & social details'
        };
    }
  };

  const message = getTriggerMessage();

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        {showCloseButton && (
          <TouchableOpacity onPress={onClose} style={styles.closeButton}>
            <Text style={styles.closeText}>✕</Text>
          </TouchableOpacity>
        )}
      </View>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Hero */}
        <View style={styles.hero}>
          <Text style={styles.crown}>👑</Text>
          <Text style={styles.title}>{message.title}</Text>
          <Text style={styles.subtitle}>{message.subtitle}</Text>
        </View>

        {/* Features */}
        <View style={styles.features}>
          {PREMIUM_FEATURES.map((feature, index) => (
            <View
              key={index}
              style={[
                styles.featureCard,
                feature.highlight && styles.featureCardHighlight
              ]}
            >
              <Text style={styles.featureIcon}>{feature.icon}</Text>
              <View style={styles.featureContent}>
                <Text style={styles.featureTitle}>{feature.title}</Text>
                <Text style={styles.featureDescription}>{feature.description}</Text>
              </View>
            </View>
          ))}
        </View>

        {/* Pricing */}
        <View style={styles.pricing}>
          {/* Yearly Plan (Recommended) */}
          <TouchableOpacity
            style={[styles.pricingCard, styles.pricingCardRecommended]}
            onPress={() => onUpgrade('yearly')}
            activeOpacity={0.8}
          >
            <View style={styles.recommendedBadge}>
              <Text style={styles.recommendedText}>BEST VALUE</Text>
            </View>
            <Text style={styles.pricingLabel}>Yearly</Text>
            <View style={styles.pricingPrice}>
              <Text style={styles.pricingAmount}>$49.99</Text>
              <Text style={styles.pricingPeriod}>/year</Text>
            </View>
            <Text style={styles.pricingSavings}>Save 48% • Just $4.16/month</Text>
          </TouchableOpacity>

          {/* Monthly Plan */}
          <TouchableOpacity
            style={styles.pricingCard}
            onPress={() => onUpgrade('monthly')}
            activeOpacity={0.8}
          >
            <Text style={styles.pricingLabel}>Monthly</Text>
            <View style={styles.pricingPrice}>
              <Text style={styles.pricingAmount}>$7.99</Text>
              <Text style={styles.pricingPeriod}>/month</Text>
            </View>
            <Text style={styles.pricingNote}>Cancel anytime</Text>
          </TouchableOpacity>
        </View>

        {/* Trust Signals */}
        <View style={styles.trustSignals}>
          <TrustItem icon="✓" text="7-day free trial" />
          <TrustItem icon="✓" text="Cancel anytime, no commitments" />
          <TrustItem icon="✓" text="Your data stays encrypted" />
        </View>

        {/* Social Proof */}
        <View style={styles.socialProof}>
          <Text style={styles.socialProofQuote}>
            "This app showed me I score 18 points lower on high-scroll days. Changed my life. Worth every penny."
          </Text>
          <Text style={styles.socialProofAuthor}>— Sarah, Premium Member</Text>
        </View>

        <View style={styles.bottomPadding} />
      </ScrollView>
    </View>
  );
};

const TrustItem: React.FC<{ icon: string; text: string }> = ({ icon, text }) => (
  <View style={styles.trustItem}>
    <Text style={styles.trustIcon}>{icon}</Text>
    <Text style={styles.trustText}>{text}</Text>
  </View>
);

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FAFBFC',
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 20,
    alignItems: 'flex-end',
  },
  closeButton: {
    width: 32,
    height: 32,
    justifyContent: 'center',
    alignItems: 'center',
  },
  closeText: {
    fontSize: 24,
    color: '#666',
  },
  content: {
    flex: 1,
  },
  hero: {
    alignItems: 'center',
    paddingHorizontal: 32,
    paddingBottom: 32,
  },
  crown: {
    fontSize: 56,
    marginBottom: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#1A1A1A',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 15,
    color: '#666',
    textAlign: 'center',
    lineHeight: 22,
  },
  features: {
    paddingHorizontal: 16,
    gap: 10,
    marginBottom: 32,
  },
  featureCard: {
    flexDirection: 'row',
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    gap: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 1,
  },
  featureCardHighlight: {
    backgroundColor: '#F5F8FF',
    borderWidth: 2,
    borderColor: '#007AFF',
  },
  featureIcon: {
    fontSize: 32,
  },
  featureContent: {
    flex: 1,
  },
  featureTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#1A1A1A',
    marginBottom: 2,
  },
  featureDescription: {
    fontSize: 13,
    color: '#666',
    lineHeight: 18,
  },
  pricing: {
    paddingHorizontal: 16,
    gap: 12,
    marginBottom: 24,
  },
  pricingCard: {
    backgroundColor: '#FFF',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#E8E8E8',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 3,
  },
  pricingCardRecommended: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  recommendedBadge: {
    position: 'absolute',
    top: -12,
    backgroundColor: '#FFD93D',
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 20,
  },
  recommendedText: {
    fontSize: 11,
    fontWeight: '800',
    color: '#1A1A1A',
    letterSpacing: 0.5,
  },
  pricingLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
    marginBottom: 8,
  },
  pricingPrice: {
    flexDirection: 'row',
    alignItems: 'baseline',
    marginBottom: 8,
  },
  pricingAmount: {
    fontSize: 40,
    fontWeight: '800',
    color: '#1A1A1A',
  },
  pricingPeriod: {
    fontSize: 16,
    color: '#666',
    marginLeft: 4,
  },
  pricingSavings: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FFF',
  },
  pricingNote: {
    fontSize: 13,
    color: '#999',
  },
  trustSignals: {
    paddingHorizontal: 32,
    marginBottom: 24,
    gap: 12,
  },
  trustItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  trustIcon: {
    fontSize: 16,
    color: '#34C759',
  },
  trustText: {
    fontSize: 14,
    color: '#666',
  },
  socialProof: {
    marginHorizontal: 16,
    backgroundColor: '#F5F8FF',
    borderRadius: 16,
    padding: 20,
    marginBottom: 20,
  },
  socialProofQuote: {
    fontSize: 14,
    fontStyle: 'italic',
    color: '#333',
    lineHeight: 22,
    marginBottom: 8,
  },
  socialProofAuthor: {
    fontSize: 12,
    color: '#007AFF',
    fontWeight: '600',
  },
  bottomPadding: {
    height: 40,
  },
});

// Update pricing card selected state in the recommended card
const pricingCardRecommendedStyle = StyleSheet.create({
  pricingLabel: {
    color: '#FFF',
  },
  pricingPrice: {
    color: '#FFF',
  },
  pricingAmount: {
    color: '#FFF',
  },
  pricingPeriod: {
    color: 'rgba(255,255,255,0.8)',
  },
});

