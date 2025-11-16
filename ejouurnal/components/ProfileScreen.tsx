import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  Switch,
  Linking,
  Platform,
} from 'react-native';

type JournalTone = 'reflective' | 'factual' | 'coach-like' | 'poetic';

interface ProfileScreenProps {
  onBack: () => void;
  userName: string;
  userEmail: string;
  isPremium: boolean;
  currentStreak: number;
  totalCheckIns: number;
  joinDate: Date;
  currentTone: JournalTone;
  notificationsEnabled: boolean;
  onEditProfile: () => void;
  onManagePremium: () => void;
  onGenerateJournal: () => void;
  onViewJournalHistory: () => void;
  onToneChange: (tone: JournalTone) => void;
  onToggleNotifications: (enabled: boolean) => void;
  onExportData: () => void;
  onLogout: () => void;
  onAppSettings?: () => void;
  onViewDemo?: () => void;
}

export const ProfileScreen: React.FC<ProfileScreenProps> = ({
  onBack,
  userName,
  userEmail,
  isPremium,
  currentStreak,
  totalCheckIns,
  joinDate,
  currentTone,
  notificationsEnabled,
  onEditProfile,
  onManagePremium,
  onGenerateJournal,
  onViewJournalHistory,
  onToneChange,
  onToggleNotifications,
  onExportData,
  onLogout,
  onAppSettings,
  onViewDemo,
}) => {
  const [showToneSelector, setShowToneSelector] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showPrivacy, setShowPrivacy] = useState(false);

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const handleExport = () => {
    Alert.alert(
      'Export Data',
      'Choose export format:',
      [
        { text: 'PDF (Journals)', onPress: () => onExportData() },
        { text: 'CSV (Check-ins)', onPress: () => onExportData() },
        { text: 'JSON (All Data)', onPress: () => onExportData() },
        { text: 'Cancel', style: 'cancel' },
      ]
    );
  };

  const handleHelp = () => {
    if (Platform.OS === 'web') {
      // Web: Direct action
      if (onViewDemo) {
        onViewDemo();
      } else {
        window.alert('Demo mode coming soon!');
      }
    } else {
      // Native: Show action sheet
      Alert.alert(
        'Help & Support',
        'How can we help?',
        [
          { text: '🎬 View AI Guidance Demo', onPress: onViewDemo },
          { text: 'FAQs', onPress: () => Linking.openURL('https://example.com/faq') },
          { text: 'Contact Support', onPress: () => Linking.openURL('mailto:support@fulfillment.app') },
          { text: 'Tutorial', onPress: () => Alert.alert('Tutorial', 'Tutorial coming soon!') },
          { text: 'Cancel', style: 'cancel' },
        ]
      );
    }
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack}>
          <Text style={styles.backButton}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Profile</Text>
        <View style={styles.spacer} />
      </View>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* User Info Card */}
        <View style={styles.userCard}>
          <View style={styles.avatarContainer}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>{getInitials(userName)}</Text>
            </View>
            {isPremium && (
              <View style={styles.premiumBadge}>
                <Text style={styles.premiumIcon}>💎</Text>
              </View>
            )}
          </View>
          
          <Text style={styles.userName}>{userName}</Text>
          <Text style={styles.userEmail}>{userEmail}</Text>
          
          <View style={styles.statsRow}>
            <StatBox label="Check-ins" value={totalCheckIns.toString()} />
            <StatBox label="Streak" value={`${currentStreak}d`} />
            <StatBox 
              label="Member" 
              value={`${Math.floor((Date.now() - joinDate.getTime()) / (1000 * 60 * 60 * 24))}d`} 
            />
          </View>
        </View>

        {/* Menu Items */}
        <View style={styles.menuSection}>
          {/* Edit Profile */}
          <MenuItem
            icon="👤"
            title="Edit Profile"
            subtitle="Update name, email, photo"
            onPress={onEditProfile}
          />

          {/* Notifications */}
          <MenuItem
            icon="🔔"
            title="Notifications"
            subtitle={notificationsEnabled ? '4x daily reminders' : 'Off'}
            onPress={() => setShowNotifications(!showNotifications)}
          />

          {showNotifications && (
            <View style={styles.expandedSection}>
              <View style={styles.settingRow}>
                <Text style={styles.settingLabel}>Daily Reminders</Text>
                <Switch
                  value={notificationsEnabled}
                  onValueChange={onToggleNotifications}
                  trackColor={{ false: '#E0E0E0', true: '#34C759' }}
                />
              </View>
              
              {notificationsEnabled && (
                <>
                  <NotificationTime emoji="🌅" label="Morning" time="8:00 AM" />
                  <NotificationTime emoji="☀️" label="Day" time="1:00 PM" />
                  <NotificationTime emoji="🌆" label="Evening" time="6:00 PM" />
                  <NotificationTime emoji="🌙" label="Night" time="9:00 PM" />
                  
                  <Text style={styles.hintText}>
                    ℹ️ Tap times to customize (coming soon)
                  </Text>
                </>
              )}
            </View>
          )}

          {/* Journal Tone */}
          <MenuItem
            icon="🎨"
            title="Journal Tone"
            subtitle={currentTone.charAt(0).toUpperCase() + currentTone.slice(1).replace('-', ' ')}
            onPress={() => setShowToneSelector(!showToneSelector)}
          />

          {showToneSelector && (
            <View style={styles.expandedSection}>
              <ToneOption 
                label="Reflective" 
                description="Personal & encouraging"
                selected={currentTone === 'reflective'}
                onPress={() => onToneChange('reflective')}
              />
              <ToneOption 
                label="Coach-Like" 
                description="Motivational & action-oriented"
                selected={currentTone === 'coach-like'}
                onPress={() => onToneChange('coach-like')}
              />
              <ToneOption 
                label="Poetic" 
                description="Literary & contemplative"
                selected={currentTone === 'poetic'}
                onPress={() => onToneChange('poetic')}
              />
              <ToneOption 
                label="Factual" 
                description="Data-focused & clinical"
                selected={currentTone === 'factual'}
                onPress={() => onToneChange('factual')}
              />
            </View>
          )}

          {/* App Settings */}
          <MenuItem
            icon="⚙️"
            title="App Settings"
            subtitle="Theme, language, data sync"
            onPress={onAppSettings || (() => Alert.alert('App Settings', 'Dark mode, language preferences, and sync options coming soon!'))}
          />

          {/* Manage Premium */}
          <MenuItem
            icon="💎"
            title="Manage Premium"
            subtitle={isPremium ? 'Active subscription' : 'Upgrade to unlock'}
            badge={!isPremium ? 'Upgrade' : undefined}
            onPress={onManagePremium}
          />

          {/* Generate Journal */}
          <MenuItem
            icon="✍️"
            title="Generate Today's Journal"
            subtitle="AI reflection of your day"
            onPress={onGenerateJournal}
          />

          {/* Journal History */}
          <MenuItem
            icon="📔"
            title="Journal History"
            subtitle="View past journals"
            onPress={onViewJournalHistory}
          />

          {/* Export Data */}
          <MenuItem
            icon="📊"
            title="Export Data"
            subtitle="PDF, CSV, or JSON"
            onPress={handleExport}
          />

          {/* Privacy & Security */}
          <MenuItem
            icon="🔒"
            title="Privacy & Security"
            subtitle="Data protection & encryption"
            onPress={() => setShowPrivacy(!showPrivacy)}
          />

          {showPrivacy && (
            <View style={styles.expandedSection}>
              <View style={styles.privacyCard}>
                <Text style={styles.privacyTitle}>🔒 Your Data is Safe</Text>
                <Text style={styles.privacyText}>
                  • End-to-end encryption{'\n'}
                  • Zero-knowledge architecture{'\n'}
                  • Even we can't read your journals{'\n'}
                  • Stored locally on your device{'\n'}
                  • Cloud backup: encrypted in transit & at rest{'\n'}
                  • GDPR & CCPA compliant
                </Text>
              </View>
              
              <TouchableOpacity 
                style={styles.linkButton}
                onPress={() => Linking.openURL('https://example.com/privacy')}
              >
                <Text style={styles.linkButtonText}>Read Full Privacy Policy →</Text>
              </TouchableOpacity>
            </View>
          )}

          {/* Help & Support */}
          <MenuItem
            icon="❓"
            title="Help & Support"
            subtitle={Platform.OS === 'web' ? 'Click to view AI guidance demo' : 'FAQs, demo, contact, tutorial'}
            onPress={handleHelp}
          />
        </View>

        {/* Danger Zone */}
        <View style={styles.dangerSection}>
          <TouchableOpacity 
            style={styles.logoutButton}
            onPress={() => {
              Alert.alert(
                'Log Out',
                'Are you sure you want to log out?',
                [
                  { text: 'Cancel', style: 'cancel' },
                  { text: 'Log Out', style: 'destructive', onPress: onLogout },
                ]
              );
            }}
          >
            <Text style={styles.logoutText}>Log Out</Text>
          </TouchableOpacity>
          
          <TouchableOpacity 
            style={styles.deleteButton}
            onPress={() => {
              Alert.alert(
                'Delete Account',
                'This will permanently delete all your data. This action cannot be undone.',
                [
                  { text: 'Cancel', style: 'cancel' },
                  { text: 'Delete', style: 'destructive', onPress: () => Alert.alert('Coming Soon', 'Account deletion will be available in production.') },
                ]
              );
            }}
          >
            <Text style={styles.deleteText}>Delete Account</Text>
          </TouchableOpacity>
        </View>

        {/* App Version */}
        <Text style={styles.versionText}>Version 1.0.0 (Build 1)</Text>

        <View style={styles.bottomPadding} />
      </ScrollView>
    </View>
  );
};

