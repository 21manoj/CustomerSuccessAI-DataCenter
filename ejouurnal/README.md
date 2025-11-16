# eJournal - Mobile Journaling App

A React Native mobile app for daily journaling with emotion tracking, automatic summary generation, and intelligent suggestions for community and professional support.

## Features

### 🎭 Emotion Tracking
- Quick-click emotion selection with 10 predefined emotions
- Visual emotion picker with emojis and colors
- Emotion intensity tracking (1-5 scale)

### 📝 Journal Entries
- Simple form with Who/When/Where/How fields
- Additional notes section for extra details
- Timestamped entries for chronological tracking

### 📊 Daily Summaries
- Automatic generation of daily summaries
- Dominant emotion identification
- Chronological entry display
- Pattern recognition and insights

### 💡 Smart Suggestions
- Community support recommendations
- Professional help suggestions
- Priority-based suggestion system
- Context-aware recommendations

## Getting Started

### Prerequisites
- Node.js (v14 or higher)
- npm or yarn
- Expo CLI (`npm install -g @expo/cli`)
- iOS Simulator (for iOS development) or Android Studio (for Android development)

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd ejouurnal
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

4. Run on your preferred platform:
```bash
# For iOS
npm run ios

# For Android
npm run android

# For web
npm run web
```

## App Structure

```
src/
├── components/
│   ├── EmotionSelector.tsx    # Emotion selection interface
│   ├── JournalEntryForm.tsx   # Journal entry form
│   └── DailySummary.tsx       # Daily summary display
├── services/
│   └── JournalService.ts      # Data management and business logic
├── types/
│   └── index.ts               # TypeScript type definitions
└── App.tsx                    # Main app component
```

## How to Use

### 1. Emotion Selection
- Open the app to see the emotion selector
- Tap on any emotion to start a new journal entry
- Each emotion has a unique color and emoji

### 2. Creating Journal Entries
- After selecting an emotion, fill out the form:
  - **Who**: Who were you with?
  - **When**: When did this happen?
  - **Where**: Where were you?
  - **How**: How did it make you feel?
  - **Additional Notes**: Optional extra details

### 3. Viewing Daily Summary
- After creating entries, view your daily summary
- See all entries chronologically
- Get insights about your dominant emotions
- Receive personalized suggestions

### 4. Suggestions System
- **Community Suggestions**: Connect with others, join groups
- **Professional Suggestions**: Seek professional help when needed
- **Priority Levels**: High, Medium, Low priority suggestions

## Data Storage

The app uses AsyncStorage for local data persistence:
- Journal entries are stored locally on your device
- Emotions and settings are saved automatically
- Data persists between app sessions

## Customization

### Adding New Emotions
Edit the `defaultEmotions` array in `JournalService.ts`:

```typescript
private defaultEmotions: Emotion[] = [
  { id: '11', name: 'Excited', emoji: '🤩', color: '#FF1493', intensity: 5 },
  // Add more emotions...
];
```

### Modifying Suggestions
Update the `generateSuggestions` method in `JournalService.ts` to customize the suggestion logic.

## Technical Details

- **Framework**: React Native with Expo
- **Language**: TypeScript
- **Storage**: AsyncStorage
- **Navigation**: React Navigation (ready for implementation)
- **UI**: Custom components with React Native styling

## Future Enhancements

- [ ] Cloud sync and backup
- [ ] Data export (PDF, CSV)
- [ ] Mood trends and analytics
- [ ] Push notifications for journaling reminders
- [ ] Social sharing features
- [ ] Integration with health apps
- [ ] Voice-to-text journaling
- [ ] Photo attachments

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support or questions, please open an issue in the repository or contact the development team.

---

**Note**: This app is designed for personal use and mental health tracking. For serious mental health concerns, please consult with a qualified healthcare professional.

