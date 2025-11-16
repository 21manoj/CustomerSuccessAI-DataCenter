#!/usr/bin/env ts-node
/**
 * SIMULATION RUNNER
 * Execute 2-hour user simulation and generate analytics
 */

import { UserSimulator } from './UserSimulator';
import { AnalyticsEngine } from './AnalyticsEngine';
import * as fs from 'fs';
import * as path from 'path';

async function main() {
  console.clear();
  console.log('╔════════════════════════════════════════════════════════════╗');
  console.log('║                                                            ║');
  console.log('║          FULFILLMENT APP - 100 USER SIMULATOR              ║');
  console.log('║                                                            ║');
  console.log('║  • 100 users with realistic behavior patterns             ║');
  console.log('║  • 12 simulated days (10 minutes = 1 day)                 ║');
  console.log('║  • Real-time check-ins, details, journals                 ║');
  console.log('║  • Premium conversion tracking                            ║');
  console.log('║  • Comprehensive analytics                                ║');
  console.log('║                                                            ║');
  console.log('╚════════════════════════════════════════════════════════════╝');
  console.log('\n');
  
  // Initialize simulator
  const simulator = new UserSimulator();
  
  // Run 2-hour simulation
  await simulator.runSimulation();
  
  // Export data
  console.log('💾 Exporting simulation data...\n');
  const data = simulator.exportData();
  
  // Generate analytics
  console.log('📊 Generating analytics...\n');
  const analytics = new AnalyticsEngine(data);
  const report = analytics.generateAnalytics();
  
  // Save to files
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const outputDir = path.join(__dirname, 'output');
  
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  
  // Save raw data
  fs.writeFileSync(
    path.join(outputDir, `simulation-data-${timestamp}.json`),
    JSON.stringify(data, null, 2)
  );
  
  // Save analytics report
  fs.writeFileSync(
    path.join(outputDir, `analytics-report-${timestamp}.json`),
    JSON.stringify(report, null, 2)
  );
  
  // Generate HTML dashboard
  const dashboard = generateDashboard(report, data);
  fs.writeFileSync(
    path.join(outputDir, `dashboard-${timestamp}.html`),
    dashboard
  );
  
  console.log('✅ Files saved:');
  console.log(`   📄 simulation-data-${timestamp}.json`);
  console.log(`   📊 analytics-report-${timestamp}.json`);
  console.log(`   🌐 dashboard-${timestamp}.html`);
  console.log('\n');
  
  // Print key metrics
  printKeyMetrics(report);
  
  console.log('\n🎉 Simulation complete! Open dashboard HTML to view detailed analytics.\n');
}

function printKeyMetrics(report: any) {
  console.log('╔════════════════════════════════════════════════════════════╗');
  console.log('║                     KEY METRICS                            ║');
  console.log('╚════════════════════════════════════════════════════════════╝\n');
  
  console.log('📊 OVERVIEW:');
  console.log(`   Total Users: ${report.overview.totalUsers}`);
  console.log(`   Active Users: ${report.overview.activeUsers} (${report.overview.activationRate})`);
  console.log(`   Premium Users: ${report.overview.premiumUsers} (${report.overview.conversionRate})`);
  console.log(`   Avg MDW: ${report.overview.avgMDW}`);
  console.log(`   Projected ARR: ${report.overview.projectedARR}`);
  console.log('');
  
  console.log('💰 REVENUE:');
  console.log(`   MRR: ${report.revenueProjection.mrr}`);
  console.log(`   ARR: ${report.revenueProjection.arr}`);
  console.log(`   LTV: ${report.revenueProjection.ltv}`);
  console.log(`   Avg Days to Convert: ${report.revenueProjection.avgDaysToConvert}`);
  console.log('');
  
  console.log('📈 ENGAGEMENT:');
  console.log(`   DAU: ${report.engagementMetrics.dau}`);
  console.log(`   Stickiness: ${report.engagementMetrics.stickiness}`);
  console.log(`   L7 Retention: ${report.engagementMetrics.l7Retention}`);
  console.log(`   Avg Session Duration: ${report.engagementMetrics.avgSessionDuration}`);
  console.log('');
  
  console.log('⚠️  CHURN RISK:');
  console.log(`   High Risk: ${report.churnRisk.summary.highRisk} users`);
  console.log(`   Medium Risk: ${report.churnRisk.summary.mediumRisk} users`);
  console.log(`   Premium at Risk: ${report.churnRisk.summary.premiumAtRisk} users`);
}

function generateDashboard(report: any, data: any): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Fulfillment App - Simulation Analytics</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
  </style>
