/**
 * Interaction Tracker Service
 * Tracks user interactions for conversion optimization
 */

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:3005';

class InteractionTracker {
  constructor(userId) {
    this.userId = userId;
  }

  /**
   * Track a locked insight click
   */
  async trackLockedInsightClick(insightId, insightType, previewText) {
    try {
      await fetch(`${API_BASE}/api/users/${this.userId}/interactions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'locked_insight_click',
          data: {
            insightId,
            insightType,
            previewText
          }
        })
      });
      console.log('✅ Tracked locked insight click:', insightId);
    } catch (error) {
      console.error('❌ Error tracking interaction:', error.message);
    }
  }

  /**
   * Track premium preview view duration
   */
  async trackPremiumPreviewView(duration, featurePreviewed) {
    try {
      await fetch(`${API_BASE}/api/users/${this.userId}/interactions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'premium_preview_view',
          data: {
            duration, // seconds
            featurePreviewed
          }
        })
      });
    } catch (error) {
      console.error('❌ Error tracking preview view:', error.message);
    }
  }

  /**
   * Track conversion offer interaction
   */
  async trackConversionOfferInteraction(action, offerType) {
    try {
      await fetch(`${API_BASE}/api/users/${this.userId}/interactions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'conversion_offer_interaction',
          data: {
            action, // 'shown', 'dismissed', 'clicked'
            offerType
          }
        })
      });
    } catch (error) {
      console.error('❌ Error tracking conversion offer:', error.message);
    }
  }

  /**
   * Get user's interaction history
   */
  async getInteractions(type = null) {
    try {
      const url = type
        ? `${API_BASE}/api/users/${this.userId}/interactions?type=${type}`
        : `${API_BASE}/api/users/${this.userId}/interactions`;
      
      const response = await fetch(url);
      const data = await response.json();
      return data.interactions || [];
    } catch (error) {
      console.error('❌ Error getting interactions:', error.message);
      return [];
    }
  }
}

export default InteractionTracker;

