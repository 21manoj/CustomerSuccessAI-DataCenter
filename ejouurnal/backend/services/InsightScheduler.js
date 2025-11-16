/**
 * InsightScheduler - Background job to auto-generate insights
 * 
 * Runs daily at midnight to:
 * 1. Find users with 3+ days of data
 * 2. Generate fresh insights
 * 3. Queue notifications for new insights
 */

const cron = require('node-cron');
const { Pool } = require('pg');
const insightEngine = require('./InsightEngine');

class InsightScheduler {
  constructor(pool) {
    this.pool = pool;
    this.isRunning = false;
  }

  /**
   * Start the scheduler
   * Runs daily at 1:00 AM
   */
  start() {
    console.log('📅 Insight Scheduler started');
    
    // Run daily at 1:00 AM
    cron.schedule('0 1 * * *', async () => {
      console.log('🧠 Running daily insight generation...');
      await this.generateDailyInsights();
    });
    
    // Also run on startup (optional)
    // this.generateDailyInsights();
  }

  /**
   * Generate insights for all eligible users
   */
  async generateDailyInsights() {
    if (this.isRunning) {
      console.log('⚠️  Insight generation already running, skipping...');
      return;
    }

    this.isRunning = true;

    try {
      // Find users with 3+ check-ins who haven't had insights generated today
      const usersResult = await this.pool.query(`
        SELECT DISTINCT u.user_id, u.is_premium
        FROM users u
        INNER JOIN check_ins ci ON u.user_id = ci.user_id
        WHERE ci.created_at > NOW() - INTERVAL '30 days'
        GROUP BY u.user_id, u.is_premium
        HAVING COUNT(ci.id) >= 6
      `);

      console.log(`📊 Found ${usersResult.rows.length} users eligible for insights`);

      let insightsGenerated = 0;
      let usersProcessed = 0;

      for (const user of usersResult.rows) {
        try {
          // Get user data
          const checkInsResult = await this.pool.query(
            `SELECT * FROM check_ins 
             WHERE user_id = $1 
             ORDER BY created_at DESC 
             LIMIT 120`,
            [user.user_id]
          );

          const detailsResult = await this.pool.query(
            `SELECT * FROM details 
             WHERE user_id = $1 
             ORDER BY created_at DESC 
             LIMIT 30`,
            [user.user_id]
          );

          const scoresResult = await this.pool.query(
            `SELECT * FROM daily_scores 
             WHERE user_id = $1 
             ORDER BY created_at DESC 
             LIMIT 30`,
            [user.user_id]
          );

          const userData = {
            checkIns: checkInsResult.rows,
            details: detailsResult.rows,
            scores: scoresResult.rows,
            isPremium: user.is_premium || false,
          };

          // Generate insights
          const insights = await insightEngine.generateInsights(userData);

          // Save new insights
          for (const insight of insights) {
            const existing = await this.pool.query(
              `SELECT id FROM insights 
               WHERE user_id = $1 AND insight_type = $2 AND title = $3
               AND created_at > NOW() - INTERVAL '7 days'`,
              [user.user_id, insight.type, insight.title]
            );

            if (existing.rows.length === 0) {
              await this.pool.query(
                `INSERT INTO insights 
                 (user_id, insight_type, title, description, confidence, source_metric, target_metric, impact, metadata)
                 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
                [
                  user.user_id,
                  insight.type,
                  insight.title,
                  insight.description,
                  insight.confidence,
                  insight.sourceMetric,
                  insight.targetMetric,
                  insight.impact,
                  JSON.stringify({ 
                    isPremiumGate: insight.isPremiumGate || false,
                    lagDays: insight.lagDays,
                    threshold: insight.threshold
                  })
                ]
              );
              insightsGenerated++;
            }
          }

          usersProcessed++;
        } catch (error) {
          console.error(`Error processing user ${user.user_id}:`, error.message);
        }
      }

      console.log(`✅ Insight generation complete: ${insightsGenerated} new insights for ${usersProcessed} users`);
    } catch (error) {
      console.error('Error in daily insight generation:', error);
    } finally {
      this.isRunning = false;
    }
  }

  /**
   * Manually trigger insight generation (for testing)
   */
  async runNow() {
    console.log('🔄 Manually triggering insight generation...');
    await this.generateDailyInsights();
  }
}

module.exports = InsightScheduler;