</head>
<body class="bg-gray-50">
  
  <!-- Header -->
  <div class="bg-gradient-to-r from-blue-600 to-teal-600 text-white py-8">
    <div class="max-w-7xl mx-auto px-6">
      <h1 class="text-4xl font-bold mb-2">📊 Simulation Analytics Dashboard</h1>
      <p class="text-blue-100">100 Users • 12 Days • Real Behavior Patterns</p>
      <p class="text-sm text-blue-200 mt-2">Generated: ${new Date().toLocaleString()}</p>
    </div>
  </div>
  
  <!-- Overview Cards -->
  <div class="max-w-7xl mx-auto px-6 py-8">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
      <div class="bg-white rounded-xl p-6 shadow-lg">
        <div class="text-gray-500 text-sm mb-1">Total Users</div>
        <div class="text-3xl font-bold text-gray-900">${report.overview.totalUsers}</div>
        <div class="text-sm text-green-600 mt-1">${report.overview.activationRate} active</div>
      </div>
      
      <div class="bg-white rounded-xl p-6 shadow-lg">
        <div class="text-gray-500 text-sm mb-1">Premium Conversion</div>
        <div class="text-3xl font-bold text-purple-600">${report.overview.conversionRate}</div>
        <div class="text-sm text-gray-600 mt-1">${report.overview.premiumUsers} users</div>
      </div>
      
      <div class="bg-white rounded-xl p-6 shadow-lg">
        <div class="text-gray-500 text-sm mb-1">Avg MDW</div>
        <div class="text-3xl font-bold text-blue-600">${report.overview.avgMDW}</div>
        <div class="text-sm text-gray-600 mt-1">Meaningful Days/Week</div>
      </div>
      
      <div class="bg-white rounded-xl p-6 shadow-lg">
        <div class="text-gray-500 text-sm mb-1">Projected ARR</div>
        <div class="text-3xl font-bold text-green-600">${report.overview.projectedARR}</div>
        <div class="text-sm text-gray-600 mt-1">MRR: ${report.revenueProjection.mrr}</div>
      </div>
    </div>
    
    <!-- Cohort Analysis -->
    <div class="bg-white rounded-xl p-6 shadow-lg mb-8">
      <h2 class="text-xl font-bold text-gray-900 mb-4">📈 Daily Cohort Analysis</h2>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-4 py-2 text-left">Day</th>
              <th class="px-4 py-2 text-right">Active Users</th>
              <th class="px-4 py-2 text-right">Retention %</th>
              <th class="px-4 py-2 text-right">Avg Check-ins</th>
              <th class="px-4 py-2 text-right">MDW</th>
              <th class="px-4 py-2 text-right">Conversions</th>
              <th class="px-4 py-2 text-right">Total Premium</th>
            </tr>
          </thead>
          <tbody>
            ${report.cohortAnalysis.map((c: any) => `
              <tr class="border-t">
                <td class="px-4 py-2 font-semibold">Day ${c.day}</td>
                <td class="px-4 py-2 text-right">${c.activeUsers}</td>
                <td class="px-4 py-2 text-right ${c.retentionRate >= 70 ? 'text-green-600' : c.retentionRate >= 50 ? 'text-yellow-600' : 'text-red-600'}">${c.retentionRate.toFixed(1)}%</td>
                <td class="px-4 py-2 text-right">${c.avgCheckInsPerActiveUser.toFixed(1)}</td>
                <td class="px-4 py-2 text-right">${c.meaningfulDays}</td>
                <td class="px-4 py-2 text-right ${c.premiumConversions > 0 ? 'text-purple-600 font-bold' : ''}">${c.premiumConversions || '-'}</td>
                <td class="px-4 py-2 text-right font-semibold">${c.cumulativePremium}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
    
    <!-- Funnel Metrics -->
    <div class="bg-white rounded-xl p-6 shadow-lg mb-8">
      <h2 class="text-xl font-bold text-gray-900 mb-4">🔄 Conversion Funnel</h2>
      <div class="space-y-3">
        ${report.funnelMetrics.map((f: any, i: number) => `
          <div>
            <div class="flex items-center justify-between mb-1">
              <div class="text-sm font-semibold">${f.stage}</div>
              <div class="text-sm text-gray-600">${f.users} users (${f.percentage.toFixed(1)}%)</div>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-3">
              <div class="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full" style="width: ${f.percentage}%"></div>
            </div>
            ${f.dropOff > 0 ? `<div class="text-xs text-red-600 mt-1">Drop-off: ${f.dropOff} users</div>` : ''}
          </div>
        `).join('')}
      </div>
    </div>
    
    <!-- Persona Metrics -->
    <div class="bg-white rounded-xl p-6 shadow-lg mb-8">
      <h2 class="text-xl font-bold text-gray-900 mb-4">🎭 Persona Breakdown</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        ${report.personaMetrics.map((p: any) => `
          <div class="border border-gray-200 rounded-lg p-4">
            <div class="text-lg font-bold text-gray-900 mb-3">${p.persona.toUpperCase()}</div>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-gray-600">Users:</span>
                <span class="font-semibold">${p.count} (${p.percentage})</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">Avg Check-ins:</span>
                <span class="font-semibold">${p.avgCheckIns}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">Avg MDW:</span>
                <span class="font-semibold">${p.avgMDW}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">Fulfillment Score:</span>
                <span class="font-semibold">${p.avgFulfillment}/100</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">Premium Rate:</span>
                <span class="font-semibold text-purple-600">${p.premiumRate}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">Avg Streak:</span>
                <span class="font-semibold">${p.avgStreak} days</span>
              </div>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
    
    <!-- Revenue Metrics -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
      <div class="bg-white rounded-xl p-6 shadow-lg">
        <h2 class="text-xl font-bold text-gray-900 mb-4">💰 Revenue Projection</h2>
        <div class="space-y-3">
          <div class="flex justify-between items-center">
            <span class="text-gray-600">MRR</span>
            <span class="text-2xl font-bold text-green-600">${report.revenueProjection.mrr}</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-gray-600">ARR</span>
            <span class="text-2xl font-bold text-green-600">${report.revenueProjection.arr}</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-gray-600">Avg LTV</span>
            <span class="text-xl font-bold text-blue-600">${report.revenueProjection.ltv}</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-gray-600">Avg Days to Convert</span>
            <span class="text-lg font-semibold">${report.revenueProjection.avgDaysToConvert} days</span>
          </div>
        </div>
      </div>
      
      <div class="bg-white rounded-xl p-6 shadow-lg">
        <h2 class="text-xl font-bold text-gray-900 mb-4">⚠️ Churn Risk</h2>
        <div class="space-y-3">
          <div class="flex justify-between items-center">
            <span class="text-gray-600">High Risk</span>
            <span class="text-2xl font-bold text-red-600">${report.churnRisk.summary.highRisk}</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-gray-600">Medium Risk</span>
            <span class="text-2xl font-bold text-yellow-600">${report.churnRisk.summary.mediumRisk}</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-gray-600">Low Risk</span>
            <span class="text-2xl font-bold text-green-600">${report.churnRisk.summary.lowRisk}</span>
          </div>
          <div class="flex justify-between items-center pt-3 border-t">
            <span class="text-gray-600 font-semibold">Premium at Risk</span>
            <span class="text-xl font-bold text-red-600">${report.churnRisk.summary.premiumAtRisk}</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Conversion Factors -->
    <div class="bg-white rounded-xl p-6 shadow-lg mb-8">
      <h2 class="text-xl font-bold text-gray-900 mb-4">🎯 Conversion Factors</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div>
          <h3 class="font-semibold text-gray-700 mb-2">MDW Impact</h3>
          <div class="text-sm space-y-1">
            <div>Premium: <span class="font-bold">${report.conversionFactors.mdwImpact.premium}</span></div>
            <div>Free: <span class="font-bold">${report.conversionFactors.mdwImpact.free}</span></div>
            <div class="text-green-600 font-semibold">Lift: ${report.conversionFactors.mdwImpact.lift}</div>
          </div>
        </div>
        <div>
          <h3 class="font-semibold text-gray-700 mb-2">Check-in Impact</h3>
          <div class="text-sm space-y-1">
            <div>Premium: <span class="font-bold">${report.conversionFactors.checkInImpact.premium}</span></div>
            <div>Free: <span class="font-bold">${report.conversionFactors.checkInImpact.free}</span></div>
            <div class="text-green-600 font-semibold">Lift: ${report.conversionFactors.checkInImpact.lift}</div>
          </div>
        </div>
        <div>
          <h3 class="font-semibold text-gray-700 mb-2">Streak Impact</h3>
          <div class="text-sm space-y-1">
            <div>Premium: <span class="font-bold">${report.conversionFactors.streakImpact.premium}</span></div>
            <div>Free: <span class="font-bold">${report.conversionFactors.streakImpact.free}</span></div>
            <div class="text-green-600 font-semibold">Lift: ${report.conversionFactors.streakImpact.lift}</div>
          </div>
        </div>
      </div>
    </div>
    
  </div>
  
</body>
</html>`;
}

main().catch(console.error);

