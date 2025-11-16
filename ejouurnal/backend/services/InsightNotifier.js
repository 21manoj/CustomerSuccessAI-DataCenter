/**
 * InsightNotifier - Push notification service for new insights
 * 
 * Notifies users when:
 * 1. First insight is generated (Day 3-4)
 * 2. New breakthrough insights are discovered
 * 3. Premium-gated insights are available
 */

class InsightNotifier {
  constructor(pool) {
    this.pool = pool;
  }

  /**
   * Notify user about new insight
   */
  async notifyNewInsight(userId, insight) {
    try {
      // Store notification in database
      await this.pool.query(
        `INSERT INTO notifications 
         (user_id, type, title, body, data, sent_at)
         VALUES ($1, $2, $3, $4, $5, NOW())`,
        [
          userId,
          'new_insight',
          '💡 New Insight Discovered!',
          insight.title,
          JSON.stringify({ insightId: insight.id, insightType: insight.type })
        ]
      );

      // TODO: Integrate with push notification service (OneSignal, Firebase, etc.)
      console.log(`📨 Notification queued for user ${userId}: ${insight.title}`);
      
      return { success: true };
    } catch (error) {
      console.error('Error sending notification:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Notify about first "aha moment"
   */
  async notifyFirstInsight(userId) {
    try {
      await this.pool.query(
        `INSERT INTO notifications 
         (user_id, type, title, body, data, sent_at)
         VALUES ($1, $2, $3, $4, $5, NOW())`,
        [
          userId,
          'first_insight',
          '🎉 Your First Insight is Ready!',
          'We\'ve analyzed your patterns and found something interesting. Tap to see what we discovered about you.',
          JSON.stringify({ trigger: 'first_insight' })
        ]
      );

      console.log(`🎉 First insight notification sent to user ${userId}`);
      return { success: true };
    } catch (error) {
      console.error('Error sending first insight notification:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Notify about premium gate
   */
  async notifyPremiumGate(userId, insightType) {
    try {
      await this.pool.query(
        `INSERT INTO notifications 
         (user_id, type, title, body, data, sent_at)
         VALUES ($1, $2, $3, $4, $5, NOW())`,
        [
          userId,
          'premium_gate',
          '🔒 Deeper Insights Available',
          `Unlock ${insightType} analysis to see your personal thresholds and patterns.`,
          JSON.stringify({ trigger: 'premium_gate', insightType })
        ]
      );

      console.log(`🔒 Premium gate notification sent to user ${userId}`);
      return { success: true };
    } catch (error) {
      console.error('Error sending premium gate notification:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Get unread notifications for user
   */
  async getUnreadNotifications(userId) {
    try {
      const result = await this.pool.query(
        `SELECT * FROM notifications 
         WHERE user_id = $1 AND viewed_at IS NULL 
         ORDER BY sent_at DESC`,
        [userId]
      );

      return result.rows;
    } catch (error) {
      console.error('Error fetching notifications:', error);
      return [];
    }
  }

  /**
   * Mark notification as viewed
   */
  async markAsViewed(notificationId) {
    try {
      await this.pool.query(
        `UPDATE notifications 
         SET viewed_at = NOW() 
         WHERE id = $1`,
        [notificationId]
      );

      return { success: true };
    } catch (error) {
      console.error('Error marking notification as viewed:', error);
      return { success: false, error: error.message };
    }
  }
}

module.exports = InsightNotifier;