// Sub-components
const StatBox: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <View style={styles.statBox}>
    <Text style={styles.statValue}>{value}</Text>
    <Text style={styles.statLabel}>{label}</Text>
  </View>
);

const MenuItem: React.FC<{
  icon: string;
  title: string;
  subtitle: string;
  badge?: string;
  onPress: () => void;
}> = ({ icon, title, subtitle, badge, onPress }) => (
  <TouchableOpacity style={styles.menuItem} onPress={onPress} activeOpacity={0.7}>
    <Text style={styles.menuIcon}>{icon}</Text>
    <View style={styles.menuContent}>
      <Text style={styles.menuTitle}>{title}</Text>
      <Text style={styles.menuSubtitle}>{subtitle}</Text>
    </View>
    {badge && (
      <View style={styles.badge}>
        <Text style={styles.badgeText}>{badge}</Text>
      </View>
    )}
    <Text style={styles.menuArrow}>→</Text>
  </TouchableOpacity>
);

const NotificationTime: React.FC<{
  emoji: string;
  label: string;
  time: string;
}> = ({ emoji, label, time }) => (
  <View style={styles.notificationRow}>
    <Text style={styles.notificationEmoji}>{emoji}</Text>
    <Text style={styles.notificationLabel}>{label}</Text>
    <Text style={styles.notificationTime}>{time}</Text>
  </View>
);

const ToneOption: React.FC<{
  label: string;
  description: string;
  selected: boolean;
  onPress: () => void;
}> = ({ label, description, selected, onPress }) => (
  <TouchableOpacity
    style={[styles.toneOption, selected && styles.toneOptionSelected]}
    onPress={onPress}
    activeOpacity={0.7}
  >
    <View style={styles.toneOptionContent}>
      <Text style={[styles.toneOptionLabel, selected && styles.toneOptionLabelSelected]}>
        {label}
      </Text>
      <Text style={styles.toneOptionDescription}>{description}</Text>
    </View>
    {selected && (
      <View style={styles.selectedBadge}>
        <Text style={styles.selectedBadgeText}>✓</Text>
      </View>
    )}
  </TouchableOpacity>
);

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
  spacer: {
    width: 50,
  },
  content: {
    flex: 1,
  },
  userCard: {
    backgroundColor: '#FFFFFF',
    marginHorizontal: 16,
    marginTop: 20,
    borderRadius: 24,
    padding: 28,
    alignItems: 'center',
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.12,
    shadowRadius: 14,
    elevation: 4,
    borderWidth: 1,
    borderColor: '#E9D5FF',
  },
  avatarContainer: {
    position: 'relative',
    marginBottom: 18,
  },
  avatar: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: '#8B5CF6',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 3,
  },
  avatarText: {
    fontSize: 36,
    fontWeight: '800',
    color: '#FFFFFF',
  },
  premiumBadge: {
    position: 'absolute',
    bottom: -4,
    right: -4,
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#FFD700',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    borderColor: '#FFF',
  },
  premiumIcon: {
    fontSize: 16,
  },
  userName: {
    fontSize: 24,
    fontWeight: '700',
    color: '#1A1A1A',
    marginBottom: 4,
  },
  userEmail: {
    fontSize: 14,
    color: '#666',
    marginBottom: 20,
  },
  statsRow: {
    flexDirection: 'row',
    gap: 16,
  },
  statBox: {
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 20,
    backgroundColor: '#F5F8FF',
    borderRadius: 12,
  },
  statValue: {
    fontSize: 22,
    fontWeight: '700',
    color: '#007AFF',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 11,
    color: '#666',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  menuSection: {
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    marginTop: 20,
    borderRadius: 20,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 18,
    borderBottomWidth: 1,
    borderBottomColor: '#E9D5FF',
    backgroundColor: '#FFFFFF',
  },
  menuIcon: {
    fontSize: 26,
    width: 44,
  },
  menuContent: {
    flex: 1,
  },
  menuTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: '#1F2937',
    marginBottom: 4,
  },
  menuSubtitle: {
    fontSize: 13,
    color: '#666',
  },
  badge: {
    backgroundColor: '#34C759',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    marginRight: 8,
  },
  badgeText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#FFF',
  },
  menuArrow: {
    fontSize: 18,
    color: '#C0C0C0',
  },
  expandedSection: {
    backgroundColor: '#F9F9FB',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  settingLabel: {
    fontSize: 15,
    fontWeight: '600',
    color: '#333',
  },
  notificationRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 12,
    backgroundColor: '#FFF',
    borderRadius: 10,
    marginTop: 8,
  },
  notificationEmoji: {
    fontSize: 20,
    marginRight: 12,
  },
  notificationLabel: {
    flex: 1,
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  notificationTime: {
    fontSize: 14,
    color: '#007AFF',
    fontWeight: '500',
  },
  hintText: {
    fontSize: 12,
    color: '#999',
    marginTop: 12,
    fontStyle: 'italic',
  },
  toneOption: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#FFF',
    borderRadius: 10,
    padding: 14,
    marginTop: 8,
    borderWidth: 2,
    borderColor: '#E8E8E8',
  },
  toneOptionSelected: {
    backgroundColor: '#E5F1FF',
    borderColor: '#007AFF',
  },
  toneOptionContent: {
    flex: 1,
  },
  toneOptionLabel: {
    fontSize: 15,
    fontWeight: '700',
    color: '#333',
    marginBottom: 2,
  },
  toneOptionLabelSelected: {
    color: '#007AFF',
  },
  toneOptionDescription: {
    fontSize: 12,
    color: '#666',
  },
  selectedBadge: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
  },
  selectedBadgeText: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: '700',
  },
  privacyCard: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  privacyTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1A1A1A',
    marginBottom: 12,
  },
  privacyText: {
    fontSize: 13,
    color: '#666',
    lineHeight: 22,
  },
  linkButton: {
    backgroundColor: '#007AFF',
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
  },
  linkButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FFF',
  },
  dangerSection: {
    marginHorizontal: 16,
    marginTop: 32,
    marginBottom: 20,
    gap: 12,
  },
  logoutButton: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#FF3B30',
  },
  logoutText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FF3B30',
  },
  deleteButton: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#FF3B30',
  },
  deleteText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FF3B30',
  },
  versionText: {
    textAlign: 'center',
    fontSize: 12,
    color: '#999',
    marginTop: 20,
    marginBottom: 8,
  },
  bottomPadding: {
    height: 40,
  },
});

export default ProfileScreen;

